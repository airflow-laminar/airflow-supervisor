from typing import Type

from airflow_pydantic import ImportPath, Task, TaskArgs
from pydantic import Field, field_validator

from .supervisor import SupervisorAirflowConfiguration

__all__ = (
    "SupervisorOperatorArgs",
    "SupervisorTaskArgs",
    "SupervisorOperator",
    "SupervisorTask",
)


class SupervisorTaskArgs(TaskArgs):
    cfg: SupervisorAirflowConfiguration


# Alias
SupervisorOperatorArgs = SupervisorTaskArgs


class SupervisorTask(Task, SupervisorTaskArgs):
    operator: ImportPath = Field(default="airflow_supervisor.Supervisor", validate_default=True)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: Type) -> Type:
        if not isinstance(v, Type) and issubclass(v, SupervisorAirflowConfiguration):
            raise ValueError(f"operator must be 'airflow_supervisor.Supervisor', got: {v}")
        return v


# Alias
SupervisorOperator = SupervisorTask
