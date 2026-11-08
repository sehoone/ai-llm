"""음성 전사(+화자 분리) — meeting 오디오용 (ADR-0005).

주 경로: Azure **Fast Transcription** REST — 오디오 파일을 직접 받아 화자 분리·타임스탬프가
포함된 구문을 반환한다. 폴백: OpenAI Whisper(화자 분리 없음 — 단일 "Speaker 1"). Azure 미설정·
실패 시 Whisper로, 둘 다 없으면 빈 세그먼트를 반환(도메인은 이를 SAVED로 처리).

engine 모듈 — `domains`·FastAPI 비의존. 외부 서비스 좌표는 도메인이 `TranscriptionConfig`로 주입
(engine은 env·DB 미조회).
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Azure Fast Transcription API 버전 (2024-11-15 안정).
_AZURE_API_VERSION = "2024-11-15"


@dataclass(frozen=True, slots=True)
class TranscriptionConfig:
    """전사 외부 서비스 설정(도메인이 settings에서 해석해 주입)."""

    azure_key: str = ""
    azure_region: str = ""
    openai_key: str = ""           # Whisper 폴백용
    stt_model: str = "whisper-1"

    @property
    def azure_enabled(self) -> bool:
        return bool(self.azure_key and self.azure_region)

    @property
    def whisper_enabled(self) -> bool:
        return bool(self.openai_key)


async def transcribe(
    audio_bytes: bytes,
    filename: str,
    language: str,
    max_speakers: int,
    *,
    config: TranscriptionConfig,
) -> dict:
    """오디오 바이트를 전사.

    Returns:
        dict: ``{"provider": "azure"|"whisper"|None, "segments": [ {seq, speaker_label,
        start_ms, end_ms, text}, ... ], "duration_sec": int|None}``.
        전사기가 없거나 결과가 없으면 ``segments=[]`` (도메인이 SAVED로 처리).
    """
    if config.azure_enabled:
        try:
            result = await _azure_fast_transcribe(audio_bytes, filename, language, max_speakers, config)
            if result and result["segments"]:
                logger.info("meeting_transcribe_azure_ok segments=%s", len(result["segments"]))
                return result
            logger.warning("meeting_transcribe_azure_empty — whisper 폴백 시도")
        except Exception:
            logger.exception("meeting_transcribe_azure_error — whisper 폴백 시도")

    if config.whisper_enabled:
        logger.info("meeting_transcribe_whisper")
        return await _whisper_transcribe(audio_bytes, filename, language, config)

    logger.warning("meeting_transcribe_unavailable — STT 미설정(저장만)")
    return {"provider": None, "segments": [], "duration_sec": None}


async def _azure_fast_transcribe(
    audio_bytes: bytes,
    filename: str,
    language: str,
    max_speakers: int,
    config: TranscriptionConfig,
) -> dict | None:
    """Azure Fast Transcription(화자 분리 활성) 호출."""
    url = (
        f"https://{config.azure_region}.api.cognitive.microsoft.com"
        f"/speechtotext/transcriptions:transcribe?api-version={_AZURE_API_VERSION}"
    )
    definition = {
        "locales": [language],
        "diarization": {"maxSpeakers": max(2, max_speakers), "enabled": True},
    }
    files = {
        "audio": (filename or "recording.webm", audio_bytes, "application/octet-stream"),
        "definition": (None, json.dumps(definition), "application/json"),
    }
    headers = {"Ocp-Apim-Subscription-Key": config.azure_key}

    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(url, headers=headers, files=files)
        if resp.status_code != 200:
            logger.error(
                "azure_fast_transcribe_failed status=%s body=%s",
                resp.status_code, resp.text[:500],
            )
            return None
        data = resp.json()

    phrases = data.get("phrases", []) or []
    segments: list[dict] = []
    for i, p in enumerate(phrases):
        speaker = p.get("speaker")
        label = f"Speaker {speaker}" if speaker is not None else "Speaker 1"
        start_ms = int(p.get("offsetMilliseconds", 0) or 0)
        dur_ms = int(p.get("durationMilliseconds", 0) or 0)
        text = (p.get("text") or "").strip()
        if not text:
            continue
        segments.append(
            {"seq": i, "speaker_label": label, "start_ms": start_ms, "end_ms": start_ms + dur_ms, "text": text}
        )

    duration_ms = int(data.get("durationMilliseconds", 0) or 0)
    duration_sec = round(duration_ms / 1000) if duration_ms else None
    return {"provider": "azure", "segments": segments, "duration_sec": duration_sec}


async def _whisper_transcribe(
    audio_bytes: bytes, filename: str, language: str, config: TranscriptionConfig
) -> dict:
    """OpenAI Whisper 전사(화자 분리 없음) — LiteLLM 경유. 실패 시 빈 세그먼트."""
    import asyncio

    import litellm

    # Whisper 언어 코드는 2글자(예: "ko") — 로케일("ko-KR")이 아님.
    lang2 = (language or "ko").split("-")[0]

    def _call() -> object:
        buf = io.BytesIO(audio_bytes)
        buf.name = filename or "audio.webm"
        return litellm.transcription(
            model=config.stt_model,
            file=buf,
            api_key=config.openai_key,
            language=lang2,
            response_format="verbose_json",
        )

    try:
        transcript = await asyncio.to_thread(_call)
        text = (getattr(transcript, "text", "") or "").strip()
        duration = getattr(transcript, "duration", None)
        segments: list[dict] = []
        whisper_segments = getattr(transcript, "segments", None) or []
        if whisper_segments:
            for i, s in enumerate(whisper_segments):
                seg = s if isinstance(s, dict) else getattr(s, "__dict__", {})
                seg_text = str(seg.get("text", "") or getattr(s, "text", "")).strip()
                if not seg_text:
                    continue
                start = seg.get("start", getattr(s, "start", 0)) or 0
                end = seg.get("end", getattr(s, "end", 0)) or 0
                segments.append(
                    {
                        "seq": i,
                        "speaker_label": "Speaker 1",
                        "start_ms": int(float(start) * 1000),
                        "end_ms": int(float(end) * 1000),
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
    except Exception:
        logger.exception("whisper_transcribe_error")
        return {"provider": "whisper", "segments": [], "duration_sec": None}
