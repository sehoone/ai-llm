"""Local filesystem storage for chat file attachments."""

import asyncio
import base64
import uuid
from pathlib import Path

from src.common.logging import logger


class FileStorageService:
    """Saves and loads attachment files from the local filesystem.

    storage_path values stored in DB are relative to base_dir,
    so the service is relocatable without a DB migration.
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    def _ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    async def save(self, data_base64: str, session_id: str, original_filename: str) -> tuple[str, int]:
        """Decode base64 data and write to disk.

        Returns:
            (relative_path, file_size_bytes)
        """
        def _sync() -> tuple[str, int]:
            dir_path = self.base_dir / session_id
            self._ensure_dir(dir_path)

            unique_name = f"{uuid.uuid4().hex}_{original_filename}"
            file_path = dir_path / unique_name

            raw = base64.b64decode(data_base64)
            file_path.write_bytes(raw)

            relative = str(Path(session_id) / unique_name)
            logger.info("attachment_saved", path=relative, size=len(raw))
            return relative, len(raw)

        return await asyncio.to_thread(_sync)

    def absolute_path(self, relative_path: str) -> Path:
        return self.base_dir / relative_path

    async def delete(self, relative_path: str) -> None:
        def _sync() -> None:
            path = self.base_dir / relative_path
            if path.exists():
                path.unlink()
                logger.info("attachment_deleted", path=relative_path)

        await asyncio.to_thread(_sync)
