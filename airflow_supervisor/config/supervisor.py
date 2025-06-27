from typing import Optional

from pydantic import Field
from supervisor_pydantic import SupervisorConvenienceConfiguration

from .airflow import AirflowConfiguration

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
    airflow: AirflowConfiguration = Field(
        default_factory=AirflowConfiguration, description="Required options for airflow integration"
    )

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
    #         self.airflow.runtime = self.airflow.runtime or self.airflow.timedelta(hours=12)
    #         self.stop_on_exit = True
    #         self.cleanup = True
    #         self.restart_on_initial = False
    #         self.restart_on_retrigger = False
    #     return self


load_airflow_config = SupervisorAirflowConfiguration.load
