from typing import Optional

from airflow_pydantic import SSHOperatorArgs
from pydantic import Field

from .supervisor import SupervisorAirflowConfiguration

__all__ = (
    "SupervisorSSHAirflowConfiguration",
    "SSHOperatorArgs",  # reexport
    "load_airflow_ssh_config",
)


class SupervisorSSHAirflowConfiguration(SupervisorAirflowConfiguration):
    command_prefix: Optional[str] = Field(default="")

    ssh_operator_args: Optional[SSHOperatorArgs] = Field(
        default=None,
        description="SSH Operator arguments to use for remote execution.",
    )


load_airflow_ssh_config = SupervisorSSHAirflowConfiguration.load
