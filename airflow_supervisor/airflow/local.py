from typing import Dict

from airflow.models.dag import DAG
from airflow.models.operator import Operator
from airflow.operators.python import PythonOperator
from airflow_ha import Action, CheckResult, HighAvailabilityOperator, Result

from airflow_supervisor.client import SupervisorRemoteXMLRPCClient
from airflow_supervisor.config import SupervisorAirflowConfiguration

from .common import SupervisorTaskStep, skip_

__all__ = ("Supervisor",)


class Supervisor(DAG):
    _supervisor_cfg: SupervisorAirflowConfiguration
    _supervisor_kill: DAG
    _supervisor_xmlrpc_client: SupervisorRemoteXMLRPCClient

    def __init__(self, supervisor_cfg: SupervisorAirflowConfiguration, **kwargs):
        # store config
        self._supervisor_cfg = supervisor_cfg
        self._supervisor_xmlrpc_client = kwargs.pop(
            "supervisor_xmlrpc_client", SupervisorRemoteXMLRPCClient(self._supervisor_cfg)
        )

        # setup role and tweak dag id
        if "dag_id" not in kwargs:
            kwargs["dag_id"] = list(self._supervisor_cfg.program.keys())[0]

        # override dag kwargs that dont make sense
        kwargs["catchup"] = False
        kwargs["concurrency"] = 1
        kwargs["max_active_tasks"] = 1
        kwargs["max_active_runs"] = 1

        # init with base DAG
        super().__init__(**kwargs)

        # initialize tasks
        self.initialize_tasks()

        self.configure_supervisor >> self.start_supervisor >> self.start_programs >> self.check_programs
        # fail, restart
        self.check_programs.retrigger_fail >> self.restart_programs
        # pass, finish
        self.check_programs.stop_pass >> self.stop_programs >> self.stop_supervisor >> self.unconfigure_supervisor

        # TODO make helper dag
        self._force_kill = self.get_step_operator("force-kill")
        # Default non running
        PythonOperator(task_id="skip", python_callable=skip_) >> self._force_kill

    def initialize_tasks(self):
        # tasks
        self._configure_supervisor = self.get_step_operator(step="configure-supervisor")
        self._start_supervisor = self.get_step_operator(step="start-supervisor")
        self._start_programs = self.get_step_operator("start-programs")
        self._stop_programs = self.get_step_operator("stop-programs")
        self._restart_programs = self.get_step_operator("restart-programs")
        self._stop_supervisor = self.get_step_operator("stop-supervisor")
        self._unconfigure_supervisor = self.get_step_operator("unconfigure-supervisor")

        # TODO check programs should be sensor
        self._check_programs = self.get_step_operator("check-programs")

    @property
    def configure_supervisor(self) -> Operator:
        return self._configure_supervisor

    @property
    def start_supervisor(self) -> Operator:
        return self._start_supervisor

    @property
    def start_programs(self) -> Operator:
        return self._start_programs

    @property
    def check_programs(self) -> HighAvailabilityOperator:
        return self._check_programs

    @property
    def stop_programs(self) -> Operator:
        return self._stop_programs

    @property
    def restart_programs(self) -> Operator:
        return self._restart_programs

    @property
    def stop_supervisor(self) -> Operator:
        return self._stop_supervisor

    @property
    def unconfigure_supervisor(self) -> Operator:
        return self._unconfigure_supervisor

    @property
    def supervisor_client(self) -> SupervisorRemoteXMLRPCClient:
        return SupervisorRemoteXMLRPCClient(self._supervisor_cfg)

    def get_base_operator_kwargs(self) -> Dict:
        return dict(dag=self)

    def get_step_kwargs(self, step: SupervisorTaskStep) -> Dict:
        if step == "configure-supervisor":
            from .commands import write_supervisor_config

            return dict(
                python_callable=lambda: write_supervisor_config(self._supervisor_cfg, _exit=False), do_xcom_push=True
            )
        elif step == "start-supervisor":
            from .commands import start_supervisor

            return dict(
                python_callable=lambda: start_supervisor(self._supervisor_cfg._pydantic_path, _exit=False),
                do_xcom_push=True,
            )
        elif step == "start-programs":
            from .commands import start_programs

            return dict(python_callable=lambda: start_programs(self._supervisor_cfg, _exit=False), do_xcom_push=True)
        elif step == "stop-programs":
            from .commands import stop_programs

            return dict(python_callable=lambda: stop_programs(self._supervisor_cfg, _exit=False), do_xcom_push=True)
        elif step == "check-programs":
            from .commands import check_programs

            def _check_programs(supervisor_cfg=self._supervisor_cfg, **kwargs) -> CheckResult:
                # TODO formalize
                if check_programs(supervisor_cfg, check_done=True, _exit=False):
                    # finish
                    return Result.PASS, Action.STOP
                if check_programs(supervisor_cfg, check_running=True, _exit=False):
                    return Result.PASS, Action.CONTINUE
                if check_programs(supervisor_cfg, _exit=False):
                    return Result.PASS, Action.CONTINUE
                return Result.FAIL, Action.RETRIGGER

            return dict(python_callable=_check_programs, do_xcom_push=True)
        elif step == "restart-programs":
            from .commands import restart_programs

            return dict(python_callable=lambda: restart_programs(self._supervisor_cfg, _exit=False), do_xcom_push=True)
        elif step == "stop-supervisor":
            from .commands import stop_supervisor

            return dict(python_callable=lambda: stop_supervisor(self._supervisor_cfg, _exit=False), do_xcom_push=True)
        elif step == "unconfigure-supervisor":
            from .commands import remove_supervisor_config

            return dict(
                python_callable=lambda: remove_supervisor_config(self._supervisor_cfg, _exit=False), do_xcom_push=True
            )
        elif step == "force-kill":
            from .commands import kill_supervisor

            return dict(python_callable=lambda: kill_supervisor(self._supervisor_cfg, _exit=False), do_xcom_push=True)
        raise NotImplementedError

    def get_step_operator(self, step: SupervisorTaskStep) -> Operator:
        if step == "check-programs":
            return HighAvailabilityOperator(
                **{
                    "task_id": f"{self.dag_id}-{step}",
                    "poke_interval": self._supervisor_cfg.check_interval.total_seconds(),
                    "timeout": self._supervisor_cfg.check_timeout.total_seconds(),
                    "mode": "poke",
                    **self.get_base_operator_kwargs(),
                    **self.get_step_kwargs(step),
                }
            )
        return PythonOperator(
            **{"task_id": f"{self.dag_id}-{step}", **self.get_base_operator_kwargs(), **self.get_step_kwargs(step)}
        )
