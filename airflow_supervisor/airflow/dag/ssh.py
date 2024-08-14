from typing import List, Optional, Union

from airflow.providers.ssh.hooks.ssh import SSHHook

from airflow_supervisor.config import SupervisorConfiguration

from .common import SupervisorCommon


class SupervisorRemote(SupervisorCommon):
    # Mimic SSH Operator: https://airflow.apache.org/docs/apache-airflow-providers-ssh/stable/_api/airflow/providers/ssh/operators/ssh/index.html
    def __init__(
        self,
        supervisor_cfg: SupervisorConfiguration,
        ssh_hook: Optional[SSHHook] = None,
        ssh_conn_id: Optional[str] = None,
        remote_host: Optional[str] = None,
        command: Optional[str] = None,
        conn_timeout: Optional[int] = None,
        cmd_timeout: Optional[int] = None,
        environment: Optional[dict] = None,
        get_pty: Optional[bool] = None,
        banner_timeout: Optional[float] = None,
        skip_on_exit_code: Optional[Union[int, List[int]]] = None,
        **kwargs,
    ):
        super().__init__(supervisor_cfg=supervisor_cfg, **kwargs)
        self._supervisor_cfg = supervisor_cfg
        self._ssh_operator_kwargs = {}
        if ssh_hook:
            self._ssh_operator_kwargs["ssh_hook"] = ssh_hook
        if ssh_conn_id:
            self._ssh_operator_kwargs["ssh_conn_id"] = ssh_conn_id
        if remote_host:
            self._ssh_operator_kwargs["remote_host"] = remote_host
        if command:
            self._ssh_operator_kwargs["command"] = command
        if conn_timeout:
            self._ssh_operator_kwargs["conn_timeout"] = conn_timeout
        if cmd_timeout:
            self._ssh_operator_kwargs["cmd_timeout"] = cmd_timeout
        if environment:
            self._ssh_operator_kwargs["environment"] = environment
        if get_pty:
            self._ssh_operator_kwargs["get_pty"] = get_pty
        if banner_timeout:
            self._ssh_operator_kwargs["banner_timeout"] = banner_timeout
        if skip_on_exit_code:
            self._ssh_operator_kwargs["skip_on_exit_code"] = skip_on_exit_code
