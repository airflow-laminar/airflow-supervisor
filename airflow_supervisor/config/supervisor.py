from datetime import time, timedelta
from graphlib import TopologicalSorter
from typing import Literal

from airflow_pydantic import Pool
from pydantic import Field, model_validator
from supervisor_pydantic import SupervisorConvenienceConfiguration

from .program import ProgramLifecycleConfiguration

__all__ = (
    "SupervisorAirflowConfiguration",
    "load_airflow_config",
)


_PRESETS = {
    "always_on": {
        "runtime": timedelta(days=7),
        "stop_on_exit": False,
        "cleanup": False,
        "restart_on_initial": True,
        "restart_on_retrigger": False,
    },
    "daily": {
        "runtime": timedelta(days=1),
        "stop_on_exit": True,
        "cleanup": True,
        "restart_on_initial": False,
        "restart_on_retrigger": False,
    },
    "half_day": {
        "runtime": timedelta(hours=12),
        "endtime": time(20),
        "maxretrigger": 10,
        "stop_on_exit": True,
        "cleanup": False,
        "restart_on_initial": False,
        "restart_on_retrigger": False,
    },
}


class SupervisorAirflowConfiguration(SupervisorConvenienceConfiguration):
    """Settings that MUST be set when running in airflow"""

    forward_logs: bool = Field(default=True, description="Forward program stdout and stderr into Airflow task logs")
    log_chunk_size: int = Field(
        default=65536, gt=0, le=1048576, description="Log read budget in bytes per program stream on each poll"
    )

    # Passthrough to PythonSensor in airflow-ha
    check_interval: timedelta = Field(
        default=timedelta(seconds=5), description="Interval between supervisor program status checks"
    )
    check_timeout: timedelta = Field(
        default=timedelta(hours=8), description="Timeout to wait for supervisor program status checks"
    )

    # HighAvailabilityOperator custom args
    runtime: timedelta | None = Field(default=None, description="Max runtime of Supervisor job")
    endtime: time | None = Field(default=None, description="End time of Supervisor job")
    maxretrigger: int | None = Field(
        default=None,
        description="Max number of retriggers of Supervisor job (e.g. max number of checks separated by `check_interval`)",
    )

    reference_date: Literal["start_date", "logical_date", "data_interval_end"] = Field(
        default="data_interval_end",
        description="Reference date for the job. NOTE: Airflow schedules after end of date interval, so `data_interval_end` is the default",
    )

    # Airflow-specific settings
    pool: str | Pool | None = Field(
        default=None,
        description="Airflow pool to use for the job. If not set, the job will use the default pool, or the pool from a balancer host.",
    )

    """Other Airflow Configuration"""
    # Should the programs be stopped when the DAG finishes?
    stop_on_exit: bool | None = Field(default=True, description="Stop supervisor on dag completion")

    # Should the supervisor folder be removed on dag completion?
    cleanup: bool | None = Field(
        default=True, description="Cleanup supervisor folder on dag completion. Note: stop_on_exit must be True"
    )

    # For Jobs that do not shutdown, e.g. stop_on_exit=False, one might want to configure them to
    # restart when the DAG is rescheduled by airflow or retriggered by airflow-ha
    restart_on_initial: bool | None = Field(
        default=False,
        description="Restart the job when the DAG is run directly via airflow (NOT retriggered). This is useful for jobs that do not shutdown",
    )
    restart_on_retrigger: bool | None = Field(
        default=False,
        description="Restart the job when the DAG is retriggered. This is useful for jobs that do not shutdown",
    )

    preset: Literal["always_on", "daily", "half_day"] | None = Field(
        default=None, description="Lifecycle defaults applied before explicit configuration values"
    )

    program_lifecycle: dict[str, ProgramLifecycleConfiguration] | None = Field(
        default=None, description="Enable discrete Airflow tasks and policies for configured Supervisor program groups"
    )

    @model_validator(mode="after")
    def _validate_program_lifecycle(self):
        if self.program_lifecycle is None:
            return self
        names = set(self.program) | set(self.fcgiprogram or {})
        for group in (self.group or {}).values():
            names.difference_update(group.programs)
        names.update(self.group or {})
        if not names:
            raise ValueError("program_lifecycle requires at least one Supervisor program group")
        unknown = set(self.program_lifecycle) - names
        if unknown:
            raise ValueError(f"Unknown Supervisor program groups: {sorted(unknown)}")
        start_graph = {name: set() for name in names}
        stop_graph = {name: set() for name in names}
        for name, policy in self.program_lifecycle.items():
            unknown = (set(policy.start_after) | set(policy.stop_before)) - names
            if unknown:
                raise ValueError(f"Unknown lifecycle dependencies for {name}: {sorted(unknown)}")
            start_graph[name].update(policy.start_after)
            for parent in policy.start_after:
                stop_graph[parent].add(name)
            for after in policy.stop_before:
                stop_graph[after].add(name)
            if policy.required and policy.max_consecutive_failures is not None:
                raise ValueError(f"{name}: max_consecutive_failures requires required=False")
        tuple(TopologicalSorter(start_graph).static_order())
        tuple(TopologicalSorter(stop_graph).static_order())
        return self

    @model_validator(mode="before")
    @classmethod
    def _apply_preset(cls, values):
        if isinstance(values, dict) and isinstance(values.get("preset"), str) and values["preset"] in _PRESETS:
            return {
                "check_interval": timedelta(seconds=30),
                "check_timeout": timedelta(hours=8),
                **_PRESETS[values["preset"]],
                **values,
            }
        return values


load_airflow_config = SupervisorAirflowConfiguration.load
