from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.models.dag import DAG
from airflow.models.operator import Operator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from typing import Dict, Literal

from airflow_supervisor.client import SupervisorRemoteXMLRPCClient
from airflow_supervisor.config import SupervisorAirflowConfiguration


def _skip():
    raise AirflowSkipException


def _fail():
    raise AirflowFailException


def _pass():
    pass


SupervisorTaskStep = Literal[
    "configure-supervisor",
    "start-supervisor",
    "start-programs",
    "stop-programs",
    "check-programs",
    "restart-programs",
    "stop-supervisor",
    "unconfigure-supervisor",
    "force-kill",
]

__all__ = (
    "Supervisor",
    "SupervisorTaskStep",
)


class Supervisor(DAG):
    _cfg: SupervisorAirflowConfiguration
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

        trigger_self_good = TriggerDagRunOperator(
            task_id=f"{self.dag_id}-trigger-loop",
            trigger_dag_id=self.dag_id,
        )
        trigger_self_bad = TriggerDagRunOperator(
            task_id=f"{self.dag_id}-trigger-redo",
            trigger_dag_id=self.dag_id,
        )
        fail_ = PythonOperator(task_id=f"{self.dag_id}-fail", python_callable=_fail)
        skip_ = PythonOperator(task_id=f"{self.dag_id}-skip", python_callable=_skip)
        pass_ = PythonOperator(task_id=f"{self.dag_id}-pass", python_callable=_pass)

        def _choose_branch(**kwargs):
            task_instance = kwargs["task_instance"]
            check_program_result = task_instance.xcom_pull(task_ids=[f"{self.dag_id}-check-programs"])
            if check_program_result:
                # TODO
                ...

        check_programs_decide = BranchPythonOperator(
            task_id=f"{self.dag_id}-check-programs-decide",
            python_callable=_choose_branch,
            provide_context=True,
        )

        self.configure_supervisor >> self.start_supervisor >> self.start_programs >> self.check_programs
        self.check_programs >> check_programs_decide

        # fail, restart
        check_programs_decide >> self.restart_programs >> trigger_self_bad >> fail_
        # pass, finish
        check_programs_decide >> self.stop_programs >> self.stop_supervisor >> self.unconfigure_supervisor >> pass_
        # loop
        check_programs_decide >> trigger_self_good >> pass_

        # TODO make helper dag
        self._force_kill = self.get_step_operator("force-kill")
        # Default non running
        skip_ >> self._force_kill

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
    def check_programs(self) -> Operator:
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
        # return_kwargs = {}
        if step == "configure-supervisor":
            from .commands import write_supervisor_config

            return dict(python_callable=lambda: write_supervisor_config(self._cfg))
        elif step == "start-supervisor":
            from .commands import start_supervisor

            return dict(python_callable=lambda: start_supervisor(self._cfg._pydantic_path))
        elif step == "start-programs":
            from .commands import start_programs

            return dict(python_callable=lambda: start_programs(self._cfg))
        elif step == "stop-programs":
            from .commands import stop_programs

            return dict(python_callable=lambda: stop_programs(self._cfg))
        elif step == "check-programs":
            from .commands import check_programs

            return dict(python_callable=lambda: check_programs(self._cfg))
        elif step == "restart-programs":
            from .commands import restart_programs

            return dict(python_callable=lambda: restart_programs(self._cfg))
        elif step == "stop-supervisor":
            from .commands import stop_supervisor

            return dict(python_callable=lambda: stop_supervisor(self._cfg))
        elif step == "unconfigure-supervisor":
            from .commands import remove_supervisor_config

            return dict(python_callable=lambda: remove_supervisor_config(self._cfg))
        elif step == "force-kill":
            from .commands import kill_supervisor

            return dict(python_callable=lambda: kill_supervisor(self._cfg))
        return dict(python_callable=lambda *args, **kwargs: True)

    def get_step_operator(self, step: SupervisorTaskStep) -> Operator:
        return PythonOperator(
            **{"task_id": f"{self.dag_id}-{step}", **self.get_base_operator_kwargs(), **self.get_step_kwargs(step)}
        )
