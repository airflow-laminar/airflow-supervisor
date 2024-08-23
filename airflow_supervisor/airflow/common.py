from airflow.exceptions import AirflowFailException, AirflowSkipException
from typing import Literal

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


def skip_():
    raise AirflowSkipException


def fail_():
    raise AirflowFailException


def pass_():
    pass


__all__ = (
    "SupervisorTaskStep",
    "pass_",
    "fail_",
    "skip_",
)
