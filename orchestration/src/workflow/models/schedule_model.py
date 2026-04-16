"""WorkflowSchedule DB model — cron-based workflow triggers."""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


class WorkflowSchedule(SQLModel, table=True):
    """Cron schedule that triggers a workflow automatically.

    Fields:
        id          : UUID primary key (used as APScheduler job_id)
        workflow_id : FK to workflow
        user_id     : owner
        cron_expr   : cron expression (e.g. "0 9 * * 1-5")
        input_data  : static input_data passed to each triggered execution
        is_active   : paused schedules are not fired
        created_at  : creation timestamp
        next_run_at : denormalized hint for display
    """

    __tablename__ = "workflow_schedule"

    id: str = Field(primary_key=True)
    workflow_id: str = Field(index=True)
    user_id: int = Field(index=True)
    label: str = Field(default="", max_length=200)
    cron_expr: str = Field(max_length=100)
    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_run_at: Optional[datetime] = Field(default=None, nullable=True)
