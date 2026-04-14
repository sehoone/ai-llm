"""Audio processing services.

This module provides services for Text-to-Speech (TTS), Speech-to-Text (STT),
and pronunciation assessment using OpenAI and Azure Cognitive Services.
"""

import base64
import io
import json
import time
from typing import Optional, Dict, Any
import tempfile
import os

from openai import OpenAI
import azure.cognitiveservices.speech as speechsdk

from src.common.config import settings, Environment
from src.common.logging import logger


class AudioService:
    """Service for handling audio operations."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.tts_model = settings.OPENAI_TTS_MODEL
        self.tts_voice = settings.OPENAI_TTS_VOICE
        self.stt_model = settings.OPENAI_STT_MODEL

        if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION,
            )
            self.speech_config.speech_recognition_language = "en-US"
            logger.info("azure_speech_initialized", region=settings.AZURE_SPEECH_REGION)
        else:
            self.speech_config = None
            logger.warning("azure_speech_not_configured")

    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech (TTS)."""
        try:
            logger.info("tts_request_start", text_length=len(text), model=self.tts_model, voice=self.tts_voice)
            response = self.client.audio.speech.create(model=self.tts_model, voice=self.tts_voice, input=text)
            audio_content = response.content
            logger.info("tts_success", audio_bytes=len(audio_content))
            return audio_content
        except Exception as e:
            logger.error("tts_error", error=str(e), exc_info=True)
            return None

    async def speech_to_text(self, audio_data: bytes, format: str = "wav") -> Optional[str]:
        """Convert speech to text (STT).

        Prioritizes Azure Speech Service, falls back to OpenAI Whisper if failed.
        """
        try:
            logger.info("stt_request_start", format=format, audio_bytes=len(audio_data))

            if not audio_data:
                logger.warning("stt_empty_audio")
                return None

            if self.speech_config and settings.ENVIRONMENT != Environment.DEVELOPMENT:
                logger.info("stt_attempting_azure")
                azure_text = await self._azure_speech_to_text(audio_data, format)
                if azure_text:
                    logger.info("stt_azure_success", text_length=len(azure_text))
                    return azure_text
                logger.info("stt_azure_failed_fallback_whisper")

            logger.info("stt_attempting_whisper")
            whisper_text = await self._openai_speech_to_text(audio_data, format)
            if whisper_text:
                logger.info("stt_whisper_success", text_length=len(whisper_text))
            else:
                logger.error("stt_whisper_also_failed")
            return whisper_text

        except Exception as e:
            logger.error("stt_error", error=str(e), exc_info=True)
            return None

    async def _azure_speech_to_text(self, audio_data: bytes, format: str) -> Optional[str]:
        """STT using Azure Speech Service."""
        if not self.speech_config:
            return None

        temp_file_path = None
        try:
            logger.info("azure_stt_start", format=format, audio_bytes=len(audio_data))

            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            audio_config = speechsdk.AudioConfig(filename=temp_file_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )

            result = speech_recognizer.recognize_once()
            del speech_recognizer
            del audio_config

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info("azure_stt_success", text_length=len(result.text))
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("azure_stt_no_match")
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                error_details = result.cancellation_details.error_details if result.cancellation_details else "Unknown"
                logger.warning("azure_stt_canceled", error_details=error_details)
                return None

        except Exception as e:
            logger.error("azure_stt_error", error=str(e), exc_info=True)
            return None
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                for attempt in range(3):
                    try:
                        os.unlink(temp_file_path)
                        logger.debug("azure_stt_temp_file_deleted")
                        break
                    except OSError:
                        if attempt < 2:
                            logger.debug("azure_stt_temp_file_delete_retry", attempt=attempt + 1)
                            time.sleep(0.1)
                        else:
                            logger.warning("azure_stt_temp_file_delete_failed", path=temp_file_path)

    async def _openai_speech_to_text(self, audio_data: bytes, format: str) -> Optional[str]:
        """STT using OpenAI Whisper."""
        try:
            logger.info("whisper_stt_start", audio_bytes=len(audio_data), format=format)
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{format}"
            transcript = self.client.audio.transcriptions.create(
                model=self.stt_model, file=audio_file, language="en"
            )
            logger.info("whisper_stt_success", text_length=len(transcript.text))
            return transcript.text
        except Exception as e:
            logger.error("whisper_stt_error", error=str(e), exc_info=True)
            return None

    def audio_to_base64(self, audio_data: bytes) -> str:
        """Encode raw audio bytes to a Base64 string.

        Args:
            audio_data: Raw audio bytes.

        Returns:
            str: Base64-encoded audio string.
        """
        return base64.b64encode(audio_data).decode("utf-8")

    def base64_to_audio(self, base64_string: str) -> bytes:
        """Decode a Base64 string back to raw audio bytes.

        Args:
            base64_string: Base64-encoded audio string.

        Returns:
            bytes: Decoded audio bytes.
        """
        return base64.b64decode(base64_string)

    async def assess_pronunciation(
        self,
        audio_data: bytes,
        reference_text: Optional[str] = None,
        format: str = "wav",
    ) -> Optional[Dict[str, Any]]:
        """Assess pronunciation using Azure Speech Service."""
        if not self.speech_config:
            logger.warning("pronunciation_assessment_skipped_no_config", reference_text=reference_text)
            return None

        if not reference_text:
            logger.warning("pronunciation_assessment_no_reference_text")
            return None

        temp_file_path = None
        try:
            logger.info("pronunciation_assessment_start", format=format, audio_bytes=len(audio_data))

            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True,
            )
            audio_config = speechsdk.AudioConfig(filename=temp_file_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )
            pronunciation_config.apply_to(speech_recognizer)

            env_val = getattr(settings, "ENVIRONMENT", "")
            if str(env_val).lower() == "local":
                logger.info("pronunciation_assessment_skipped_local_env")
                return None

            result = speech_recognizer.recognize_once()
            del speech_recognizer
            del audio_config

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
                accuracy = pronunciation_result.accuracy_score
                pronunciation = pronunciation_result.pronunciation_score
                completeness = pronunciation_result.completeness_score
                fluency = pronunciation_result.fluency_score

                logger.info(
                    "pronunciation_assessment_scores",
                    recognized_text_length=len(result.text),
                    accuracy=round(accuracy, 1),
                    pronunciation=round(pronunciation, 1),
                    completeness=round(completeness, 1),
                    fluency=round(fluency, 1),
                )

                prosody = getattr(pronunciation_result, "prosody_score", None)
                assessment_data = {
                    "accuracy_score": round(accuracy, 2),
                    "pronunciation_score": round(pronunciation, 2),
                    "completeness_score": round(completeness, 2),
                    "fluency_score": round(fluency, 2),
                    "prosody_score": round(prosody, 2) if prosody is not None else 0,
                    "recognized_text": result.text,
                }

                json_result = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                if json_result:
                    try:
                        detailed_result = json.loads(json_result)
                        if "NBest" in detailed_result and detailed_result["NBest"]:
                            nbest = detailed_result["NBest"][0]
                            if "Words" in nbest:
                                word_details = [
                                    {
                                        "word": w.get("Word", ""),
                                        "accuracy_score": round(w.get("PronunciationAssessment", {}).get("AccuracyScore", 0), 2),
                                        "pronunciation_score": round(w.get("PronunciationAssessment", {}).get("PronunciationScore", 0), 2),
                                    }
                                    for w in nbest["Words"]
                                ]
                                assessment_data["word_details"] = word_details
                                logger.info("pronunciation_word_analysis", word_count=len(word_details))
                            if "PronunciationAssessment" in nbest:
                                pa = nbest["PronunciationAssessment"]
                                assessment_data["detailed_scores"] = {
                                    "overall_accuracy": round(pa.get("AccuracyScore", 0), 2),
                                    "overall_pronunciation": round(pa.get("PronunciationScore", 0), 2),
                                    "overall_completeness": round(pa.get("CompletenessScore", 0), 2),
                                    "overall_fluency": round(pa.get("FluencyScore", 0), 2),
                                    "overall_prosody": round(pa.get("ProsodyScore", 0), 2),
                                }
                    except json.JSONDecodeError as e:
                        logger.error("pronunciation_json_parse_failed", error=str(e))

                logger.info("pronunciation_assessment_complete")
                return assessment_data

            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("pronunciation_no_match", details=str(result.no_match_details))
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.warning("pronunciation_canceled", reason=str(cancellation.reason))
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    logger.error("pronunciation_canceled_error", error_details=cancellation.error_details)
                return None

        except Exception as e:
            logger.error("pronunciation_assessment_error", error=str(e), exc_info=True)
            return None
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
