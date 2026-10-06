import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch
from xmlrpc.client import Fault

import pytest

pytest.importorskip("airflow")

from airflow.exceptions import AirflowException
from airflow_pydantic.airflow import DAG
from supervisor_pydantic import ProcessInfo, SupervisorRemoteXMLRPCClient

from airflow_supervisor import (
    Supervisor,
    SupervisorAirflowConfiguration,
    SupervisorSSH,
    SupervisorSSHAirflowConfiguration,
    check_supervisor_health,
)
from airflow_supervisor.airflow.observability import _LogForwarder


def info(state="RUNNING", exitstatus=0):
    return ProcessInfo(
        name="demo",
        group="demo",
        state=state,
        exitstatus=exitstatus,
        spawnerr="spawn failed" if state == "FATAL" else "",
        start=datetime.now(UTC),
        stop=datetime.fromtimestamp(0, UTC),
        now=datetime.now(UTC),
        description="",
        logfile="",
        stdout_logfile="",
        stderr_logfile="",
        pid=123,
    )


class Logs:
    def __init__(self):
        self.stdout = b""
        self.stderr = b""

    def tailProcessStdoutLog(self, name, offset, length):
        return ["", len(self.stdout), False]

    def tailProcessStderrLog(self, name, offset, length):
        return ["", len(self.stderr), False]

    def _read(self, stream, offset, length):
        try:
            return stream[offset : offset + length].decode("utf-8")
        except UnicodeDecodeError as error:
            raise Fault(1, f"UnicodeDecodeError: {error}") from error

    def readProcessStdoutLog(self, name, offset, length):
        return self._read(self.stdout, offset, length)

    def readProcessStderrLog(self, name, offset, length):
        return self._read(self.stderr, offset, length)


class TI:
    task_id = "health"
    run_id = "run"

    def __init__(self):
        self.values = {}

    def xcom_pull(self, **kwargs):
        return [self.values.get(kwargs["key"])]

    def xcom_push(self, key, value):
        self.values[key] = value


def client(cfg, process=None):
    value = SupervisorRemoteXMLRPCClient.__new__(SupervisorRemoteXMLRPCClient)
    value._cfg = cfg
    value._client = SimpleNamespace(supervisor=Logs())
    value.getAllProcessInfo = Mock(return_value=[process or info()])
    return value


def setup(tmp_path, forward_logs=True, **kwargs):
    cfg = SupervisorAirflowConfiguration(
        working_dir=tmp_path,
        program={"demo": {"command": "/bin/sleep 1"}},
        forward_logs=forward_logs,
        **kwargs,
    )
    return cfg, client(cfg)


def test_chunked_output_and_partial_lines_are_not_duplicated(tmp_path, caplog):
    cfg, value = setup(tmp_path, log_chunk_size=5)
    stream = value._client.supervisor
    stream.stdout = "café\npartial".encode()
    stream.stderr = b"error\n"
    forwarder = _LogForwarder(cfg, value)
    caplog.set_level(logging.INFO)
    forwarder.forward([info()], {})
    forwarder.forward([info()], {})
    stream.stdout += b" line\n"
    forwarder.forward([info()], {}, flush=True)
    forwarder.forward([info()], {}, flush=True)
    messages = [record.getMessage() for record in caplog.records]
    assert sum("café" in message for message in messages) == 1
    assert sum(" error" in message for message in messages) == 1
    assert any("[supervisor demo:demo stdout]" in message for message in messages)
    assert any("[supervisor demo:demo stderr]" in message for message in messages)


def test_truncation_does_not_combine_previous_partial_line(tmp_path, caplog):
    cfg, value = setup(tmp_path)
    forwarder = _LogForwarder(cfg, value)
    value._client.supervisor.stdout = b"old partial"
    caplog.set_level(logging.INFO)
    forwarder.forward([info()], {})
    value._client.supervisor.stdout = b"new\n"
    forwarder.forward([info()], {}, flush=True)
    assert "was truncated or rotated" in caplog.text
    assert " stdout] new" in caplog.text
    assert "old partialnew" not in caplog.text


def test_retry_or_next_health_run_resumes_from_last_complete_line(tmp_path, caplog):
    cfg, value = setup(tmp_path)
    ti = TI()
    caplog.set_level(logging.INFO)
    value._client.supervisor.stdout = b"first\npartial"
    _LogForwarder(cfg, value).forward([info()], {"ti": ti})
    assert ti.values["supervisor_log_offsets"]["offsets"]["demo:demo:stdout"] == 6
    assert "pending" not in str(ti.values)
    value._client.supervisor.stdout += b" line\n"
    _LogForwarder(cfg, value).forward([info()], {"ti": ti}, flush=True)
    assert sum(" stdout] first" in record.getMessage() for record in caplog.records) == 1
    assert " stdout] partial line" in caplog.text


def test_default_does_not_read_logs(tmp_path):
    cfg, value = setup(tmp_path, forward_logs=False)
    value.readProcessLogChunk = Mock(side_effect=AssertionError("unexpected log read"))
    result = check_supervisor_health(cfg, supervisor_client=value)
    assert result["healthy"]
    value.readProcessLogChunk.assert_not_called()


def test_unavailable_logs_warn_without_failing_healthy_workload(tmp_path, caplog):
    cfg, value = setup(tmp_path)
    value.readProcessLogChunk = Mock(side_effect=Fault(70, "NO_FILE"))
    result = check_supervisor_health(cfg, supervisor_client=value)
    assert result["healthy"]
    assert "Cannot forward supervisor log" in caplog.text


@pytest.mark.parametrize("state,exitstatus", [("FATAL", 0), ("EXITED", 7), ("EXITED", 0), ("STOPPED", 0)])
def test_watchdog_detects_stopped_or_failed_persistent_service(tmp_path, state, exitstatus):
    cfg, value = setup(tmp_path)
    value.getAllProcessInfo.return_value = [info(state, exitstatus)]
    ti = TI()
    with pytest.raises(AirflowException, match=f"state={state} exitstatus={exitstatus}"):
        check_supervisor_health(cfg.model_dump(), supervisor_client=value, ti=ti)
    assert ti.values["supervisor_process_status"][0]["state"] == state
    if state == "FATAL" or exitstatus == 7:
        assert ti.values["supervisor_failure"][0]["state"] == state


def test_finite_health_check_accepts_successful_completion(tmp_path):
    cfg, value = setup(tmp_path)
    value.getAllProcessInfo.return_value = [info("EXITED")]
    assert check_supervisor_health(cfg, require_running=False, supervisor_client=value)["healthy"]


def test_watchdog_connection_error_is_airflow_failure(tmp_path):
    cfg, value = setup(tmp_path)
    value.getAllProcessInfo.side_effect = ConnectionRefusedError("offline")
    with pytest.raises(AirflowException, match="offline"):
        check_supervisor_health(cfg, supervisor_client=value)


@pytest.mark.parametrize(
    "step,command",
    [
        ("configure-supervisor", "write_supervisor_config"),
        ("start-supervisor", "start_supervisor"),
        ("start-programs", "start_programs"),
        ("stop-programs", "stop_programs"),
        ("restart-programs", "restart_programs"),
        ("stop-supervisor", "stop_supervisor"),
        ("unconfigure-supervisor", "remove_supervisor_config"),
        ("force-kill", "kill_supervisor"),
    ],
)
def test_false_lifecycle_command_raises_with_program_diagnostics(tmp_path, step, command):
    cfg, value = setup(tmp_path, forward_logs=False)
    value.getAllProcessInfo.return_value = [info("FATAL")]
    with DAG(dag_id=f"failed-{step}", schedule=None) as dag:
        supervisor = Supervisor(dag=dag, cfg=cfg, xmlrpc_client=value)
    supervisor.check_programs._check_end_conditions = Mock(return_value=None)
    with (
        patch(f"airflow_supervisor.airflow.local.{command}", return_value=False),
        pytest.raises(AirflowException, match=f"{step} failed: demo:demo state=FATAL"),
    ):
        supervisor.get_step_kwargs(step)["python_callable"]()


def test_end_condition_does_not_turn_deliberate_start_skip_into_failure(tmp_path):
    cfg, value = setup(tmp_path, forward_logs=False)
    with DAG(dag_id="expired-start", schedule=None) as dag:
        supervisor = Supervisor(dag=dag, cfg=cfg, xmlrpc_client=value)
    supervisor.check_programs._check_end_conditions = Mock(return_value="expired")
    with patch("airflow_supervisor.airflow.local.start_programs") as start:
        assert supervisor.get_step_kwargs("start-programs")["python_callable"]() is False
    start.assert_not_called()


