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
    from airflow.exceptions import AirflowSkipException

    raise AirflowSkipException


__all__ = (
    "SupervisorTaskStep",
    "skip_",
)
