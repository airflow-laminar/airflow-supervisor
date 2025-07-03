from datetime import time, timedelta
from typing import Literal, Optional, Union

from airflow_pydantic import Pool
from pydantic import Field
from supervisor_pydantic import SupervisorConvenienceConfiguration

__all__ = (
    "SupervisorAirflowConfiguration",
    "load_airflow_config",
)


# PredefinedTemplates = Literal[
#     "always_on",
#     "half_day",
#     # TODO add more
# ]


class SupervisorAirflowConfiguration(SupervisorConvenienceConfiguration):
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

    reference_date: Literal["start_date", "logical_date", "data_interval_end"] = Field(
        default="data_interval_end",
        description="Reference date for the job. NOTE: Airflow schedules after end of date interval, so `data_interval_end` is the default",
    )

    # Airflow-specific settings
    pool: Optional[Union[str, Pool]] = Field(
        default=None,
        description="Airflow pool to use for the job. If not set, the job will use the default pool, or the pool from a balancer host.",
    )

    """Other Airflow Configuration"""
    # Should the programs be stopped when the DAG finishes?
    stop_on_exit: Optional[bool] = Field(default=True, description="Stop supervisor on dag completion")

    # Should the supervisor folder be removed on dag completion?
    cleanup: Optional[bool] = Field(
        default=True, description="Cleanup supervisor folder on dag completion. Note: stop_on_exit must be True"
    )

    # For Jobs that do not shutdown, e.g. stop_on_exit=False, one might want to configure them to
    # restart when the DAG is rescheduled by airflow or retriggered by airflow-ha
    restart_on_initial: Optional[bool] = Field(
        default=False,
        description="Restart the job when the DAG is run directly via airflow (NOT retriggered). This is useful for jobs that do not shutdown",
    )
    restart_on_retrigger: Optional[bool] = Field(
        default=False,
        description="Restart the job when the DAG is retriggered. This is useful for jobs that do not shutdown",
    )

    # template: Optional[PredefinedTemplates] = Field(
    #     default=None,
    #     description="A template of settings to use. This is a convenience for common settings. Individual settings will override the template.",
    # )

    # @model_validator(mode="after")
    # def _set_fields_from_template(self):
    #     if self.template == "always_on":

    #         self.stop_on_exit = False
    #         self.cleanup = False
    #         self.restart_on_initial = True
    #         self.restart_on_retrigger = True
    #     elif self.template == "half_day":
    #         self.runtime = self.runtime or self.timedelta(hours=12)
    #         self.stop_on_exit = True
    #         self.cleanup = True
    #         self.restart_on_initial = False
    #         self.restart_on_retrigger = False
    #     return self


load_airflow_config = SupervisorAirflowConfiguration.load
