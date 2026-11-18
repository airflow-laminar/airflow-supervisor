from airflow_pydantic import ImportPath, Task, TaskArgs
from pydantic import Field, field_validator

from .subtasks import SupervisorSubtasks, render_with_subtasks
from .supervisor import SupervisorAirflowConfiguration

__all__ = (
    "SupervisorOperator",
    "SupervisorOperatorArgs",
    "SupervisorTask",
    "SupervisorTaskArgs",
)


class SupervisorTaskArgs(TaskArgs, SupervisorSubtasks):
    cfg: SupervisorAirflowConfiguration


# Alias
SupervisorOperatorArgs = SupervisorTaskArgs


class SupervisorTask(Task, SupervisorTaskArgs):
    operator: ImportPath = Field(default="airflow_supervisor.Supervisor", validate_default=True)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: type) -> type:
        if not isinstance(v, type) and issubclass(v, SupervisorAirflowConfiguration):
            raise TypeError(f"operator must be 'airflow_supervisor.Supervisor', got: {v}")
        return v

    def render(self, raw=False, dag_from_context=False, airflow_major_version=2, **kwargs):
        rendered = super().render(
            raw=True, dag_from_context=dag_from_context, airflow_major_version=airflow_major_version, **kwargs
        )
        return render_with_subtasks(rendered, self.subtasks, raw, airflow_major_version)


# Alias
SupervisorOperator = SupervisorTask
