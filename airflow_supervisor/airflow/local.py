from logging import getLogger
from typing import TYPE_CHECKING

from airflow_pydantic import Pool, fail, skip
from supervisor_pydantic.client import SupervisorRemoteXMLRPCClient
from supervisor_pydantic.convenience import (
    SupervisorTaskStep,
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

from .observability import _RPC_ERRORS, _failure_details, _LogForwarder, _publish_status

if TYPE_CHECKING:
    from airflow.models.dag import DAG
    from airflow.models.operator import Operator
    from airflow_ha import HighAvailabilityOperator

__all__ = ("Supervisor",)

_log = getLogger(__name__)


class Supervisor:
    _cfg: SupervisorAirflowConfiguration
    _dag: "DAG"
    _kill_dag: "DAG"
    _pool: "Pool"
    _xmlrpc_client: SupervisorRemoteXMLRPCClient

    def __init__(self, dag: "DAG", cfg: SupervisorAirflowConfiguration, **kwargs):
        if isinstance(cfg, dict):
            # NOTE: used in airflow-pydantic rendering
            cfg = SupervisorAirflowConfiguration.model_validate(cfg)

        # store config
        self._cfg = cfg

        # process pool
        self._pool = cfg.pool.pool if isinstance(cfg.pool, Pool) else cfg.pool

        # store or create client
        self._xmlrpc_client = kwargs.pop("xmlrpc_client", SupervisorRemoteXMLRPCClient(self._cfg))

        self._callbacks = {
            name: kwargs.pop(name)
            for name in (
                "on_failure_callback",
                "on_retry_callback",
                "on_success_callback",
                "on_execute_callback",
                "on_skipped_callback",
            )
            if name in kwargs
        }
        self._log_forwarder = _LogForwarder(
            cfg,
            self._xmlrpc_client,
            (
                f"{dag.dag_id}-check-programs",
                f"{dag.dag_id}-start-programs",
                f"{dag.dag_id}-restart-programs",
            ),
        )

        # store dag
        self._dag = dag
        existing_tasks = set(dag.task_ids)

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
        from airflow.operators.python import PythonOperator

        (
            PythonOperator(
                task_id=f"{self._dag.dag_id}-force-kill-dag", python_callable=skip, **self.get_base_operator_kwargs()
            )
            >> self._force_kill
        )

        # Deal with any configuration or cleanup problems
        any_config_fail = PythonOperator(
            task_id=f"{self._dag.dag_id}-check-config-failed",
            python_callable=fail,
            trigger_rule="one_failed",
            **self.get_base_operator_kwargs(),
        )
        self.configure_supervisor >> any_config_fail
        self.start_supervisor >> any_config_fail
        self.start_programs >> any_config_fail
        self.stop_programs >> any_config_fail
        self.unconfigure_supervisor >> any_config_fail

        for task in self._dag.tasks:
            if task.task_id not in existing_tasks:
                for name, callback in self._callbacks.items():
                    setattr(task, name, callback)

    def setup_dag(self):
        # override dag kwargs that dont make sense
        self._dag.catchup = False
        self._dag.concurrency = 1
        self._dag.max_active_tasks = 1
        self._dag.max_active_runs = 1

    def initialize_tasks(self):
        from airflow.operators.python import PythonOperator

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
                    task_id=f"{self._dag.dag_id}-unconfigure-supervisor",
                    python_callable=skip,
                    **self.get_base_operator_kwargs(),
                )
        else:
            _log.info("Not stopping programs on exit")
            _log.info("Skipping cleanup of supervisor config on exit")
            self._stop_programs = PythonOperator(
                task_id=f"{self._dag.dag_id}-stop-programs", python_callable=skip, **self.get_base_operator_kwargs()
            )
            self._unconfigure_supervisor = PythonOperator(
                task_id=f"{self._dag.dag_id}-unconfigure-supervisor",
                python_callable=skip,
                **self.get_base_operator_kwargs(),
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
        return self._xmlrpc_client

    def get_base_operator_kwargs(self) -> dict:
        return {"dag": self._dag, "pool": self._pool, **self._callbacks}

    def _inspect_programs(self, context, flush=False):
        infos = self._xmlrpc_client.getProgramProcessInfo()
        self._log_forwarder.forward(infos, context, flush=flush)
        _publish_status(infos, context, self._cfg.exitcodes)
        return infos

    def _diagnose(self, context):
        try:
            infos = self._inspect_programs(context, flush=True)
            _publish_status(infos, context, self._cfg.exitcodes, failed=True)
            details = _failure_details(infos)
            _log.error("Supervisor diagnostics: %s", details)
            return details
        except _RPC_ERRORS as error:
            _log.warning("Cannot collect supervisor diagnostics: %s", error)
            return str(error)

    def _run_step(self, step, context):
        from airflow.exceptions import AirflowException

        if (
            step in ("configure-supervisor", "start-supervisor", "start-programs")
            and self.check_programs.check_end_conditions(**context) is not None
        ):
            return False
        if step == "start-programs" and self._cfg.forward_logs:
            try:
                self._log_forwarder.baseline(self._xmlrpc_client.getProgramProcessInfo(), context)
            except _RPC_ERRORS as error:
                _log.warning("Cannot establish supervisor log cursors: %s", error)
        if (
            step in ("restart-programs", "stop-programs", "stop-supervisor", "unconfigure-supervisor", "force-kill")
            and self._cfg.forward_logs
        ):
            try:
                self._inspect_programs(context, flush=True)
            except _RPC_ERRORS as error:
                _log.warning("Cannot collect final supervisor logs: %s", error)
        cfg = self._cfg
        commands = {
            "configure-supervisor": lambda: write_supervisor_config(cfg, _exit=False),
            "start-supervisor": lambda: start_supervisor(cfg._pydantic_path, _exit=False),
            "start-programs": lambda: start_programs(
                cfg,
                restart=bool(
                    cfg.restart_on_retrigger
                    or (cfg.restart_on_initial and self.check_programs.is_initial_run(**context))
                ),
                _exit=False,
            ),
            "restart-programs": lambda: restart_programs(cfg, _exit=False),
            "stop-programs": lambda: stop_programs(cfg, _exit=False),
            "stop-supervisor": lambda: stop_supervisor(cfg, _exit=False),
            "unconfigure-supervisor": lambda: remove_supervisor_config(cfg, _exit=False),
            "force-kill": lambda: kill_supervisor(cfg, _exit=False),
        }
        if step not in commands:
            raise NotImplementedError(f"Unknown step: {step}")
        try:
            result = commands[step]()
        except Exception:
            self._diagnose(context)
            raise
        if result is False:
            details = self._diagnose(context)
            raise AirflowException(f"Supervisor {step} failed: {details}")
        if step in ("restart-programs", "stop-programs") and self._cfg.forward_logs:
            try:
                self._inspect_programs(context, flush=True)
            except _RPC_ERRORS as error:
                _log.warning("Cannot collect supervisor command output: %s", error)
        return result

    def get_step_kwargs(self, step: SupervisorTaskStep) -> dict:
        if step == "check-programs":

            def _check_programs(**context):
                from airflow_ha import Action, Result

                infos = self._inspect_programs(context)
                if infos and all(info.done(self._cfg.exitcodes) for info in infos):
                    self._log_forwarder.forward(infos, context, flush=True)
                    return Result.PASS, Action.STOP
                if infos and all(info.ok(self._cfg.exitcodes) for info in infos):
                    return Result.PASS, Action.CONTINUE
                self._log_forwarder.forward(infos, context, flush=True)
                _publish_status(infos, context, self._cfg.exitcodes, failed=True)
                _log.error("Supervisor workload failed: %s", _failure_details(infos))
                return Result.FAIL, Action.RETRIGGER

            return {"python_callable": _check_programs, "do_xcom_push": True}
        return {"python_callable": lambda **context: self._run_step(step, context), "do_xcom_push": True}

    def get_step_operator(self, step: SupervisorTaskStep) -> "Operator":
        from airflow.operators.python import PythonOperator
        from airflow_ha import HighAvailabilityOperator

        if step == "check-programs":
            ha_operator_args = {
                # Sensor Args
                "task_id": f"{self._dag.dag_id}-{step}",
                "poke_interval": self._cfg.check_interval.total_seconds(),
                "timeout": self._cfg.check_timeout.total_seconds(),
                "mode": "poke",
                # HighAvailabilityOperator Args
                "runtime": self._cfg.runtime,
                "endtime": self._cfg.endtime,
                "maxretrigger": self._cfg.maxretrigger,
                "reference_date": self._cfg.reference_date,
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
        """e.g. Supervisor() << b"""
        self.configure_supervisor << other
        return self.unconfigure_supervisor

    def __rshift__(self, other: "Operator") -> "Operator":
        """e.g. Supervisor() >> b"""
        self.unconfigure_supervisor >> other
        return other

    def set_upstream(self, other: "Operator"):
        self.configure_supervisor.set_upstream(other)

    def set_downstream(self, other: "Operator"):
        self.unconfigure_supervisor.set_downstream(other)

    def update_relative(self, other, upstream: bool = True, edge_modifier=None):
        if upstream:
            self.configure_supervisor.update_relative(other, upstream=True, edge_modifier=edge_modifier)
        else:
            self.unconfigure_supervisor.update_relative(other, upstream=False, edge_modifier=edge_modifier)
        return self

    @property
    def leaves(self):
        """Return the leaves of the DAG."""
        return self.unconfigure_supervisor.leaves

    @property
    def roots(self):
        """Return the roots of the DAG."""
        return self.configure_supervisor.roots
