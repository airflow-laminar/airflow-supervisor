from typing import List, Optional, Union

from pydantic import Field, field_serializer, field_validator
from supervisor_pydantic import SupervisorConvenienceConfiguration

from .airflow import AirflowConfiguration

__all__ = (
    "SupervisorAirflowConfiguration",
    "SupervisorSSHAirflowConfiguration",
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

    # SSH Kwargs
    ssh_hook: Optional[object] = Field(default=None)
    ssh_conn_id: Optional[str] = Field(default=None)
    remote_host: Optional[str] = Field(default=None)
    conn_timeout: Optional[int] = Field(default=None)
    cmd_timeout: Optional[int] = Field(default=3600)
    environment: Optional[dict] = Field(default=None)
    get_pty: Optional[bool] = Field(default=None)
    banner_timeout: Optional[float] = Field(default=None)
    skip_on_exit_code: Optional[Union[int, List[int]]] = Field(default=None)

    @field_validator("ssh_hook")
    @classmethod
    def _validate_ssh_hook(cls, v):
        if v:
            from airflow.providers.ssh.hooks.ssh import SSHHook

            assert isinstance(v, SSHHook)
        return v

    @field_serializer("ssh_hook")
    def _serialize_hook(self, ssh_hook: object):
        if ssh_hook is not None:
            return "<SSHHook>"
        return None


load_airflow_config = SupervisorAirflowConfiguration.load
load_airflow_ssh_config = SupervisorSSHAirflowConfiguration.load
