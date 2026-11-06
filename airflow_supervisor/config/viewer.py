from datetime import timedelta

from airflow_pydantic import BaseModel
from pydantic import Field, HttpUrl, field_serializer

from .supervisor import SupervisorAirflowConfiguration

__all__ = ("SupervisorViewerConfiguration", "SupervisorViewerInstance")


class SupervisorViewerInstance(BaseModel):
    cfg: SupervisorAirflowConfiguration
    run_url: HttpUrl | None = None
    log_url: HttpUrl | None = None


class SupervisorViewerConfiguration(BaseModel):
    instances: dict[str, SupervisorViewerInstance] = Field(min_length=1)
    variable_key: str = "airflow-supervisor:instances"
    timeout: float = Field(default=3, gt=0, le=30)
    max_age: timedelta = Field(default=timedelta(minutes=2), gt=timedelta(0))

    @field_serializer("instances")
    def _dump_instances(self, values):
        # Task instantiation must pass plain credentials, not SecretStr objects.
        return {name: value.model_dump(mode="json", exclude_unset=True) for name, value in values.items()}
