"""transcription: 음성 전사(STT) + 회의록 생성 — meeting용 (ADR-0005).

- `transcribe`: 오디오 바이트 → 화자별 세그먼트 (Azure Fast Transcription 주, Whisper 폴백).
- `generate_minutes` / `minutes_to_markdown`: 전사 → 구조화 회의록 → 마크다운.

engine 경계: `domains`·FastAPI 비의존. 외부 서비스·LLM 설정은 도메인이 주입한다.
"""

from src.engine.transcription.minutes import generate_minutes, minutes_to_markdown
from src.engine.transcription.stt import TranscriptionConfig, transcribe

__all__ = ["TranscriptionConfig", "transcribe", "generate_minutes", "minutes_to_markdown"]
