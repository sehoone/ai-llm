"""문서 본문 추출 (ADR-0016) — 바이트 → 텍스트.

재사용 가능한 엔진 능력(ADR-0005): `domains`·FastAPI 비의존. 도메인이 첨부 바이트를
넘기면 markdown 텍스트를 돌려준다. RAG 인제스트 등에서 재사용 가능.
"""

from src.engine.extraction.markitdown import ExtractResult, ExtractStatus, extract_text

__all__ = ["ExtractResult", "ExtractStatus", "extract_text"]
