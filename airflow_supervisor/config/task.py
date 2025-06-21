from typing import Optional, Type

from airflow_balancer import Host, Port
from airflow_pydantic import ImportPath, Task, TaskArgs
from pydantic import Field, field_validator

from .supervisor import SupervisorAirflowConfiguration, SupervisorSSHAirflowConfiguration

__all__ = (
    "SupervisorOperatorArgs",
    "SupervisorTaskArgs",
    "SupervisorOperator",
    "SupervisorTask",
)


class SupervisorTaskArgs(TaskArgs, extra="allow"):
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


class SupervisorSSHTaskArgs(TaskArgs, extra="allow"):
    cfg: SupervisorAirflowConfiguration
    host: Optional[Host] = Field(description="The host to connect to for SSH, if not otherwise provided in configs")
    port: Optional[Port] = Field(
        default=None, description="The port to user for Supervisor, if not otherwise provided in configs"
    )


class SupervisorSSHTask(Task, SupervisorSSHTaskArgs):
    operator: ImportPath = Field(default="airflow_supervisor.SupervisorSSH", validate_default=True)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: Type) -> Type:
        if not isinstance(v, Type) and issubclass(v, SupervisorSSHAirflowConfiguration):
            raise ValueError(f"operator must be 'airflow_supervisor.SupervisorSSH', got: {v}")
        return v
