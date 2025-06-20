from logging import getLogger
from shlex import quote
from typing import Dict

from airflow.models.dag import DAG
from airflow.models.operator import Operator
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow_balancer import Host, Port
from airflow_pydantic import SSHOperatorArgs
from supervisor_pydantic.convenience import SupervisorTaskStep

from airflow_supervisor.config import SupervisorSSHAirflowConfiguration

from .local import Supervisor

__all__ = ("SupervisorSSH",)

_log = getLogger(__name__)


class SupervisorSSH(Supervisor):
    # Mimic SSH Operator: https://airflow.apache.org/docs/apache-airflow-providers-ssh/stable/_api/airflow/providers/ssh/operators/ssh/index.html
    def __init__(
        self,
        dag: DAG,
        cfg: SupervisorSSHAirflowConfiguration,
        host: "Host" = None,
        port: "Port" = None,
        **kwargs,
    ):
        for attr in ("command_prefix",):
            if attr in kwargs:
                _log.info(f"Setting {attr} to {kwargs.get(attr)}")
                setattr(self, f"_{attr}", kwargs.pop(attr))
            elif cfg and getattr(cfg, attr):
                _log.info(f"Setting {attr} to {getattr(cfg, attr)}")
                setattr(self, f"_{attr}", getattr(cfg, attr))
            else:
                _log.info(f"Setting {attr} to empty string")
                setattr(self, f"_{attr}", "")

        self._ssh_operator_kwargs = cfg.ssh_operator_args.model_dump(exclude_none=True)

        pydantic_fields = (
            cfg.ssh_operator_args.__pydantic_fields__.keys()
            if hasattr(cfg.ssh_operator_args, "__pydantic_fields__")
            else cfg.ssh_operator_args.__fields__
        )
        for attr in pydantic_fields:
            if attr in kwargs:
                _log.info(f"Setting {attr} to {kwargs.get(attr)}")
                self._ssh_operator_kwargs[attr] = kwargs.pop(attr)
                setattr(cfg, attr, self._ssh_operator_kwargs[attr])

        # Integrate with airflow-balancer, use host if provided
        if host:
            _log.info(f"Setting host to {host.name}")
            self._ssh_operator_kwargs["remote_host"] = host.name
            self._ssh_operator_kwargs["ssh_hook"] = host.hook()
            cfg.ssh_operator_args = SSHOperatorArgs(**self._ssh_operator_kwargs)

            # Ensure host matches the configuration
            cfg.convenience.host = host.name

            # Extract pool if available
            if host.pool and not cfg.airflow.pool:
                _log.info(f"Setting airflow pool to {host.pool}")
                cfg.airflow.pool = host.pool

        if port:
            _log.info(f"Setting port to {port.port}")
            # Ensure port matches the configuration
            cfg.convenience.port = f"*:{port.port}"

        if host or port:
            # revalidate
            _log.info("Revalidating configuration")
            cfg._setup_convenience_defaults()

        super().__init__(dag=dag, cfg=cfg, **kwargs)

    def get_step_kwargs(self, step: SupervisorTaskStep) -> Dict:
        if step == "configure-supervisor":
            # TODO
            return {
                **self._ssh_operator_kwargs,
                "command": f"""
{self._command_prefix}
_supervisor_convenience {step} '{self._cfg.model_dump_json()}'
""",
            }
        elif step in ("start-supervisor", "stop-supervisor", "unconfigure-supervisor", "force-kill"):
            # must be done via SSH
            return {
                **self._ssh_operator_kwargs,
                "command": f"""
{self._command_prefix}
_supervisor_convenience {step} --cfg {quote(str(self._cfg._pydantic_path))}
""",
            }
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
                    "task_id": f"{self._dag.dag_id}-{step}",
                    **self.get_base_operator_kwargs(),
                    **self.get_step_kwargs(step),
                }
            )
        else:
            # can be done via XMLRPC API
            return super().get_step_operator(step=step)
