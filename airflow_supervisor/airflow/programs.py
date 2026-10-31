import json
from datetime import UTC, datetime
from functools import partial
from types import SimpleNamespace

from supervisor_pydantic import ProcessState

from airflow_supervisor.config.program import ProgramLifecycleConfiguration

from .observability import _RPC_ERRORS, _failure_details, _log, _publish_status

_STATE = "supervisor_program_state"


def _variable_get(key):
    from airflow_pydantic.migration import _airflow_3

    if _airflow_3():
        from airflow.sdk import Variable

        return Variable.get(key, default={}, deserialize_json=True)
    from airflow.models import Variable

    return Variable.get(key, default_var={}, deserialize_json=True)


def _variable_set(key, value):
    from airflow_pydantic.migration import _airflow_3

    if _airflow_3():
        from airflow.sdk import Variable
    else:
        from airflow.models import Variable
    Variable.set(key, value, serialize_json=True)


class ProgramLifecycle:
    def __init__(self, supervisor):
        self.supervisor = supervisor
        self.cfg = supervisor._cfg
        self.dag = supervisor._dag
        self.client = supervisor.supervisor_client
        self.counts = {
            name: program.numprocs or 1
            for name, program in {**self.cfg.program, **(self.cfg.fcgiprogram or {})}.items()
        }
        for name, group in (self.cfg.group or {}).items():
            self.counts[name] = sum(self.counts.pop(program) for program in group.programs)
        self.policies = {
            name: (self.cfg.program_lifecycle or {}).get(name, ProgramLifecycleConfiguration()) for name in self.counts
        }
        self.tasks = {}

    def _control_key(self, program):
        return f"airflow-supervisor:{self.dag.dag_id}:{program}:control"

    def _inspect(self, context, flush=False):
        infos = [info for info in self.client.getAllProcessInfo() if info.group in self.policies]
        self.supervisor._log_forwarder.forward(infos, context, flush=flush)
        _publish_status(infos, context, self.cfg.exitcodes)
        return infos

    def _load(self, program, context):
        conf = context["dag_run"].conf or {}
        inherited = conf.get(_STATE, {})
        if isinstance(inherited, str):
            inherited = json.loads(inherited)
        state = inherited.get(program, {}).copy()
        ti = context["ti"]
        for value in (
            ti.xcom_pull(
                task_ids=[self.supervisor.check_programs.task_id, self.tasks[program].start.task_id],
                key=f"{_STATE}:{program}",
            )
            or []
        ):
            if isinstance(value, dict):
                state = value.copy()
                break
        control = _variable_get(self._control_key(program))
        if state.get("revision") != control.get("revision"):
            state = {"revision": control.get("revision")}
        state.setdefault("failures", 0)
        state.setdefault("disabled", False)
        state.setdefault("failure_observed", False)
        state["enabled"] = control.get("enabled", True)
        return state

    def _save(self, program, state, context):
        context["ti"].xcom_push(key=f"{_STATE}:{program}", value=state)

    def _failed(self, program, state):
        if not state["failure_observed"]:
            state["failures"] += 1
            state["failure_observed"] = True
        policy = self.policies[program]
        if policy.max_consecutive_failures is not None and state["failures"] >= policy.max_consecutive_failures:
            state["disabled"] = True
            _log.error("Supervisor program %s disabled for this chain after %s failures", program, state["failures"])

    def _command(self, program, action, context):
        from airflow.exceptions import AirflowException

        infos = [info for info in self._inspect(context, flush=True) if info.group == program]
        if len(infos) != self.counts[program]:
            raise AirflowException(f"Supervisor program {program} is missing configured processes")
        if action in ("stop", "restart"):
            for info in infos:
                self.client.stopProcess(f"{info.group}:{info.name}")
        if action in ("start", "restart"):
            for info in infos:
                if action == "restart" or info.state not in (ProcessState.RUNNING, ProcessState.STARTING):
                    self.client.startProcess(f"{info.group}:{info.name}")
        infos = [info for info in self._inspect(context, flush=True) if info.group == program]
        valid = (
            all(info.stopped() for info in infos)
            if action == "stop"
            else all(info.ok(self.cfg.exitcodes) for info in infos)
        )
        if len(infos) != self.counts[program] or not valid:
            raise AirflowException(f"Supervisor program {program} {action} failed: {_failure_details(infos)}")
        return infos

    def start(self, program, **context):
        from airflow.exceptions import AirflowException

        state = self._load(program, context)
        if self.supervisor.check_programs.check_end_conditions(**context) is not None:
            return
        if not state["enabled"] or state["disabled"]:
            self._save(program, state, context)
            return
        action = (
            "restart"
            if self.cfg.restart_on_retrigger
            or (self.cfg.restart_on_initial and self.supervisor.check_programs.is_initial_run(**context))
            else "start"
        )
        if not self.supervisor.check_programs.is_initial_run(**context) and action == "start":
            infos = [info for info in self._inspect(context) if info.group == program]
            if len(infos) == self.counts[program] and all(info.done(self.cfg.exitcodes) for info in infos):
                self._save(program, state, context)
                return
        state["failure_observed"] = False
        try:
            self._command(program, action, context)
        except (*_RPC_ERRORS, AirflowException):
            task = context["task"]
            if self.policies[program].required or context["ti"].try_number <= task.retries:
                raise
            self._failed(program, state)
            _log.exception("Supervisor optional program %s could not start", program)
        else:
            state["failure_observed"] = False
        self._save(program, state, context)

    def delay(self, program, force=False, **context):
        state = self._load(program, context)
        if not force and (not state["enabled"] or state["disabled"]):
            return True
        if self.supervisor.check_programs.check_end_conditions(**context) is not None:
            return True
        infos = self._inspect(context)
        if any(info.group == program and info.running() for info in infos):
            return True
        parents = self.policies[program].start_after
        for parent in parents:
            processes = [info for info in infos if info.group == parent]
            if len(processes) != self.counts[parent] or any(info.bad(self.cfg.exitcodes) for info in processes):
                from airflow.exceptions import AirflowException

                raise AirflowException(f"Supervisor predecessor {parent} failed while waiting to start {program}")
        starts = [info.start for info in infos if info.group in parents]
        if not starts:
            starts = [context["dag_run"].start_date]
        return (datetime.now(UTC) - max(starts)).total_seconds() >= self.policies[program].start_delay.total_seconds()

    def monitor(self, **context):
        from airflow_ha import Action, Result

        infos = self._inspect(context)
        required_failure = False
        recover = False
        complete = True
        states = {}
        for name, policy in self.policies.items():
            state = self._load(name, context)
            processes = [info for info in infos if info.group == name]
            if state["enabled"] and not state["disabled"]:
                healthy = len(processes) == self.counts[name] and all(
                    info.ok(self.cfg.exitcodes) or info.state == ProcessState.STARTING for info in processes
                )
                if healthy:
                    if all(info.state != ProcessState.STARTING for info in processes):
                        state["failures"] = 0
                        state["failure_observed"] = False
                    complete &= all(info.done(self.cfg.exitcodes) for info in processes)
                else:
                    self._failed(name, state)
                    required_failure |= policy.required
                    recover |= not state["disabled"]
                    complete = False
                    _log.error("Supervisor program %s unhealthy: %s", name, _failure_details(processes))
            self._save(name, state, context)
            states[name] = state
        context["ti"].xcom_push(key=_STATE, value=states)
        if required_failure or recover:
            self.supervisor._log_forwarder.forward(infos, context, flush=True)
            return (Result.FAIL if required_failure else Result.PASS), Action.RETRIGGER
        return Result.PASS, Action.STOP if complete else Action.CONTINUE

    def build(self):
        from airflow.providers.standard.operators.empty import EmptyOperator
        from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
        from airflow.providers.standard.sensors.python import PythonSensor

        owner = self.supervisor
        owner._check_programs = owner.get_step_operator("check-programs")
        owner.check_programs.trigger_rule = "all_done"
        for trigger in (owner.check_programs.retrigger_pass, owner.check_programs.retrigger_fail):
            trigger.conf[_STATE] = (
                "{{ (ti.xcom_pull(task_ids='"
                + owner.check_programs.task_id
                + "', key='"
                + _STATE
                + "') or {}) | tojson }}"
            )
        owner._configure_supervisor = owner.get_step_operator("configure-supervisor")
        owner._start_supervisor = owner.get_step_operator("start-supervisor")
        owner._stop_supervisor = (
            owner.get_step_operator("stop-supervisor")
            if self.cfg.stop_on_exit
            else (EmptyOperator(task_id=f"{self.dag.dag_id}-stop-supervisor", **owner.get_base_operator_kwargs()))
        )
        owner._unconfigure_supervisor = (
            owner.get_step_operator("unconfigure-supervisor")
            if self.cfg.cleanup and self.cfg.stop_on_exit
            else (
                EmptyOperator(task_id=f"{self.dag.dag_id}-unconfigure-supervisor", **owner.get_base_operator_kwargs())
            )
        )
        for action in ("start", "stop"):
            setattr(
                owner,
                f"_{action}_programs",
                EmptyOperator(
                    task_id=f"{self.dag.dag_id}-{action}-programs",
                    trigger_rule="all_done" if action == "start" else "none_failed_min_one_success",
                    **owner.get_base_operator_kwargs(),
                ),
            )
        for name, policy in self.policies.items():
            kwargs = {**owner.get_base_operator_kwargs(), "retries": policy.retries, "retry_delay": policy.retry_delay}
            self.tasks[name] = SimpleNamespace(
                start=PythonOperator(
                    task_id=f"{self.dag.dag_id}-start-{name}", python_callable=partial(self.start, name), **kwargs
                ),
                stop=PythonOperator(
                    task_id=f"{self.dag.dag_id}-stop-{name}",
                    python_callable=partial(self._stop, name),
                    trigger_rule="all_done",
                    **kwargs,
                ),
                delay=PythonSensor(
                    task_id=f"{self.dag.dag_id}-delay-{name}",
                    python_callable=partial(self.delay, name),
                    mode="reschedule",
                    poke_interval=30,
                    timeout=self.cfg.check_timeout.total_seconds(),
                    **kwargs,
                ),
            )
        gate = BranchPythonOperator(
            task_id=f"{self.dag.dag_id}-shutdown",
            python_callable=self.shutdown_branch,
            trigger_rule="all_done",
            **owner.get_base_operator_kwargs(),
        )
        owner.check_programs.stop_pass >> gate
        owner.check_programs.stop_fail >> gate
        owner.configure_supervisor >> owner.start_supervisor
        for name, policy in self.policies.items():
            tasks = self.tasks[name]
            owner.start_supervisor >> tasks.delay >> tasks.start >> owner.start_programs
            for parent in policy.start_after:
                self.tasks[parent].start >> tasks.delay
                tasks.stop >> self.tasks[parent].stop
            for after in policy.stop_before:
                tasks.stop >> self.tasks[after].stop
            gate >> tasks.stop >> owner.stop_programs
        owner.start_programs >> owner.check_programs
        owner.stop_programs >> owner.stop_supervisor >> owner.unconfigure_supervisor
        from airflow_pydantic import fail

        terminal_failure = PythonOperator(
            task_id=f"{self.dag.dag_id}-terminal-failure",
            python_callable=fail,
            trigger_rule="all_done",
            **owner.get_base_operator_kwargs(),
        )
        owner.check_programs.stop_fail >> terminal_failure
        gate >> terminal_failure
        owner._program_tasks = self.tasks
        owner._log_forwarder.task_ids = (
            owner.check_programs.task_id,
            *(tasks.start.task_id for tasks in self.tasks.values()),
        )

    def shutdown_branch(self, **context):
        from airflow_ha import Action, Result

        outcome = context["ti"].xcom_pull(task_ids=self.supervisor.check_programs.task_id, key="return_value")
        result, action = (Result(outcome[0]), Action(outcome[1])) if outcome else (Result.FAIL, Action.RETRIGGER)
        end = self.supervisor.check_programs.check_end_conditions(**context)
        if end is not None:
            result, action = end[0] or result, end[1]
        if action != Action.STOP:
            return []
        tasks = [tasks.stop.task_id for tasks in self.tasks.values()]
        if result == Result.FAIL:
            tasks.append(f"{self.dag.dag_id}-terminal-failure")
        return tasks

    def _stop(self, program, **context):
        if self.cfg.stop_on_exit:
            self._command(program, "stop", context)

    def control(self, program, action, **context):
        _variable_set(
            self._control_key(program),
            {
                "enabled": action != "stop",
                "revision": context["run_id"],
            },
        )
        self._command(program, action, context)


