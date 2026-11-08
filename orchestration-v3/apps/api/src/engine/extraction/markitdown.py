"""markitdown 어댑터 — PDF·Office·HTML 등 다포맷 → markdown (ADR-0016 §2).

markitdown의 안정 API(`convert(path)`)를 쓰기 위해 바이트를 임시 파일로 떨군다(버전 간
`convert_stream` 시그니처 변동 회피). 무거운 추이적 의존성은 지연 import로 미사용 시 비용 회피.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

ExtractStatus = Literal["ok", "empty", "truncated", "unsupported"]


@dataclass(frozen=True)
class ExtractResult:
    text: str
    status: ExtractStatus
    note: str | None = None  # "추출 가능한 텍스트 없음(스캔 이미지 가능성)" 등


def extract_text(
    data: bytes, content_type: str, filename: str, *, max_chars: int = 50_000
) -> ExtractResult:
    """바이트에서 본문 텍스트(markdown)를 추출한다.

    - 결과가 공백이면 `empty`(스캔 PDF 등 텍스트 레이어 없음).
    - `max_chars` 초과 시 잘라 `truncated`.
    - 추출기 미설치·변환 실패·미지원 포맷은 `unsupported`.
    """
    try:
        from markitdown import MarkItDown
    except Exception:
        logger.exception("markitdown_import_failed")
        return ExtractResult(text="", status="unsupported", note="추출기 미설치")

    suffix = Path(filename).suffix.lower()
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        result = MarkItDown().convert(tmp_path)
        text = (result.text_content or "").strip()
    except Exception:
        logger.exception("extract_failed", extra={"filename": filename, "content_type": content_type})
        return ExtractResult(text="", status="unsupported", note="본문 추출 실패")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                logger.warning("extract_tmp_cleanup_failed", extra={"path": tmp_path})

    if not text:
        return ExtractResult(
            text="", status="empty", note="추출 가능한 텍스트 없음(스캔 이미지 가능성)"
        )
    if len(text) > max_chars:
        return ExtractResult(text=text[:max_chars], status="truncated")
    return ExtractResult(text=text, status="ok")