@pytest.mark.parametrize("operator", [Supervisor, SupervisorSSH])
def test_direct_callbacks_reach_failure_finalizers_and_skipped_steps(tmp_path, operator):
    callback = Mock()
    cfg_type = SupervisorSSHAirflowConfiguration if operator is SupervisorSSH else SupervisorAirflowConfiguration
    cfg = cfg_type(working_dir=tmp_path, program={"demo": {"command": "/bin/sleep 1"}}, cleanup=False)
    value = client(cfg)
    with DAG(dag_id=f"callback-{operator.__name__}", schedule=None) as dag:
        supervisor = operator(dag=dag, cfg=cfg, xmlrpc_client=value, task_id="wrapper", on_failure_callback=[callback])
    assert all(task.on_failure_callback == [callback] for task in dag.tasks)
    assert supervisor.supervisor_client is value


def test_accepted_exit_status_does_not_publish_failure(tmp_path):
    cfg, value = setup(tmp_path, exitcodes=[0, 42])
    value.getAllProcessInfo.return_value = [info("EXITED", 42)]
    ti = TI()
    assert check_supervisor_health(cfg, require_running=False, supervisor_client=value, ti=ti)["healthy"]
    assert "supervisor_failure" not in ti.values


def test_persistent_service_clean_exit_has_failure_snapshot(tmp_path):
    cfg, value = setup(tmp_path)
    value.getAllProcessInfo.return_value = [info("EXITED", 0)]
    ti = TI()
    with pytest.raises(AirflowException):
        check_supervisor_health(cfg, supervisor_client=value, ti=ti)
    assert ti.values["supervisor_failure"][0]["exitstatus"] == 0


def test_monitor_retains_unhealthy_snapshot_after_recovery(tmp_path):
    from airflow_ha import Action, Result

    cfg, value = setup(tmp_path)
    with DAG(dag_id="monitor-recovery", schedule=None) as dag:
        supervisor = Supervisor(dag=dag, cfg=cfg, xmlrpc_client=value)
    monitor = supervisor.get_step_kwargs("check-programs")["python_callable"]
    ti = TI()
    value.getAllProcessInfo.return_value = [info("FATAL")]
    assert monitor(ti=ti) == (Result.FAIL, Action.RETRIGGER)
    value.getAllProcessInfo.return_value = [info()]
    assert monitor(ti=ti) == (Result.PASS, Action.CONTINUE)
    assert ti.values["supervisor_process_status"][0]["state"] == "RUNNING"
    assert ti.values["supervisor_failure"][0]["state"] == "FATAL"


def test_monitor_publishes_empty_workload_failure(tmp_path):
    from airflow_ha import Action, Result

    cfg, value = setup(tmp_path)
    cfg.program = {}
    value.getAllProcessInfo.return_value = []
    with DAG(dag_id="empty-monitor", schedule=None) as dag:
        supervisor = Supervisor(dag=dag, cfg=cfg, xmlrpc_client=value)
    ti = TI()
    assert supervisor.get_step_kwargs("check-programs")["python_callable"](ti=ti) == (Result.FAIL, Action.RETRIGGER)
    assert ti.values["supervisor_failure"] == []


def test_stop_forwards_output_before_and_during_shutdown_once(tmp_path, caplog):
    cfg, value = setup(tmp_path)
    value._client.supervisor.stdout = b"before stop\n"
    with DAG(dag_id="shutdown-output", schedule=None) as dag:
        supervisor = Supervisor(dag=dag, cfg=cfg, xmlrpc_client=value)

    def stop(*args, **kwargs):
        value._client.supervisor.stdout += b"during stop\n"
        return True

    caplog.set_level(logging.INFO)
    with patch("airflow_supervisor.airflow.local.stop_programs", side_effect=stop):
        assert supervisor.get_step_kwargs("stop-programs")["python_callable"]()
    assert caplog.text.count(" stdout] before stop") == 1
    assert caplog.text.count(" stdout] during stop") == 1


def test_start_baseline_avoids_replaying_output_from_previous_lifecycle(tmp_path, caplog):
    cfg, value = setup(tmp_path)
    value._client.supervisor.stdout = b"historical output\n"
    with DAG(dag_id="fresh-output", schedule=None) as dag:
        supervisor = Supervisor(dag=dag, cfg=cfg, xmlrpc_client=value)
    supervisor.check_programs._check_end_conditions = Mock(return_value=None)

    def start(*args, **kwargs):
        value._client.supervisor.stdout += b"current output\n"
        return True

    caplog.set_level(logging.INFO)
    with patch("airflow_supervisor.airflow.local.start_programs", side_effect=start):
        assert supervisor.get_step_kwargs("start-programs")["python_callable"]()
    supervisor.get_step_kwargs("check-programs")["python_callable"]()
    assert "historical output" not in caplog.text
    assert " stdout] current output" in caplog.text
