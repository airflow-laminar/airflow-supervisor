from typing import Optional

from airflow_pydantic import SSHOperatorArgs
from pydantic import Field
from supervisor_pydantic import SupervisorLocation

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

    # NOTE: Override in base-base class
    local_or_remote: Optional[SupervisorLocation] = Field(
        default="remote",
        description="Location of supervisor, either local for same-machine or remote. If same-machine, communicates via Unix sockets by default, if remote, communicates via inet http server",
    )


load_airflow_ssh_config = SupervisorSSHAirflowConfiguration.load
