"""Audio storage for meetings.

Uses MinIO / S3-compatible object storage when ``MEETING_S3_ENDPOINT`` is set
(persistent and shared across replicas); otherwise falls back to the local
filesystem under ``MEETING_AUDIO_DIR`` (suitable for single-node local dev).

The interface (``save`` / ``exists`` / ``delete`` / serving helpers) is backend
agnostic so call sites don't care which storage is active.
"""

import os
import uuid
from typing import Optional

from src.common.config import settings
from src.common.logging import logger

_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
}

_ALLOWED_EXT = set(_CONTENT_TYPES.keys())


class StorageService:
    """Persist and retrieve meeting audio by an opaque object key."""

    def __init__(self) -> None:
        self.use_s3 = bool(settings.MEETING_S3_ENDPOINT)
        self.bucket = settings.MEETING_S3_BUCKET
        self._client = None
        self._bucket_ready = False
        if self.use_s3:
            logger.info("meeting_storage_s3", endpoint=settings.MEETING_S3_ENDPOINT, bucket=self.bucket)
        else:
            self.base_dir = settings.MEETING_AUDIO_DIR
            os.makedirs(self.base_dir, exist_ok=True)
            logger.info("meeting_storage_local", dir=self.base_dir)

    # ── backend selection helpers ─────────────────────────────────────────────

    def _s3(self):
        """Lazily build the boto3 S3 client (path-style for MinIO)."""
        if self._client is None:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "s3",
                endpoint_url=settings.MEETING_S3_ENDPOINT,
                aws_access_key_id=settings.MEETING_S3_ACCESS_KEY,
                aws_secret_access_key=settings.MEETING_S3_SECRET_KEY,
                region_name=settings.MEETING_S3_REGION,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        return self._client

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        from botocore.exceptions import ClientError

        client = self._s3()
        try:
            client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                client.create_bucket(Bucket=self.bucket)
                logger.info("meeting_bucket_created", bucket=self.bucket)
            except ClientError as e:
                # Another worker may have created it concurrently.
                logger.warning("meeting_bucket_create_failed", bucket=self.bucket, error=str(e))
        self._bucket_ready = True

    @staticmethod
    def _safe_ext(filename: str) -> str:
        ext = os.path.splitext(filename or "")[1].lower()
        return ext if ext in _ALLOWED_EXT else ".webm"

    def content_type_for(self, object_key: str) -> str:
        """Best-effort audio MIME type for an object key."""
        ext = os.path.splitext(object_key)[1].lower()
        return _CONTENT_TYPES.get(ext, "application/octet-stream")

    def path_for(self, object_key: str) -> str:
        """Absolute local path for an object key (local backend only)."""
        return os.path.join(self.base_dir, object_key)

    # ── write / existence / delete (sync; call via asyncio.to_thread) ─────────

    def save_sync(self, data: bytes, filename: str) -> str:
        """Write audio bytes and return an object key."""
        ext = self._safe_ext(filename)
        key = f"{uuid.uuid4().hex}{ext}"
        if self.use_s3:
            self._ensure_bucket()
            self._s3().put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=self.content_type_for(key)
            )
        else:
            with open(self.path_for(key), "wb") as f:
                f.write(data)
        logger.info("meeting_audio_saved", key=key, bytes=len(data), backend="s3" if self.use_s3 else "local")
        return key

    def exists(self, object_key: str) -> bool:
        if self.use_s3:
            from botocore.exceptions import ClientError

            try:
                self._s3().head_object(Bucket=self.bucket, Key=object_key)
                return True
            except ClientError:
                return False
        return os.path.exists(self.path_for(object_key))

    def delete_sync(self, object_key: str) -> None:
        try:
            if self.use_s3:
                self._s3().delete_object(Bucket=self.bucket, Key=object_key)
            else:
                full = self.path_for(object_key)
                if os.path.exists(full):
                    os.remove(full)
            logger.info("meeting_audio_deleted", key=object_key, backend="s3" if self.use_s3 else "local")
        except Exception as e:
            logger.warning("meeting_audio_delete_failed", key=object_key, error=str(e))

    def download_to_temp(self, object_key: str) -> str:
        """Download an S3 object to a temp file and return its path (caller removes it).

        Transcription reads the audio by file path; with the S3 backend there is
        no local path, so materialize one. For the local backend this is unused.
        """
        import tempfile

        resp = self._s3().get_object(Bucket=self.bucket, Key=object_key)
        data = resp["Body"].read()
        ext = os.path.splitext(object_key)[1] or ".webm"
        fd, path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path

    # ── read / stream for the /audio endpoint ─────────────────────────────────

    def get_object(self, object_key: str, range_header: Optional[str] = None) -> dict:
        """Fetch an object from S3 for streaming (optionally a byte range).

        Returns a dict with ``body`` (StreamingBody), ``content_length``,
        ``content_type``, ``content_range`` (None if full), and ``status`` (200/206).
        S3 backend only — the local backend serves via FileResponse instead.
        """
        kwargs = {"Bucket": self.bucket, "Key": object_key}
        if range_header:
            kwargs["Range"] = range_header
        resp = self._s3().get_object(**kwargs)
        return {
            "body": resp["Body"],
            "content_length": resp.get("ContentLength"),
            "content_type": resp.get("ContentType") or self.content_type_for(object_key),
            "content_range": resp.get("ContentRange"),
            "status": 206 if range_header and resp.get("ContentRange") else 200,
        }


storage_service = StorageService()
