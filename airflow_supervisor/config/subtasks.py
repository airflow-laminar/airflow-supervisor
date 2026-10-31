from airflow_pydantic import Task, get_import_path
from pydantic import BaseModel, Field, SerializeAsAny, field_serializer, field_validator

__all__ = ("SupervisorSubtasks",)


class SupervisorSubtasks(BaseModel):
    subtasks: dict[str, SerializeAsAny[Task]] = Field(default_factory=dict)

    @field_validator("subtasks", mode="before")
    @classmethod
    def _load_tasks(cls, values):
        result = {}
        for name, value in values.items():
            if isinstance(value, dict):
                payload = value.copy()
                model = get_import_path(payload.pop("_target_")) if "_target_" in payload else Task
                if not isinstance(model, type) or not issubclass(model, Task):
                    raise TypeError(f"Subtask {name} must use an airflow-pydantic Task model")
                value = model.model_validate(payload)
            result[name] = value
        return result

    @field_serializer("subtasks")
    def _dump_tasks(self, values, info):
        return {
            name: {
                "_target_": f"{type(task).__module__}.{type(task).__name__}",
                **task.model_dump(mode=info.mode, exclude_unset=True),
            }
            for name, task in values.items()
        }
