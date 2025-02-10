from datetime import time, timedelta
from typing import Optional

from pydantic import Field
from supervisor_pydantic.config.base import _BaseCfgModel

__all__ = ("AirflowConfiguration",)


class AirflowConfiguration(_BaseCfgModel):
    """Settings that MUST be set when running in airflow"""

    # Passthrough to PythonSensor in airflow-ha
    check_interval: timedelta = Field(
        default=timedelta(seconds=5), description="Interval between supervisor program status checks"
    )
    check_timeout: timedelta = Field(
        default=timedelta(hours=8), description="Timeout to wait for supervisor program status checks"
    )

    # HighAvailabilityOperator custom args
    runtime: Optional[timedelta] = Field(default=None, description="Max runtime of Supervisor job")
    endtime: Optional[time] = Field(default=None, description="End time of Supervisor job")
    maxretrigger: Optional[int] = Field(
        default=None,
        description="Max number of retriggers of Supervisor job (e.g. max number of checks separated by `check_interval`)",
    )
