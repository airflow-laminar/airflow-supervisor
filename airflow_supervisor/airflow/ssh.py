from shlex import quote
from typing import Dict

from airflow.models.dag import DAG
from airflow.models.operator import Operator
from airflow.providers.ssh.operators.ssh import SSHOperator

from airflow_supervisor.config import SupervisorSSHAirflowConfiguration

from .common import SupervisorTaskStep
from .local import Supervisor

__all__ = ("SupervisorSSH",)


class SupervisorSSH(Supervisor):
    # Mimic SSH Operator: https://airflow.apache.org/docs/apache-airflow-providers-ssh/stable/_api/airflow/providers/ssh/operators/ssh/index.html
    def __init__(
        self,
        dag: DAG,
        cfg: SupervisorSSHAirflowConfiguration,
        **kwargs,
    ):
        for attr in ("command_prefix", "command_noescape"):
            if attr in kwargs:
                setattr(self, f"_{attr}", kwargs.pop(attr))
            elif cfg and getattr(cfg, attr):
                setattr(self, f"_{attr}", getattr(cfg, attr))

        self._ssh_operator_kwargs = {}
        for attr in (
            "ssh_hook",
            "ssh_conn_id",
            "remote_host",
            "conn_timeout",
            "cmd_timeout",
            "environment",
            "get_pty",
            "banner_timeout",
            "skip_on_exit_code",
        ):
            if attr in kwargs:
                self._ssh_operator_kwargs[attr] = kwargs.pop(attr)
            elif cfg and getattr(cfg, attr):
                self._ssh_operator_kwargs[attr] = getattr(cfg, attr)

        super().__init__(dag=dag, cfg=cfg, **kwargs)

    def get_base_operator_kwargs(self) -> Dict:
        return dict(dag=self, **self._ssh_operator_kwargs)

    def get_step_kwargs(self, step: SupervisorTaskStep) -> Dict:
        if step == "configure-supervisor":
            # TODO
            return dict(
                command=f"""
{self._command_noescape}
{quote(self._command_prefix)}
_airflow_supervisor_command {step} {self._supervisor_cfg.model_dump_json()}
"""
            )
        elif step in ("start-supervisor", "stop-supervisor", "unconfigure-supervisor", "force-kill"):
            # must be done via SSH
            return dict(
                command=f"""
{self._command_noescape}
{quote(self._command_prefix)}
_airflow_supervisor_command {step} --cfg {self._supervisor_cfg._pydantic_path}
"""
            )
        else:
            # can be done via XMLRPC API
            return super().get_step_kwargs(step=step)

    def get_step_operator(self, step: SupervisorTaskStep) -> Operator:
        if step in (
            "configure-supervisor",
            "start-supervisor",
            "stop-supervisor",
            "unconfigure-supervisor",
            "force-kill",
        ):
            return SSHOperator(
                **{
                    "task_id": f"{self.dag.dag_id}-{step}",
                    **self.get_base_operator_kwargs(),
                    **self.get_step_kwargs(step),
                }
            )
        else:
            # can be done via XMLRPC API
            return super().get_step_operator(step=step)
