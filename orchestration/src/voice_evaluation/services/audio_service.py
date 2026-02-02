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
import traceback

from openai import OpenAI
import azure.cognitiveservices.speech as speechsdk

from src.common.config import settings, Environment
from src.common.logging import logger


class AudioService:
    """Service for handling audio operations."""

    def __init__(self):
        """Initialize AudioService with OpenAI and Azure clients."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.tts_model = settings.OPENAI_TTS_MODEL
        self.tts_voice = settings.OPENAI_TTS_VOICE
        self.stt_model = settings.OPENAI_STT_MODEL
        
        # Initialize Azure Speech Service
        if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION
            )
            self.speech_config.speech_recognition_language = "en-US"
            logger.info(f"Azure Speech initialized - Region: {settings.AZURE_SPEECH_REGION}")
        else:
            self.speech_config = None
            logger.warning("Azure Speech API key not set. Pronunciation assessment unavailable.")
    
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech (TTS).

        Args:
            text: The text to convert.

        Returns:
            Optional[bytes]: The audio content in bytes, or None if failed.
        """
        try:
            logger.info(f"TTS request start - Text length: {len(text)}, Model: {self.tts_model}, Voice: {self.tts_voice}")
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text
            )
            audio_content = response.content
            logger.info(f"TTS success - Audio size: {len(audio_content)} bytes")
            return audio_content
        except Exception as e:
            logger.error(f"TTS error: {str(e)}", exc_info=True)
            return None
    
    async def speech_to_text(self, audio_data: bytes, format: str = "wav") -> Optional[str]:
        """Convert speech to text (STT).
        
        Prioritizes Azure Speech Service, falls back to OpenAI Whisper if failed.

        Args:
            audio_data: The audio data in bytes.
            format: The audio format (default: "wav").

        Returns:
            Optional[str]: The recognized text, or None if failed.
        """
        try:
            logger.info("========== STT Request Start ==========")
            logger.info(f"STT Input format: {format}, Size: {len(audio_data)} bytes")
            
            if not audio_data or len(audio_data) == 0:
                logger.warning("STT audio data is empty")
                return None
            
            # Step 1: Try Azure Speech Service
            if self.speech_config:
                # Skip Azure STT if environment is development (local server) as per original logic
                # However, original code said "local server -> azure stt done use" but then checked '!= DEVELOPMENT'
                # logic was: if settings.ENVIRONMENT != Environment.DEVELOPMENT: -> use azure
                # This implies ONLY use Azure in NON-DEV. I will keep that logic.
                if settings.ENVIRONMENT != Environment.DEVELOPMENT:
                    logger.info("Attempting STT with Azure Speech Service...")
                    azure_text = await self._azure_speech_to_text(audio_data, format)
                    if azure_text:
                        logger.info(f"Azure STT Success: '{azure_text}'")
                        logger.info("========== STT Complete ==========")
                        return azure_text
                    else:
                        logger.info("Azure STT failed, falling back to Whisper...")
            
            # Step 2: Fallback to OpenAI Whisper
            logger.info("Attempting STT with OpenAI Whisper...")
            whisper_text = await self._openai_speech_to_text(audio_data, format)
            if whisper_text:
                logger.info(f"Whisper STT Success: '{whisper_text}'")
            else:
                logger.error("Whisper STT also failed")
            logger.info("========== STT Complete ==========")
            return whisper_text
            
        except Exception as e:
            logger.error(f"STT Error: {str(e)}", exc_info=True)
            return None
    
    async def _azure_speech_to_text(self, audio_data: bytes, format: str) -> Optional[str]:
        """STT using Azure Speech Service.

        Args:
            audio_data: The audio data.
            format: The format of the audio data.

        Returns:
            Optional[str]: The recognized text, or None.
        """
        if not self.speech_config:
            return None
        
        temp_file_path = None
        try:
            logger.info(f"Azure STT Start - Format: {format}, Size: {len(audio_data)} bytes")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Azure Speech Recognition
            audio_config = speechsdk.AudioConfig(filename=temp_file_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            logger.info("Azure STT recognizing...")
            result = speech_recognizer.recognize_once()
            logger.info("Azure STT recognition complete")
            
            # Release resources
            del speech_recognizer
            del audio_config
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info(f"Azure STT Success: '{result.text}'")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("Azure STT NoMatch")
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                error_details = result.cancellation_details.error_details if result.cancellation_details else "Unknown"
                logger.warning(f"Azure STT Canceled: {error_details}")
                return None
                
        except Exception as e:
            logger.error(f"Azure STT Error: {str(e)}", exc_info=True)
            return None
        finally:
            # Try to delete temporary file (max 3 times)
            if temp_file_path and os.path.exists(temp_file_path):
                for attempt in range(3):
                    try:
                        os.unlink(temp_file_path)
                        logger.debug("Azure STT temp file deleted")
                        break
                    except OSError:
                        if attempt < 2:
                            logger.debug(f"Azure STT temp file delete retry ({attempt + 1}/3)...")
                            time.sleep(0.1)  # Short wait
                        else:
                            logger.warning(f"Azure STT temp file delete failed (will be cleaned later): {temp_file_path}")
    
    async def _openai_speech_to_text(self, audio_data: bytes, format: str) -> Optional[str]:
        """STT using OpenAI Whisper.

        Args:
            audio_data: The audio data.
            format: The format of the audio data.

        Returns:
            Optional[str]: The recognized text, or None.
        """
        try:
            logger.info(f"Whisper STT Start - Size: {len(audio_data)} bytes, Format: {format}")
            
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{format}"
            
            transcript = self.client.audio.transcriptions.create(
                model=self.stt_model,
                file=audio_file,
                language="en"
            )
            logger.info(f"Whisper STT Success: '{transcript.text}'")
            return transcript.text
        except Exception as e:
            logger.error(f"Whisper STT Error: {str(e)}", exc_info=True)
            return None
    
    def audio_to_base64(self, audio_data: bytes) -> str:
        """Encode audio data to base64 string.

        Args:
            audio_data: The raw audio bytes.

        Returns:
            str: The base64 encoded string.
        """
        return base64.b64encode(audio_data).decode('utf-8')
    
    def base64_to_audio(self, base64_string: str) -> bytes:
        """Decode base64 string to audio data.

        Args:
            base64_string: The base64 encoded string.

        Returns:
            bytes: The raw audio bytes.
        """
        return base64.b64decode(base64_string)
    
    async def assess_pronunciation(
        self, 
        audio_data: bytes, 
        reference_text: Optional[str] = None,
        format: str = "wav"
    ) -> Optional[Dict[str, Any]]:
        """Assess pronunciation using Azure Speech Service.
        
        Args:
            audio_data: The audio bytes to evaluate.
            reference_text: The evaluation reference text (optional but recommended).
            format: Audio format.
        
        Returns:
            Optional[Dict[str, Any]]: The pronunciation assessment result containing scores and details.
        """
        if not self.speech_config:
            logger.warning("Azure Speech Service not configured. Reference text: %s", reference_text)
            return None
        
        # NOTE: Original code required reference_text, but signature implies Optional.
        # Keeping original check.
        if not reference_text:
            logger.warning("Reference text is required for pronunciation assessment")
            return None
        
        temp_file_path = None
        try:
            logger.info("========== Pronunciation Assessment Start ==========")
            logger.info(f"Reference text: '{reference_text}'")
            logger.info(f"Input format: {format}, Size: {len(audio_data)} bytes")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # 1. Configure Pronunciation Assessment
            logger.info("Configuring assessment...")
            
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            # 2. Audio Config
            audio_config = speechsdk.AudioConfig(filename=temp_file_path)
            
            # 3. Create Speech Recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # 4. Apply Assessment Config
            pronunciation_config.apply_to(speech_recognizer)
            
            # 5. Perform Recognition
            logger.info("Analyzing speech...")
            
            # Check environment (assuming logic intends to skip if local/dev, but implementation here checks 'local')
            # Preserving logic but using safe attribute access if possible, or keeping string comparison
            # Using getattr to be safe if environment is not on settings, though it likely is.
            env_val = getattr(settings, "environment", None) or getattr(settings, "ENVIRONMENT", "")
            if str(env_val).lower() != "local": 
                result = speech_recognizer.recognize_once()
                
                # Release resources
                del speech_recognizer
                del audio_config
                
                # 6. Process Results
                if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    # Parse result
                    pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
                    
                    # Basic scores
                    accuracy = pronunciation_result.accuracy_score
                    pronunciation = pronunciation_result.pronunciation_score
                    completeness = pronunciation_result.completeness_score
                    fluency = pronunciation_result.fluency_score
                    
                    logger.info(f"Recognition Success: '{result.text}'")
                    logger.info("Scores:")
                    logger.info(f"  - Accuracy: {accuracy:.1f}")
                    logger.info(f"  - Pronunciation: {pronunciation:.1f}")
                    logger.info(f"  - Completeness: {completeness:.1f}")
                    logger.info(f"  - Fluency: {fluency:.1f}")
                    
                    # Prosody score
                    prosody = getattr(pronunciation_result, 'prosody_score', None)
                    prosody_score = round(prosody, 2) if prosody is not None else 0
                    
                    # Build detailed result
                    assessment_data = {
                        "accuracy_score": round(accuracy, 2),
                        "pronunciation_score": round(pronunciation, 2),
                        "completeness_score": round(completeness, 2),
                        "fluency_score": round(fluency, 2),
                        "prosody_score": prosody_score,
                        "recognized_text": result.text,
                        # "reference_text": reference_text,
                    }
                    
                    # Get JSON result for details
                    json_result = result.properties.get(
                        speechsdk.PropertyId.SpeechServiceResponse_JsonResult
                    )
                    
                    if json_result:
                        try:
                            detailed_result = json.loads(json_result)
                            logger.info("Extracting detailed analysis...")
                            
                            # Extract word details from NBest
                            if "NBest" in detailed_result and len(detailed_result["NBest"]) > 0:
                                nbest = detailed_result["NBest"][0]
                                
                                # Word details
                                if "Words" in nbest:
                                    word_details = []
                                    for word_info in nbest["Words"]:
                                        word_details.append({
                                            "word": word_info.get("Word", ""),
                                            "accuracy_score": round(word_info.get("PronunciationAssessment", {}).get("AccuracyScore", 0), 2),
                                            "pronunciation_score": round(word_info.get("PronunciationAssessment", {}).get("PronunciationScore", 0), 2),
                                        })
                                    assessment_data["word_details"] = word_details
                                    logger.info(f"Word analysis: {len(word_details)} words")
                                
                                # Overall details
                                if "PronunciationAssessment" in nbest:
                                    pa = nbest["PronunciationAssessment"]
                                    assessment_data["detailed_scores"] = {
                                        "overall_accuracy": round(pa.get("AccuracyScore", 0), 2),
                                        "overall_pronunciation": round(pa.get("PronunciationScore", 0), 2),
                                        "overall_completeness": round(pa.get("CompletenessScore", 0), 2),
                                        "overall_fluency": round(pa.get("FluencyScore", 0), 2),
                                        "overall_prosody": round(pa.get("ProsodyScore", 0), 2),
                                    }
                                    logger.info("Detailed scores extracted")
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON Parsing failed: {e}")
                    
                    logger.info("========== Assessment Complete ==========")
                    return assessment_data
                    
                elif result.reason == speechsdk.ResultReason.NoMatch:
                    logger.warning(f"Speech not recognized: {result.no_match_details}")
                    return None
                    
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation = result.cancellation_details
                    logger.warning(f"Canceled: {cancellation.reason}")
                    if cancellation.reason == speechsdk.CancellationReason.Error:
                        logger.error(f"Error details: {cancellation.error_details}")
                    return None
            else:
                logger.info("Skipped assessment (Local Environment)")
                return None
                
        except Exception as e:
            logger.error(f"Assessment Error: {str(e)}", exc_info=True)
            return None
        finally:
            # Delete temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass

