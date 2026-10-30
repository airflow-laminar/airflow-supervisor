import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("airflow")

from airflow.exceptions import AirflowException
from airflow.models.dag import DAG
from airflow_ha import Action, Result
from supervisor_pydantic import ProcessInfo, ProcessState, SupervisorRemoteXMLRPCClient

from airflow_supervisor import (
    Supervisor,
    SupervisorAirflowConfiguration,
    SupervisorSSH,
    SupervisorSSHAirflowConfiguration,
    create_supervisor_control_dags,
)
from airflow_supervisor.airflow import programs


class TaskInstance:
    def __init__(self, task_id, values, run_id="run", try_number=1):
        self.task_id, self.values, self.run_id, self.try_number = task_id, values, run_id, try_number

    def xcom_push(self, key, value):
        self.values[self.task_id, key] = value

    def xcom_pull(self, task_ids=None, key="return_value", **kwargs):
        if isinstance(task_ids, str):
            return self.values.get((task_ids, key))
        return [self.values.get((task_id, key)) for task_id in task_ids or [self.task_id]]


def process(name, state="RUNNING", group=None, start=None):
    return ProcessInfo(
        name=name,
        group=group or name,
        state=state,
        start=start or datetime.now(UTC) - timedelta(minutes=11),
        stop=datetime.fromtimestamp(0, UTC),
        now=datetime.now(UTC),
        exitstatus=1 if state == "FATAL" else 0,
        description="",
        pid=123,
        logfile="",
        stdout_logfile="",
        stderr_logfile="",
    )


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    controls = {}
    monkeypatch.setattr(programs, "_variable_get", lambda key: controls.get(key, {}))
    monkeypatch.setattr(programs, "_variable_set", lambda key, value: controls.__setitem__(key, value))
    cfg = SupervisorAirflowConfiguration(
        working_dir=tmp_path,
        forward_logs=False,
        program={name: {"command": "sleep 100"} for name in "ABC"},
        program_lifecycle={
            "B": {"start_after": ["A"], "start_delay": 600},
            "C": {"start_after": ["B"], "required": False, "max_consecutive_failures": 3},
        },
    )
    infos = [process(name) for name in "ABC"]
    client = Mock(spec=SupervisorRemoteXMLRPCClient)
    client.getAllProcessInfo.side_effect = lambda: infos

    def start(name):
        for info in infos:
            if f"{info.group}:{info.name}" == name:
                info.state = ProcessState.RUNNING

    def stop(name):
        for info in infos:
            if f"{info.group}:{info.name}" == name:
                info.state = ProcessState.STOPPED

    client.startProcess.side_effect = start
    client.stopProcess.side_effect = stop
    supervisor = Supervisor(DAG(dag_id="programs", schedule=None), cfg, xmlrpc_client=client)
    supervisor.check_programs._check_end_conditions = Mock(return_value=None)
    return supervisor, infos, client, controls


def context(supervisor, task=None, values=None, conf=None, run_id="run", try_number=1):
    task = task or supervisor.check_programs
    ti = TaskInstance(task.task_id, values if values is not None else {}, run_id, try_number)
    return {
        "ti": ti,
        "task_instance": ti,
        "task": task,
        "run_id": run_id,
        "dag_run": SimpleNamespace(conf=conf or {}, start_date=datetime.now(UTC)),
    }


def test_program_task_dependencies_and_shutdown_branch(lifecycle):
    supervisor, _, _, _ = lifecycle
    tasks = supervisor.program_tasks
    assert tasks["A"].start.task_id in tasks["B"].delay.upstream_task_ids
    assert tasks["B"].start.task_id in tasks["C"].delay.upstream_task_ids
    assert tasks["C"].stop.task_id in tasks["B"].stop.upstream_task_ids
    assert tasks["B"].stop.task_id in tasks["A"].stop.upstream_task_ids
    assert tasks["B"].delay.mode == "reschedule"
    assert supervisor.check_programs.trigger_rule == "all_done"
    supervisor._dag.topological_sort()
    controller = supervisor._program_lifecycle
    for branch in (supervisor.check_programs.retrigger_pass, supervisor.check_programs.retrigger_fail):
        values = {(supervisor.check_programs.task_id, "return_value"): (Result.PASS, Action.RETRIGGER)}
        assert controller.shutdown_branch(**context(supervisor, values=values)) == []
    values = {(supervisor.check_programs.task_id, "return_value"): (Result.PASS, Action.STOP)}
    assert set(controller.shutdown_branch(**context(supervisor, values=values))) == {
        task.stop.task_id for task in tasks.values()
    }


def test_optional_failure_budget_survives_retriggers_without_restarting_peers(lifecycle):
    supervisor, infos, client, _ = lifecycle
    controller = supervisor._program_lifecycle
    infos[2].state = ProcessState.FATAL
    client.startProcess.side_effect = None
    conf = {}
    for failure in range(1, 4):
        values = {}
        controller.start("C", **context(supervisor, supervisor.program_tasks["C"].start, values, conf))
        result = controller.monitor(**context(supervisor, values=values, conf=conf))
        state = values[supervisor.check_programs.task_id, "supervisor_program_state"]
        assert state["C"]["failures"] == failure
        assert state["C"]["disabled"] is (failure == 3)
        assert result == (Result.PASS, Action.RETRIGGER if failure < 3 else Action.CONTINUE)
        conf = {"supervisor_program_state": json.dumps(state)}
    client.startProcess.reset_mock()
    controller.start("C", **context(supervisor, supervisor.program_tasks["C"].start, conf=conf))
    client.startProcess.assert_not_called()
    client.stopProcess.assert_not_called()
    assert infos[0].state == infos[1].state == ProcessState.RUNNING
    assert controller.monitor(**context(supervisor)) == (Result.PASS, Action.RETRIGGER)


def test_task_retries_precede_tolerated_start_failure(lifecycle):
    supervisor, infos, client, _ = lifecycle
    infos[2].state = ProcessState.FATAL
    client.startProcess.side_effect = None
    task = supervisor.program_tasks["C"].start
    task.retries = 2
    values = {}
    for attempt in (1, 2):
        with pytest.raises(AirflowException, match="C start failed"):
            supervisor._program_lifecycle.start("C", **context(supervisor, task, values, try_number=attempt))
    assert not any(key == "supervisor_program_state:C" for _, key in values)
    supervisor._program_lifecycle.start("C", **context(supervisor, task, values, try_number=3))
    assert values[task.task_id, "supervisor_program_state:C"]["failures"] == 1


def test_required_failure_preserves_failure_branch(lifecycle):
    supervisor, infos, _, _ = lifecycle
    infos[0].state = ProcessState.FATAL
    assert supervisor._program_lifecycle.monitor(**context(supervisor)) == (Result.FAIL, Action.RETRIGGER)


def test_successful_observation_resets_failure_count(lifecycle):
    supervisor, _, _, _ = lifecycle
    ctx = context(supervisor, conf={"supervisor_program_state": {"C": {"failures": 2}}})
    assert supervisor._program_lifecycle.monitor(**ctx) == (Result.PASS, Action.CONTINUE)
    assert ctx["ti"].values[supervisor.check_programs.task_id, "supervisor_program_state"]["C"]["failures"] == 0


def test_start_delay_uses_predecessor_start_time(lifecycle):
    supervisor, infos, _, _ = lifecycle
    infos[1].state = ProcessState.STOPPED
    controller = supervisor._program_lifecycle
    infos[0].start = datetime.now(UTC) - timedelta(minutes=9)
    assert not controller.delay("B", **context(supervisor))
    infos[0].start -= timedelta(minutes=2)
    assert controller.delay("B", **context(supervisor))
    infos[0].state = ProcessState.FATAL
    with pytest.raises(AirflowException, match="predecessor A failed"):
        controller.delay("B", **context(supervisor))


def test_control_stop_suspends_monitoring_until_explicit_start(lifecycle):
    supervisor, infos, client, controls = lifecycle
    controller = supervisor._program_lifecycle
    controller.control("C", "stop", **context(supervisor, run_id="stop-control"))
    assert controls[controller._control_key("C")]["enabled"] is False
    assert controller.monitor(**context(supervisor)) == (Result.PASS, Action.CONTINUE)
    client.startProcess.assert_not_called()
    controller.control("C", "start", **context(supervisor, run_id="start-control"))
    assert infos[2].state == ProcessState.RUNNING
    assert controls[controller._control_key("C")]["enabled"] is True


def test_controls_are_separate_unscheduled_dags(lifecycle):
    supervisor, _, _, _ = lifecycle
    dags = create_supervisor_control_dags(supervisor)
    assert len(dags) == 13
    assert "programs-restart-C" in dags and "programs-force-kill" in dags
    assert all(type(dag.timetable).__name__ == "NullTimetable" for dag in dags.values())
    assert create_supervisor_control_dags(supervisor._dag).keys() == dags.keys()
    for dag in dags.values():
        dag.topological_sort()
    stop = dags["programs-stop-programs"]
    assert "stop-B" in stop.get_task("stop-A").upstream_task_ids
    restart = dags["programs-restart-programs"]
    assert "stop-B" in restart.get_task("stop-A").upstream_task_ids
    assert "stop-A" in restart.get_task("delay-A").upstream_task_ids
    assert "start-A" in restart.get_task("delay-B").upstream_task_ids


def test_retrigger_conf_renders_program_state_and_log_cursors(lifecycle):
    supervisor, _, _, _ = lifecycle
    values = {
        (supervisor.check_programs.task_id, "supervisor_program_state"): {"C": {"failures": 2}},
        (supervisor.check_programs.task_id, "supervisor_log_offsets"): {"offsets": {"C:C:stdout": 42}},
    }
    ctx = context(supervisor, values=values)
    for trigger in (supervisor.check_programs.retrigger_pass, supervisor.check_programs.retrigger_fail):
        trigger.render_template_fields(ctx)
        assert json.loads(trigger.conf["supervisor_program_state"])["C"]["failures"] == 2
        assert json.loads(trigger.conf["supervisor_log_offsets"])["offsets"]["C:C:stdout"] == 42


