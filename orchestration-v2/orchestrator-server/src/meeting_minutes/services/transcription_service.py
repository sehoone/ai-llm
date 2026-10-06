"""Transcription with speaker diarization for meeting audio.

Primary path: Azure **Fast Transcription** REST API, which accepts the audio file
directly (no pre-uploaded URL needed) and returns diarized, timestamped phrases.
Fallback: OpenAI Whisper (no diarization — a single "Speaker 1" segment), used
when Azure is not configured or fails. This mirrors the Azure-primary /
Whisper-fallback philosophy already used by ``voice_evaluation.AudioService``.
"""

import io
import json
from typing import Dict, List, Optional

import httpx
from openai import OpenAI

from src.common.config import settings
from src.common.logging import logger

# Azure Fast Transcription API version (stable as of 2024-11-15).
_AZURE_API_VERSION = "2024-11-15"


class TranscriptionService:
    """Produce diarized transcript segments from an audio file."""

    def __init__(self) -> None:
        self._openai = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.azure_enabled = bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION)

    async def transcribe(
        self,
        audio_path: str,
        filename: str,
        language: str = "ko-KR",
        max_speakers: int = 10,
    ) -> Dict:
        """Transcribe an audio file.

        Returns:
            dict: ``{"provider": "azure"|"whisper", "segments": [ {seq, speaker_label,
            start_ms, end_ms, text}, ... ], "duration_sec": int|None}``.
        """
        if self.azure_enabled:
            try:
                result = await self._azure_fast_transcribe(audio_path, language, max_speakers)
                if result and result["segments"]:
                    logger.info("meeting_transcribe_azure_ok", segments=len(result["segments"]))
                    return result
                logger.warning("meeting_transcribe_azure_empty_fallback_whisper")
            except Exception as e:
                logger.error("meeting_transcribe_azure_error", error=str(e), exc_info=True)

        logger.info("meeting_transcribe_whisper")
        return await self._whisper_transcribe(audio_path, filename, language)

    async def _azure_fast_transcribe(
        self, audio_path: str, language: str, max_speakers: int
    ) -> Optional[Dict]:
        """Call Azure Fast Transcription with diarization enabled."""
        url = (
            f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com"
            f"/speechtotext/transcriptions:transcribe?api-version={_AZURE_API_VERSION}"
        )
        definition = {
            "locales": [language],
            "diarization": {"maxSpeakers": max(2, max_speakers), "enabled": True},
        }

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        files = {
            "audio": (audio_path.rsplit("/", 1)[-1], audio_bytes, "application/octet-stream"),
            "definition": (None, json.dumps(definition), "application/json"),
        }
        headers = {"Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY}

        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(url, headers=headers, files=files)
            if resp.status_code != 200:
                logger.error(
                    "azure_fast_transcribe_failed",
                    status_code=resp.status_code,
                    body=resp.text[:500],
                )
                return None
            data = resp.json()

        phrases = data.get("phrases", []) or []
        segments: List[Dict] = []
        for i, p in enumerate(phrases):
            speaker = p.get("speaker")
            label = f"Speaker {speaker}" if speaker is not None else "Speaker 1"
            start_ms = int(p.get("offsetMilliseconds", 0) or 0)
            dur_ms = int(p.get("durationMilliseconds", 0) or 0)
            text = (p.get("text") or "").strip()
            if not text:
                continue
            segments.append(
                {
                    "seq": i,
                    "speaker_label": label,
                    "start_ms": start_ms,
                    "end_ms": start_ms + dur_ms,
                    "text": text,
                }
            )

        duration_ms = int(data.get("durationMilliseconds", 0) or 0)
        duration_sec = round(duration_ms / 1000) if duration_ms else None
        return {"provider": "azure", "segments": segments, "duration_sec": duration_sec}

    async def _whisper_transcribe(
        self, audio_path: str, filename: str, language: str
    ) -> Dict:
        """Transcribe with OpenAI Whisper (no diarization).

        Whisper has a ~25MB per-request limit; larger files should use the Azure
        path. On failure, returns an empty segment list so the caller can mark the
        meeting FAILED with a clear message.
        """
        if self._openai is None:
            logger.error("whisper_unavailable_no_openai_key")
            return {"provider": "whisper", "segments": [], "duration_sec": None}

        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            buf = io.BytesIO(audio_bytes)
            buf.name = filename or "audio.webm"
            # Whisper language codes are 2-letter (e.g. "ko"), not locales ("ko-KR").
            lang2 = (language or "ko").split("-")[0]
            transcript = self._openai.audio.transcriptions.create(
                model=settings.OPENAI_STT_MODEL,
                file=buf,
                language=lang2,
                response_format="verbose_json",
            )
            text = (getattr(transcript, "text", "") or "").strip()
            duration = getattr(transcript, "duration", None)
            segments: List[Dict] = []
            # Prefer Whisper's own segments (gives timestamps) when available.
            whisper_segments = getattr(transcript, "segments", None) or []
            if whisper_segments:
                for i, s in enumerate(whisper_segments):
                    seg_text = (getattr(s, "text", "") or "").strip()
                    if not seg_text:
                        continue
                    segments.append(
                        {
                            "seq": i,
                            "speaker_label": "Speaker 1",
                            "start_ms": int(float(getattr(s, "start", 0)) * 1000),
                            "end_ms": int(float(getattr(s, "end", 0)) * 1000),
                            "text": seg_text,
                        }
                    )
            elif text:
                segments.append(
                    {"seq": 0, "speaker_label": "Speaker 1", "start_ms": 0, "end_ms": 0, "text": text}
                )

            return {
                "provider": "whisper",
                "segments": segments,
                "duration_sec": round(duration) if duration else None,
            }
        except Exception as e:
            logger.error("whisper_transcribe_error", error=str(e), exc_info=True)
            return {"provider": "whisper", "segments": [], "duration_sec": None}


transcription_service = TranscriptionService()
