"""artifact 도메인 — 스트리밍 산출물·버전관리·공개 링크 (ADR-0013).

공개 포트: `ArtifactIngest` (타 도메인이 버전·발행 인프라를 재사용). 내부 모듈은 캡슐화.
"""

from src.domains.artifact.ports import ArtifactIngest

__all__ = ["ArtifactIngest"]
