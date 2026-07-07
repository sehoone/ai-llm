"""In-memory upload job tracker for async keyword generation progress."""

import uuid
from dataclasses import dataclass, field
from typing import Literal

# Module-level job registry — cleared on server restart (acceptable trade-off)
_jobs: dict[str, "UploadJob"] = {}


@dataclass
class UploadJob:
    job_id: str
    total: int
    processed: int = 0
    failed: int = 0
    status: Literal["running", "done"] = "running"
    recent: list[dict] = field(default_factory=list)  # last 10 completed docs


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
