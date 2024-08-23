from airflow.models.operator import Operator
from airflow.operators.python import PythonOperator
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.providers.ssh.operators.ssh import SSHOperator
from typing import Dict, List, Optional, Union

from airflow_supervisor.config import SupervisorConfiguration

from .common import SupervisorCommon, _SupervisorTaskStep


class SupervisorRemote(SupervisorCommon):
    # Mimic SSH Operator: https://airflow.apache.org/docs/apache-airflow-providers-ssh/stable/_api/airflow/providers/ssh/operators/ssh/index.html
    def __init__(
        self,
        supervisor_cfg: SupervisorConfiguration,
        command_prefix: str = "",
        ssh_hook: Optional[SSHHook] = None,
        ssh_conn_id: Optional[str] = None,
        remote_host: Optional[str] = None,
        conn_timeout: Optional[int] = None,
        cmd_timeout: Optional[int] = None,
        environment: Optional[dict] = None,
        get_pty: Optional[bool] = None,
        banner_timeout: Optional[float] = None,
        skip_on_exit_code: Optional[Union[int, List[int]]] = None,
        **kwargs,
    ):
        self._command_prefix = command_prefix
        self._ssh_operator_kwargs = {}
        if ssh_hook:
            self._ssh_operator_kwargs["ssh_hook"] = ssh_hook
        if ssh_conn_id:
            self._ssh_operator_kwargs["ssh_conn_id"] = ssh_conn_id
        if remote_host:
            self._ssh_operator_kwargs["remote_host"] = remote_host
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
        super().__init__(supervisor_cfg=supervisor_cfg, _airflow_supervisor_offset=2, **kwargs)

    def get_base_operator_kwargs(self) -> Dict:
        return dict(dag=self, **self._ssh_operator_kwargs)

    def get_step_kwargs(self, step: _SupervisorTaskStep) -> Dict:
        return dict(command=f"{self._command_prefix}")

    def get_step_operator(self, step: _SupervisorTaskStep) -> Operator:
        if step in ("configure-supervisor", "start-supervisor", "unconfigure-supervisor", "force-kill"):
            # These steps use the SSHOperator
            return SSHOperator(
                **{"task_id": f"{self.dag_id}-{step}", **self.get_base_operator_kwargs(), **self.get_step_kwargs(step)}
            )
        # Other steps can go via PythonOperator and the XMLRPC API
        return PythonOperator(
            **{
                "task_id": f"{self.dag_id}-{step}",
                **super().get_base_operator_kwargs(),
                **super().get_step_kwargs(step),
            }
        )
