import ast

from airflow_pydantic import Task, get_import_path
from airflow_pydantic.core.render.utils import RawRenderedCode, _get_parts_from_value
from pydantic import BaseModel, Field, SerializeAsAny, field_serializer, field_validator

__all__ = ("SupervisorSubtasks",)


def _render_subtask(name, task, airflow_major_version):
    # Task.render applies hook-specific handling, such as Variable passwords, that a plain dump loses.
    imports, _, call = Task.render(
        task.model_copy(update={"task_id": task.task_id or name}), raw=True, airflow_major_version=airflow_major_version
    )
    assert isinstance(call, ast.Call)
    keys = [ast.Constant(value="_target_")]
    values = [ast.Constant(value=f"{type(task).__module__}.{type(task).__name__}")]
    # The first import is the operator class, which the dict form never references.
    imports = imports[1:]
    for keyword in call.keywords:
        if keyword.arg != "task_id" or "task_id" in task.model_fields_set:
            keys.append(ast.Constant(value=keyword.arg))
            values.append(keyword.value)
    for key, value in task.model_dump(exclude_unset=True, include={"operator", "dependencies"}).items():
        new_imports, node = _get_parts_from_value(key, value, task, airflow_major_version=airflow_major_version)
        imports.extend(new_imports)
        keys.append(ast.Constant(value=key))
        values.append(node)
    return imports, ast.Dict(keys=keys, values=values)


def render_with_subtasks(rendered: RawRenderedCode, subtasks: dict[str, Task], raw: bool, airflow_major_version: int):
    """Replace the dumped ``subtasks`` argument of a rendered supervisor task with per-task rendering."""
    imports, globals_, call = rendered
    assert isinstance(call, ast.Call)
    for keyword in call.keywords:
        if keyword.arg == "subtasks":
            keys: list[ast.expr | None] = []
            values: list[ast.expr] = []
            for name, task in subtasks.items():
                new_imports, value = _render_subtask(name, task, airflow_major_version)
                imports.extend(new_imports)
                keys.append(ast.Constant(value=name))
                values.append(value)
            keyword.value = ast.Dict(keys=keys, values=values)
    if raw:
        return imports, globals_, call
    return [ast.unparse(i) for i in imports], [ast.unparse(i) for i in globals_], ast.unparse(call)


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
