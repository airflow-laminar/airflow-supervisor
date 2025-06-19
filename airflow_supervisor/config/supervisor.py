from typing import Optional

from airflow_pydantic import SSHOperatorArgs
from pydantic import Field
from supervisor_pydantic import SupervisorConvenienceConfiguration

from .airflow import AirflowConfiguration

__all__ = (
    "SupervisorAirflowConfiguration",
    "SupervisorSSHAirflowConfiguration",
    "SSHOperatorArgs",
    "load_airflow_config",
    "load_airflow_ssh_config",
)


class SupervisorAirflowConfiguration(SupervisorConvenienceConfiguration):
    airflow: AirflowConfiguration = Field(
        default_factory=AirflowConfiguration, description="Required options for airflow integration"
    )

    # Should the programs be stopped when the DAG finishes?
    stop_on_exit: Optional[bool] = Field(default=True, description="Stop supervisor on dag completion")
    # Should the supervisor folder be removed on dag completion?
    cleanup: Optional[bool] = Field(
        default=True, description="Cleanup supervisor folder on dag completion. Note: stop_on_exit must be True"
    )
    # For Jobs that do not shutdown, e.g. stop_on_exit=False, one might want to configure them to
    # restart when the DAG is rescheduled by airflow or retriggered by airflow-ha
    restart_on_initial: Optional[bool] = Field(
        default=False,
        description="Restart the job when the DAG is run directly via airflow (NOT retriggered). This is useful for jobs that do not shutdown",
    )
    restart_on_retrigger: Optional[bool] = Field(
        default=False,
        description="Restart the job when the DAG is retriggered. This is useful for jobs that do not shutdown",
    )


class SupervisorSSHAirflowConfiguration(SupervisorAirflowConfiguration):
    command_prefix: Optional[str] = Field(default="")

    ssh_operator_args: Optional[SSHOperatorArgs] = Field(
        default_factory=SSHOperatorArgs,
        description="SSH Operator arguments to use for remote execution.",
    )


load_airflow_config = SupervisorAirflowConfiguration.load
load_airflow_ssh_config = SupervisorSSHAirflowConfiguration.load
