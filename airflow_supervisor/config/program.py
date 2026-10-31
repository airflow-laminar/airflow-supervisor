from datetime import timedelta

from pydantic import BaseModel, Field

__all__ = ("ProgramLifecycleConfiguration",)


class ProgramLifecycleConfiguration(BaseModel):
    """Airflow lifecycle policy for a Supervisor program group."""

    start_after: list[str] = Field(default_factory=list)
    start_delay: timedelta = Field(default=timedelta(0), ge=timedelta(0))
    stop_before: list[str] = Field(default_factory=list)
    retries: int = Field(default=0, ge=0)
    retry_delay: timedelta = Field(default=timedelta(seconds=30), ge=timedelta(0))
    required: bool = True
    max_consecutive_failures: int | None = Field(default=None, gt=0)
