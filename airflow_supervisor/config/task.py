from typing import Optional

from airflow_balancer import Host, Port
from airflow_pydantic import ImportPath, Task, TaskArgs
from pydantic import Field

from .supervisor import SupervisorAirflowConfiguration

__all__ = (
    "SupervisorTaskArgs",
    "SupervisorTask",
)


class SupervisorTaskArgs(TaskArgs, extra="allow"):
    cfg: SupervisorAirflowConfiguration


class SupervisorTask(Task, SupervisorTaskArgs):
    operator: ImportPath = Field(default="airflow_supervisor.Supervisor", validate_default=True)


class SupervisorSSHTaskArgs(TaskArgs, extra="allow"):
    cfg: SupervisorAirflowConfiguration
    host: Optional[Host] = Field(description="The host to connect to for SSH, if not otherwise provided in configs")
    port: Optional[Port] = Field(
        default=None, description="The port to user for Supervisor, if not otherwise provided in configs"
    )


class SupervisorSSHTask(Task, SupervisorSSHTaskArgs):
    operator: ImportPath = Field(default="airflow_supervisor.SupervisorSSH", validate_default=True)
