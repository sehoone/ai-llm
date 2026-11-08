"""첨부 저장 어댑터 — MinIO(기본) 또는 로컬 디스크 폴백 (ADR-0017, ADR-0014 §1 개정).

`storage_path`(= 오브젝트 키)는 `"{session_id}/{uuid}_{sanitized}"` 상대경로.
MinIO는 S3 호환 — 클라우드 S3 전환은 엔드포인트/자격 설정만. bare 로컬 개발은
`storage_backend=local`로 디스크 폴백. 다운로드는 백엔드가 바이트를 스트리밍 프록시한다
(MinIO 9000은 내부망 — ADR-0017 §4).
"""

from __future__ import annotations

import base64
import io
import re
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from src.core.config import settings

_CHUNK = 32 * 1024


def _sanitize_filename(filename: str) -> str:
    name = Path(filename).name  # 디렉터리 프리픽스 제거 (../../etc/passwd → passwd)
    name = re.sub(r"[^\w\s\-.]", "", name).strip()
    return name or "file"


def _object_key(namespace: int | str, original_filename: str) -> str:
    """네임스페이스(세션 id 또는 문자열 프리픽스) + uuid 프리픽스 (경로/키 주입 방지)."""
    return f"{namespace}/{uuid.uuid4().hex}_{_sanitize_filename(original_filename)}"


class FileStorage(Protocol):
    def save_bytes(self, data: bytes, namespace: int | str, original_filename: str) -> tuple[str, int]:
        """원본 바이트 저장. (storage_path/key, 바이트크기) 반환."""
        ...

    def save_base64(self, data_base64: str, session_id: int, original_filename: str) -> tuple[str, int]:
        """base64 디코드 후 저장. (storage_path/key, 바이트크기) 반환."""
        ...

    def exists(self, key: str) -> bool: ...

    def open_stream(self, key: str) -> Iterator[bytes]:
        """다운로드용 바이트 스트림."""
        ...

    def delete(self, key: str) -> None: ...


class LocalFileStorage:
    """로컬 디스크 저장 (bare 개발·폴백). V2 FileStorageService 동기 이식."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.upload_dir)

    def save_bytes(self, data: bytes, namespace: int | str, original_filename: str) -> tuple[str, int]:
        key = _object_key(namespace, original_filename)
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key, len(data)

    def save_base64(self, data_base64: str, session_id: int, original_filename: str) -> tuple[str, int]:
        return self.save_bytes(base64.b64decode(data_base64), session_id, original_filename)

    def exists(self, key: str) -> bool:
        return (self.base_dir / key).exists()

    def open_stream(self, key: str) -> Iterator[bytes]:
        with (self.base_dir / key).open("rb") as f:
            while chunk := f.read(_CHUNK):
                yield chunk

    def delete(self, key: str) -> None:
        path = self.base_dir / key
        if path.exists():
            path.unlink()


class MinioFileStorage:
    """MinIO(S3 호환) 객체 스토리지. 최초 사용 시 버킷 보장(ADR-0017 §3).

    `bucket`을 지정하면 그 버킷을 쓴다(없으면 `settings.minio_bucket` 기본 — 첨부용). meeting 녹음은
    전용 버킷(`settings.meeting_audio_bucket`)을 주입해 첨부와 분리 저장한다.
    """

    def __init__(self, bucket: str | None = None) -> None:
        from minio import Minio

        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = bucket or settings.minio_bucket
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def save_bytes(self, data: bytes, namespace: int | str, original_filename: str) -> tuple[str, int]:
        key = _object_key(namespace, original_filename)
        self._client.put_object(self._bucket, key, io.BytesIO(data), length=len(data))
        return key, len(data)

    def save_base64(self, data_base64: str, session_id: int, original_filename: str) -> tuple[str, int]:
        return self.save_bytes(base64.b64decode(data_base64), session_id, original_filename)

    def exists(self, key: str) -> bool:
        from minio.error import S3Error

        try:
            self._client.stat_object(self._bucket, key)
            return True
        except S3Error:
            return False

    def open_stream(self, key: str) -> Iterator[bytes]:
        resp = self._client.get_object(self._bucket, key)
        try:
            yield from resp.stream(_CHUNK)
        finally:
            resp.close()
            resp.release_conn()

    def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)


_storage_cache: dict[str | None, FileStorage] = {}


def get_storage(bucket: str | None = None) -> FileStorage:
    """설정에 따른 스토리지 어댑터(버킷별 프로세스 싱글턴). 클라이언트는 최초 호출 시 지연 생성.

    `bucket=None`이면 기본 첨부 버킷(`settings.minio_bucket`). meeting 녹음 등은 전용 버킷을 넘긴다.
    local 백엔드는 버킷 개념이 없어 동일 디스크 루트를 쓴다(오브젝트 키 프리픽스로 분리).
    """
    if bucket not in _storage_cache:
        if settings.storage_backend == "minio":
            _storage_cache[bucket] = MinioFileStorage(bucket=bucket)
        else:
            _storage_cache[bucket] = LocalFileStorage()
    return _storage_cache[bucket]
