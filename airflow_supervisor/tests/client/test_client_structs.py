from datetime import datetime

from airflow_supervisor.client import ProcessInfo, ProcessState


def _gen() -> ProcessInfo:
    return ProcessInfo(
        name="test",
        group="test",
        state=ProcessState.UNKNOWN,
        description="",
        start=datetime.now(),
        stop=datetime.now(),
        now=datetime.now(),
        spawner="",
        exitstatus=0,
        logfile="",
        stdout_logfile="",
        stderr_logfile="",
        pid=0,
    )


def test_ok():
    x = _gen()
    x.state = ProcessState.RUNNING
    assert x.ok()
    x.state = ProcessState.EXITED
    x.exitstatus = 0
    assert x.ok()