def test_monitor_resumes_most_advanced_startup_log_cursors(lifecycle):
    supervisor, infos, client, _ = lifecycle
    supervisor._cfg.forward_logs = True
    values = {}
    for name, offset in (("A", 10), ("B", 20), ("C", 30)):
        values[supervisor.program_tasks[name].start.task_id, "supervisor_log_offsets"] = {
            "run_id": "run",
            "offsets": {"A:A:stdout": offset},
        }
    client.readProcessLogChunk.return_value = SimpleNamespace(text="", offset=30, truncated=False)
    supervisor._log_forwarder.forward(infos, context(supervisor, values=values))
    first = client.readProcessLogChunk.call_args_list[0]
    assert first.args[0:3] == ("A:A", "stdout", 30)


def test_program_operator_can_be_composed_in_another_dag(lifecycle):
    supervisor, _, _, _ = lifecycle
    dag = DAG(dag_id="custom-controls", schedule=None)
    stop = supervisor.program_operator("B", "stop", dag=dag)
    restart = supervisor.program_operator("A", "restart", dag=dag, retries=2)
    stop >> restart
    assert restart.retries == 2
    assert stop.task_id in restart.upstream_task_ids


def test_default_forwarding_with_real_supervisord(tmp_path, open_port, monkeypatch, caplog):
    import logging
    import subprocess
    import sys
    import time
    from shlex import quote

    from supervisor_pydantic.convenience import write_supervisor_config

    monkeypatch.setattr(programs, "_variable_get", lambda key: {})
    emitter = tmp_path / "emit_output.py"
    emitter.write_text(
        "import sys, time\nprint('program stdout', flush=True)\nprint('program stderr', file=sys.stderr, flush=True)\ntime.sleep(60)\n"
    )
    cfg = SupervisorAirflowConfiguration(
        working_dir=tmp_path / "instance",
        port=f"127.0.0.1:{open_port}",
        program={"emitter": {"command": f"{quote(sys.executable)} {quote(str(emitter))}"}},
        program_lifecycle={},
    )
    assert cfg.forward_logs is True
    write_supervisor_config(cfg.model_dump_json(exclude_unset=True), _exit=False)
    client = SupervisorRemoteXMLRPCClient(cfg)
    daemon = subprocess.Popen(
        [str(Path(sys.executable).parent / "supervisord"), "-n", "-c", str(cfg.config_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                client.getState()
                break
            except OSError:
                time.sleep(0.05)
        else:
            pytest.fail("supervisord did not start")
        supervisor = Supervisor(DAG(dag_id="real-output", schedule=None), cfg, xmlrpc_client=client)
        assert supervisor._program_lifecycle is not None
        supervisor.check_programs._check_end_conditions = Mock(return_value=None)
        caplog.set_level(logging.INFO)
        values = {}
        start = supervisor.program_tasks["emitter"].start
        start.python_callable(**context(supervisor, task=start, values=values))
        assert supervisor._program_lifecycle.monitor(**context(supervisor, values=values)) == (
            Result.PASS,
            Action.CONTINUE,
        )
        messages = [record.getMessage() for record in caplog.records]
        assert any("[supervisor emitter:emitter stdout] program stdout" in message for message in messages)
        assert any("[supervisor emitter:emitter stderr] program stderr" in message for message in messages)
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)


@pytest.mark.parametrize(
    "config_type,operator",
    [(SupervisorAirflowConfiguration, Supervisor), (SupervisorSSHAirflowConfiguration, SupervisorSSH)],
)
def test_configuration_round_trip_and_python_rendering(tmp_path, config_type, operator):
    from airflow_config import Configuration

    from airflow_supervisor import SupervisorSSHTask, SupervisorTask

    cfg = config_type(
        working_dir=tmp_path, program={"A": {"command": "sleep 1"}}, program_lifecycle={"A": {"retries": 2}}
    )
    restored = config_type.model_validate_json(cfg.model_dump_json())
    assert restored.program_lifecycle["A"].retries == 2
    task_type = SupervisorSSHTask if operator is SupervisorSSH else SupervisorTask
    model = task_type(task_id="service", cfg=cfg)
    config = Configuration(dags={"program-render": {"dag_id": "program-render", "tasks": {"service": model}}})
    source = config.dags["program-render"].render(airflow_major_version=3)
    assert "program_lifecycle" in source
    dag = config.dags["program-render"].instantiate()
    assert dag.get_task("program-render-start-A").retries == 2


@pytest.mark.parametrize(
    "policy",
    [
        {"X": {}},
        {"A": {"start_after": ["X"]}},
        {"A": {"start_after": ["A"]}},
        {"A": {"start_after": ["B"]}, "B": {"start_after": ["A"]}},
        {"A": {"start_after": ["B"]}, "B": {"stop_before": ["A"]}},
        {"A": {"max_consecutive_failures": 3}},
        {"A": {"start_delay": -1}},
    ],
)
def test_invalid_program_policies_are_rejected(policy):
    with pytest.raises(ValueError):
        SupervisorAirflowConfiguration(program={name: {"command": "true"} for name in "AB"}, program_lifecycle=policy)