def create_supervisor_control_dags(supervisor):
    """Build independently triggerable control Dags for a Supervisor lifecycle."""
    from airflow.providers.standard.operators.python import PythonOperator
    from airflow.providers.standard.sensors.python import PythonSensor
    from airflow_pydantic.airflow import DAG

    if hasattr(supervisor, "_supervisor_lifecycles"):
        return {
            dag_id: dag
            for lifecycle in supervisor._supervisor_lifecycles
            for dag_id, dag in create_supervisor_control_dags(lifecycle).items()
        }
    controller = supervisor._program_lifecycle
    if controller is None:
        raise ValueError("Control Dags require program_lifecycle configuration")
    dags = {}
    for name in controller.policies:
        for action in ("start", "stop", "restart"):
            dag_id = f"{supervisor._dag.dag_id}-{action}-{name}"
            dag = DAG(dag_id=dag_id, schedule=None, catchup=False, max_active_runs=1)
            PythonOperator(
                task_id=action,
                dag=dag,
                pool=supervisor._pool,
                python_callable=partial(controller.control, name, action),
            )
            dags[dag_id] = dag
    for action in ("start", "stop", "restart"):
        dag_id = f"{supervisor._dag.dag_id}-{action}-programs"
        dag = DAG(dag_id=dag_id, schedule=None, catchup=False, max_active_runs=1)
        stages = {}
        for stage in ("stop", "start") if action == "restart" else (action,):
            tasks = {}
            delays = {}
            for name, policy in controller.policies.items():
                tasks[name] = supervisor.program_operator(
                    name,
                    stage,
                    task_id=f"{stage}-{name}",
                    dag=dag,
                    retries=policy.retries,
                    retry_delay=policy.retry_delay,
                )
                if stage == "start":
                    delays[name] = PythonSensor(
                        task_id=f"delay-{name}",
                        dag=dag,
                        pool=supervisor._pool,
                        mode="reschedule",
                        poke_interval=30,
                        timeout=controller.cfg.check_timeout.total_seconds(),
                        python_callable=partial(controller.delay, name, force=True),
                    )
                    delays[name] >> tasks[name]
            for name, policy in controller.policies.items():
                for parent in policy.start_after:
                    if stage == "stop":
                        tasks[name] >> tasks[parent]
                    else:
                        tasks[parent] >> delays[name]
                if stage == "stop":
                    for after in policy.stop_before:
                        tasks[name] >> tasks[after]
            stages[stage] = tasks
            if stage == "start" and "stop" in stages:
                for stopped in stages["stop"].values():
                    for delay in delays.values():
                        stopped >> delay
        dags[dag_id] = dag
    dag_id = f"{supervisor._dag.dag_id}-force-kill"
    dag = DAG(dag_id=dag_id, schedule=None, catchup=False, max_active_runs=1)
    type(supervisor._start_supervisor)(
        task_id="force-kill", dag=dag, pool=supervisor._pool, **supervisor.get_step_kwargs("force-kill")
    )
    dags[dag_id] = dag
    return dags
