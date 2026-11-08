"""비동기 키워드/임베딩 생성 진행률 추적용 인메모리 작업 레지스트리.

서버 재시작 시 초기화(수용 가능한 트레이드오프). 단일 프로세스 가정 — 멀티 워커면 공유 안 됨.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

_jobs: dict[str, "UploadJob"] = {}


@dataclass
class UploadJob:
    job_id: str
    total: int
    processed: int = 0
    failed: int = 0
    status: Literal["running", "done"] = "running"
    recent: list[dict] = field(default_factory=list)  # 최근 완료 10건


def create_job(total: int) -> UploadJob:
    job = UploadJob(job_id=str(uuid.uuid4()), total=total)
    _jobs[job.job_id] = job
    return job


def get_job(job_id: str) -> UploadJob | None:
    return _jobs.get(job_id)


def record_done(job_id: str, success: bool, doc_info: dict | None = None) -> None:
    job = _jobs.get(job_id)
    if not job:
        return
    if success:
        job.processed += 1
        if doc_info:
            job.recent.insert(0, doc_info)
            if len(job.recent) > 10:
                job.recent.pop()
    else:
        job.failed += 1
    if job.processed + job.failed >= job.total:
        job.status = "done"
