from logging import getLogger
from typing import Dict

from airflow.models.dag import DAG
from airflow.models.operator import Operator
from airflow.operators.python import PythonOperator
from airflow_common_operators import fail, skip
from airflow_ha import Action, CheckResult, HighAvailabilityOperator, Result
from supervisor_pydantic.client import SupervisorRemoteXMLRPCClient
from supervisor_pydantic.convenience import (
    SupervisorTaskStep,
    check_programs,
    kill_supervisor,
    remove_supervisor_config,
    restart_programs,
    start_programs,
    start_supervisor,
    stop_programs,
    stop_supervisor,
    write_supervisor_config,
)

from airflow_supervisor.config import SupervisorAirflowConfiguration

__all__ = ("Supervisor",)

_log = getLogger(__name__)


class Supervisor(object):
    _dag: DAG
    _cfg: SupervisorAirflowConfiguration
    _kill_dag: DAG
    _xmlrpc_client: SupervisorRemoteXMLRPCClient

    def __init__(self, dag: DAG, cfg: SupervisorAirflowConfiguration, **kwargs):
        # store config
        self._cfg = cfg

        # store or create client
        self._xmlrpc_client = kwargs.pop("xmlrpc_client", SupervisorRemoteXMLRPCClient(self._cfg))

        # store dag
        self._dag = dag

        self.setup_dag()

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
        (
            PythonOperator(
                task_id=f"{self._dag.dag_id}-force-kill-dag", python_callable=skip, pool=self._cfg.airflow.pool
            )
            >> self._force_kill
        )

        # Deal with any configuration or cleanup problems
        any_config_fail = PythonOperator(
            task_id=f"{self._dag.dag_id}-check-config-failed",
            python_callable=fail,
            trigger_rule="one_failed",
            pool=self._cfg.airflow.pool,
        )
        self.configure_supervisor >> any_config_fail
        self.start_supervisor >> any_config_fail
        self.start_programs >> any_config_fail
        self.stop_programs >> any_config_fail
        self.unconfigure_supervisor >> any_config_fail

    def setup_dag(self):
        # override dag kwargs that dont make sense
        self._dag.catchup = False
        self._dag.concurrency = 1
        self._dag.max_active_tasks = 1
        self._dag.max_active_runs = 1

    def initialize_tasks(self):
        # NOTE: initialize this first as it is relied upon by startup steps
        self._check_programs = self.get_step_operator("check-programs")

        # tasks
        self._configure_supervisor = self.get_step_operator(step="configure-supervisor")
        self._start_supervisor = self.get_step_operator(step="start-supervisor")
        self._start_programs = self.get_step_operator("start-programs")
        if self._cfg.stop_on_exit:
            _log.info("Stopping programs on exit")
            self._stop_programs = self.get_step_operator("stop-programs")
            if self._cfg.cleanup:
                _log.info("Cleaning up supervisor config on exit")
                self._unconfigure_supervisor = self.get_step_operator("unconfigure-supervisor")
            else:
                _log.info("Skipping cleanup of supervisor config on exit")
                self._unconfigure_supervisor = PythonOperator(
                    task_id=f"{self._dag.dag_id}-unconfigure-supervisor", python_callable=skip
                )
        else:
            _log.info("Not stopping programs on exit")
            _log.info("Skipping cleanup of supervisor config on exit")
            self._stop_programs = PythonOperator(task_id=f"{self._dag.dag_id}-stop-programs", python_callable=skip)
            self._unconfigure_supervisor = PythonOperator(
                task_id=f"{self._dag.dag_id}-unconfigure-supervisor", python_callable=skip
            )

        self._restart_programs = self.get_step_operator("restart-programs")
        self._stop_supervisor = self.get_step_operator("stop-supervisor")

    @property
    def configure_supervisor(self) -> "Operator":
        return self._configure_supervisor

    @property
    def start_supervisor(self) -> "Operator":
        return self._start_supervisor

    @property
    def start_programs(self) -> "Operator":
        return self._start_programs

    @property
    def check_programs(self) -> "HighAvailabilityOperator":
        return self._check_programs

    @property
    def stop_programs(self) -> "Operator":
        return self._stop_programs

    @property
    def restart_programs(self) -> "Operator":
        return self._restart_programs

    @property
    def stop_supervisor(self) -> "Operator":
        return self._stop_supervisor

    @property
    def unconfigure_supervisor(self) -> "Operator":
        return self._unconfigure_supervisor

    @property
    def supervisor_client(self) -> SupervisorRemoteXMLRPCClient:
        return SupervisorRemoteXMLRPCClient(self._cfg)

    def get_base_operator_kwargs(self) -> Dict:
        return dict(dag=self._dag, pool=self._cfg.airflow.pool)

    def get_step_kwargs(self, step: SupervisorTaskStep) -> Dict:
        if step == "configure-supervisor":
            return dict(
                python_callable=lambda **kwargs: (
                    self.check_programs.check_end_conditions(**kwargs) is None
                    and write_supervisor_config(self._cfg, _exit=False)
                ),
                do_xcom_push=True,
            )
        elif step == "start-supervisor":
            return dict(
                python_callable=lambda **kwargs: (
                    self.check_programs.check_end_conditions(**kwargs) is None
                    and start_supervisor(self._cfg._pydantic_path, _exit=False)
                ),
                do_xcom_push=True,
            )
        elif step == "start-programs":
            if self._cfg.restart_on_retrigger:
                _log.info("Restarting programs on retrigger")
                return dict(
                    python_callable=lambda **kwargs: (
                        self.check_programs.check_end_conditions(**kwargs) is None
                        and start_programs(
                            self._cfg,
                            # Always restart programs
                            restart=True,
                            _exit=False,
                        )
                    ),
                    do_xcom_push=True,
                )
            if self._cfg.restart_on_initial:
                _log.info("Restarting programs on initial run")
                return dict(
                    python_callable=lambda **kwargs: (
                        self.check_programs.check_end_conditions(**kwargs) is None
                        and start_programs(
                            self._cfg,
                            # Restart programs if initial run
                            restart=self.check_programs.is_initial_run(**kwargs),
                            _exit=False,
                        )
                    ),
                    do_xcom_push=True,
                )
            _log.info("Starting programs as normal on initial run")
            return dict(
                python_callable=lambda **kwargs: (
                    self.check_programs.check_end_conditions(**kwargs) is None
                    # Don't restart programs
                    and start_programs(self._cfg, _exit=False)
                ),
                do_xcom_push=True,
            )
        elif step == "stop-programs":
            return dict(python_callable=lambda: stop_programs(self._cfg, _exit=False), do_xcom_push=True)
        elif step == "check-programs":

            def _check_programs(supervisor_cfg=self._cfg, **kwargs) -> CheckResult:
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
            return dict(python_callable=lambda: restart_programs(self._cfg, _exit=False), do_xcom_push=True)
        elif step == "stop-supervisor":
            return dict(python_callable=lambda: stop_supervisor(self._cfg, _exit=False), do_xcom_push=True)
        elif step == "unconfigure-supervisor":
            return dict(python_callable=lambda: remove_supervisor_config(self._cfg, _exit=False), do_xcom_push=True)
        elif step == "force-kill":
            return dict(python_callable=lambda: kill_supervisor(self._cfg, _exit=False), do_xcom_push=True)
        raise NotImplementedError(f"Unknown step: {step}")

    def get_step_operator(self, step: SupervisorTaskStep) -> "Operator":
        if step == "check-programs":
            ha_operator_args = {
                # Sensor Args
                "task_id": f"{self._dag.dag_id}-{step}",
                "poke_interval": self._cfg.airflow.check_interval.total_seconds(),
                "timeout": self._cfg.airflow.check_timeout.total_seconds(),
                "mode": "poke",
                # HighAvailabilityOperator Args
                "runtime": self._cfg.airflow.runtime,
                "endtime": self._cfg.airflow.endtime,
                "maxretrigger": self._cfg.airflow.maxretrigger,
                "reference_date": self._cfg.airflow.reference_date,
                # Pass through
                **self.get_base_operator_kwargs(),
                **self.get_step_kwargs(step),
            }
            _log.info(f"Creating HighAvailabilityOperator for {step} with args: {ha_operator_args}")
            return HighAvailabilityOperator(**ha_operator_args)
        return PythonOperator(
            **{"task_id": f"{self._dag.dag_id}-{step}", **self.get_base_operator_kwargs(), **self.get_step_kwargs(step)}
        )

    def __lshift__(self, other: "Operator") -> "Operator":
        """e.g. a << Supervisor() << b"""
        self.unconfigure_supervisor >> other
        return self.configure_supervisor

    def __rshift__(self, other: "Operator") -> "Operator":
        """e.g. a >> Supervisor() >> b"""
        other >> self.configure_supervisor
        return self.unconfigure_supervisors

    def set_upstream(self, other: "Operator"):
        self.configure_supervisor.set_upstream(other)

    def set_downstream(self, other: "Operator"):
        self.unconfigure_supervisor.set_downstream(other)
