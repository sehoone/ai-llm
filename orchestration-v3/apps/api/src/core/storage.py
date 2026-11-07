"""로컬 파일시스템 첨부 저장 (ADR-0014). V2 FileStorageService를 동기로 이식.

storage_path는 base_dir 상대경로로 저장해 재배치 가능. 파일명은 sanitize + uuid 프리픽스로
경로 주입을 막는다. S3/MinIO 전환 시 이 모듈을 어댑터로 교체한다.
"""

from __future__ import annotations

import base64
import re
import uuid
from pathlib import Path

from src.core.config import settings


def _sanitize_filename(filename: str) -> str:
    name = Path(filename).name  # 디렉터리 프리픽스 제거 (../../etc/passwd → passwd)
    name = re.sub(r"[^\w\s\-.]", "", name).strip()
    return name or "file"


class FileStorage:
    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.upload_dir)

    def save_base64(self, data_base64: str, session_id: int, original_filename: str) -> tuple[str, int]:
        """base64를 디코드해 디스크에 저장. (상대경로, 바이트크기) 반환."""
        dir_path = self.base_dir / str(session_id)
        dir_path.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{_sanitize_filename(original_filename)}"
        raw = base64.b64decode(data_base64)
        (dir_path / unique_name).write_bytes(raw)
        relative = str(Path(str(session_id)) / unique_name)
        return relative, len(raw)

    def absolute_path(self, relative_path: str) -> Path:
        return self.base_dir / relative_path

    def delete(self, relative_path: str) -> None:
        path = self.base_dir / relative_path
        if path.exists():
            path.unlink()
