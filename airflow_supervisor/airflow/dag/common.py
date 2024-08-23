from airflow.exceptions import AirflowSkipException
from airflow.models.dag import DAG
from airflow.models.operator import Operator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from inspect import currentframe
from pathlib import Path
from typing import Dict, Literal

from airflow_supervisor.client import SupervisorRemoteXMLRPCClient
from airflow_supervisor.config import SupervisorAirflowConfiguration


def _skip_by_default():
    raise AirflowSkipException


_DagRole = Literal[
    "setup",
    "monitor",
    "teardown",
    "restart",
    "kill",
]

_SupervisorTaskStep = Literal[
    "configure-supervisor",
    "start-supervisor",
    "start-programs",
    "check-programs",
    "restart-programs",
    "stop-supervisor",
    "unconfigure-supervisor",
    "force-kill",
]


class SupervisorCommon(DAG):
    _base_prefix = "supervisor-local"
    _base_dag_id: str

    _supervisor_dag_role: _DagRole

    _supervisor_setup: DAG
    _supervisor_monitor: DAG
    _supervisor_teardown: DAG
    _supervisor_restart: DAG
    _supervisor_kill: DAG

    _supervisor_xmlrpc_client: SupervisorRemoteXMLRPCClient

    def __init__(self, supervisor_cfg: SupervisorAirflowConfiguration, **kwargs):
        # store config
        self._supervisor_cfg = supervisor_cfg
        self._supervisor_xmlrpc_client = kwargs.pop("supervisor_xmlrpc_client", SupervisorRemoteXMLRPCClient(self._supervisor_cfg))

        _offset = kwargs.pop("_airflow_supervisor_offset", 1)

        # setup role and tweak dag id
        if "airflow_supervisor_dag_role" not in kwargs:
            self._supervisor_dag_role = "setup"
            if "dag_id" not in kwargs:
                kwargs["dag_id"] = list(self._supervisor_cfg.program.keys())[0]
        else:
            self._supervisor_dag_role = kwargs.pop("airflow_supervisor_dag_role")
            self._supervisor_setup = kwargs.pop("supervisor_setup_dag")

        # set dag role for downstream switches
        setattr(self, f"_supervisor_{self._supervisor_dag_role}", self)

        # store base dag id for setting up downstream dags
        if not kwargs["dag_id"].endswith(f"-{self._base_prefix}-{self._supervisor_dag_role}"):
            self._base_dag_id = kwargs["dag_id"]
            kwargs["dag_id"] = f"{kwargs['dag_id']}-{self._base_prefix}-{self._supervisor_dag_role}"

        # set downstream dags to be on-demand
        if self._supervisor_dag_role != "setup":
            kwargs["schedule_interval"] = None

        # override dag kwargs that dont make sense
        kwargs["catchup"] = False
        kwargs["concurrency"] = 1
        kwargs["max_active_tasks"] = 1
        kwargs["max_active_runs"] = 1

        # init with base DAG
        super().__init__(**kwargs)

        # setup sub dags
        if self._supervisor_dag_role == "setup":
            self._supervisor_kill = self.__class__(
                **{
                    **kwargs,
                    "supervisor_cfg": supervisor_cfg,
                    "supervisor_xmlrpc_client": self._supervisor_xmlrpc_client,
                    "dag_id": f"{self._base_dag_id}-{self._base_prefix}-kill",
                    "airflow_supervisor_dag_role": "kill",
                    "supervisor_setup_dag": self,
                }
            )

            self._supervisor_teardown = self.__class__(
                **{
                    **kwargs,
                    "supervisor_cfg": supervisor_cfg,
                    "supervisor_xmlrpc_client": self._supervisor_xmlrpc_client,
                    "dag_id": f"{self._base_dag_id}-{self._base_prefix}-teardown",
                    "airflow_supervisor_dag_role": "teardown",
                    "supervisor_setup_dag": self,
                }
            )

            self._supervisor_restart = self.__class__(
                **{
                    **kwargs,
                    "supervisor_cfg": supervisor_cfg,
                    "supervisor_xmlrpc_client": self._supervisor_xmlrpc_client,
                    "dag_id": f"{self._base_dag_id}-{self._base_prefix}-restart",
                    "airflow_supervisor_dag_role": "restart",
                    "supervisor_setup_dag": self,
                }
            )

            self._supervisor_monitor = self.__class__(
                **{
                    **kwargs,
                    "supervisor_cfg": supervisor_cfg,
                    "supervisor_xmlrpc_client": self._supervisor_xmlrpc_client,
                    "dag_id": f"{self._base_dag_id}-{self._base_prefix}-monitor",
                    "airflow_supervisor_dag_role": "monitor",
                    "supervisor_setup_dag": self,
                }
            )

            for role in _DagRole.__args__:
                if role == "setup":
                    continue
                cur_frame = currentframe()
                for _ in range(_offset):
                    cur_frame = cur_frame.f_back
                cur_frame.f_globals[f"{self._base_dag_id}-{self._base_prefix}-{role}"] = getattr(self, f"_supervisor_{role}")

        # tasks
        if self._supervisor_dag_role == "setup":
            self._configure_supervisor = self.get_step_operator(step="configure-supervisor")
            self._start_supervisor = self.get_step_operator(step="start-supervisor")
            trigger_next = TriggerDagRunOperator(
                task_id=f"{self.dag_id}-trigger-monitor",
                trigger_dag_id=self.monitor_dag.dag_id,
            )

            self._configure_supervisor >> self._start_supervisor >> trigger_next

        if self._supervisor_dag_role == "monitor":
            self._start_programs = self.get_step_operator("start-programs")
            self._check_programs = self.get_step_operator("check-programs")

            trigger_self_task_id = f"{self.dag_id}-trigger-self"
            trigger_restart_task_id = f"{self.dag_id}-trigger-restart"

            def _choose_branch(**kwargs):
                task_instance = kwargs["task_instance"]
                check_program_result = task_instance.xcom_pull(task_ids=[f"{self.dag_id}-check-programs"])
                if check_program_result:
                    # TODO
                    ...

            check_programs_decide = BranchPythonOperator(
                task_id=f"{self.dag_id}-program-status-action",
                python_callable=_choose_branch,
                provide_context=True,
            )
            trigger_self = TriggerDagRunOperator(
                task_id=trigger_self_task_id,
                trigger_dag_id=self.dag_id,
            )
            trigger_restart = TriggerDagRunOperator(
                task_id=trigger_restart_task_id,
                trigger_dag_id=self.restart_dag.dag_id,
            )
            self._stop_programs = self.get_step_operator("stop-programs")
            trigger_next = TriggerDagRunOperator(
                task_id=f"{self.dag_id}-trigger-teardown",
                trigger_dag_id=self.teardown_dag.dag_id,
            )

            self._start_programs >> self._check_programs >> check_programs_decide
            check_programs_decide >> self._stop_programs >> trigger_next
            check_programs_decide >> trigger_self
            check_programs_decide >> trigger_restart

        if self._supervisor_dag_role == "restart":
            self._restart_programs = self.get_step_operator("restart-programs")

        if self._supervisor_dag_role == "teardown":
            self._stop_supervisor = self.get_step_operator("stop-supervisor")
            self._unconfigure_supervisor = self.get_step_operator("unconfigure-supervisor")
            self._stop_supervisor >> self._unconfigure_supervisor

        if self._supervisor_dag_role == "kill":
            self._force_kill = self.get_step_operator("force-kill")
            # Default non running
            # PythonOperator(task_id=f"{self.dag_id}-skip-force-kill", python_callable=_skip_by_default) >> self._force_kill

    @property
    def configure_supervisor(self) -> Operator:
        return self.setup_dag._configure_supervisor

    @property
    def start_supervisor(self) -> Operator:
        return self.setup_dag._start_supervisor

    @property
    def start_programs(self) -> Operator:
        return self.monitor_dag._start_programs

    @property
    def check_programs(self) -> Operator:
        return self.monitor_dag._check_programs

    @property
    def stop_programs(self) -> Operator:
        return self.monitor_dag._stop_programs

    @property
    def restart_programs(self) -> Operator:
        return self.restart_dag._restart_programs

    @property
    def stop_supervisor(self) -> Operator:
        return self.teardown_dag._stop_supervisor

    @property
    def unconfigure_supervisor(self) -> Operator:
        return self.teardown_dag._unconfigure_supervisor

    @property
    def supervisor_client(self) -> SupervisorRemoteXMLRPCClient:
        return SupervisorRemoteXMLRPCClient(self._supervisor_cfg)

    @property
    def setup_dag(self) -> DAG:
        return self._supervisor_setup

    @property
    def monitor_dag(self) -> DAG:
        return self._supervisor_setup._supervisor_monitor

    @property
    def teardown_dag(self) -> DAG:
        return self._supervisor_setup._supervisor_teardown

    @property
    def restart_dag(self) -> DAG:
        return self._supervisor_setup._supervisor_restart

    @property
    def kill_dag(self) -> DAG:
        return self._supervisor_setup._supervisor_kill

    def get_base_operator_kwargs(self) -> Dict:
        return dict(dag=self)

    def get_step_kwargs(self, step: _SupervisorTaskStep) -> Dict:
        # return_kwargs = {}
        if step == "configure-supervisor":

            def _configure_supervisor(supervisor_cfg=self._supervisor_cfg, *args, **kwargs):
                # write supervisor config to filesystem
                self._clent
                Path(supervisor_cfg.path).write_text(supervisor_cfg.to_cfg())
        elif step == "start-supervisor":

            def _start_supervisor(*args, **kwargs):
                # start supervisor daemon
                pass
        elif step == "start-programs":

            def _start_programs(*args, **kwargs):
                # start supervised programs
                pass
        elif step == "check-programs":
            ...
        elif step == "restart-programs":
            ...
        elif step == "stop-supervisor":
            ...
        elif step == "unconfigure-supervisor":

            def _unconfigure_supervisor(supervisor_cfg=self._supervisor_cfg, *args, **kwargs):
                # remove supervisor config to filesystem
                Path(supervisor_cfg.path).unlink(missing_ok=True)
        elif step == "force-kill":
            ...
        return dict(python_callable=lambda *args, **kwargs: True)

    def get_step_operator(self, step: _SupervisorTaskStep) -> Operator:
        return PythonOperator(**{"task_id": f"{self.dag_id}-{step}", **self.get_base_operator_kwargs(), **self.get_step_kwargs(step)})
