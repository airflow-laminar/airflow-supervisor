from airflow_pydantic import ImportPath, Task, TaskArgs
from pydantic import Field, field_validator

from .supervisor import SupervisorAirflowConfiguration

__all__ = (
    "SupervisorOperator",
    "SupervisorOperatorArgs",
    "SupervisorTask",
    "SupervisorTaskArgs",
)


class SupervisorTaskArgs(TaskArgs):
    cfg: SupervisorAirflowConfiguration


# Alias
SupervisorOperatorArgs = SupervisorTaskArgs


class SupervisorTask(Task, SupervisorTaskArgs):
    operator: ImportPath = Field(default="airflow_supervisor.Supervisor", validate_default=True)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: type) -> type:
        if not isinstance(v, type) and issubclass(v, SupervisorAirflowConfiguration):
            raise TypeError(f"operator must be 'airflow_supervisor.Supervisor', got: {v}")
        return v


# Alias
SupervisorOperator = SupervisorTask
