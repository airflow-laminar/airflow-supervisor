from typing import Literal

from airflow.exceptions import AirflowSkipException

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


__all__ = (
    "SupervisorTaskStep",
    "skip_",
)
