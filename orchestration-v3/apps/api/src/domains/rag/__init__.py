"""rag: 문서 업로드·검색 (pgvector, ADR-0012).

공개 포트: `RagService`·`SearchRequest` (chat·workflow가 지식베이스 검색에 사용). 내부 모듈은 캡슐화.
"""

from src.domains.rag.schema import SearchRequest
from src.domains.rag.service import RagService

__all__ = ["RagService", "SearchRequest"]
