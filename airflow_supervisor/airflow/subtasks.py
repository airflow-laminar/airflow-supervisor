from airflow_pydantic import Pool, PythonTask, SSHTask
from airflow_pydantic.migration import _airflow_3


def apply_subtasks(supervisor, subtasks, existing_tasks):
    """Merge task options, create additional tasks, then resolve local dependencies."""
    dag = supervisor._dag
    prefix = f"{dag.dag_id}-"
    generated = {task.task_id: task for task in dag.tasks if task.task_id not in existing_tasks}
    tasks = {task_id.removeprefix(prefix): task for task_id, task in generated.items()}
    overridden = set()
    added = []
    for name, model in subtasks.items():
        task = tasks.get(name) or generated.get(name)
        task_id = task.task_id if task is not None else f"{prefix}{name}"
        if model.task_id is not None and model.task_id not in (name, task_id):
            raise ValueError(f"Subtask {name} cannot change its task ID to {model.task_id}")
        if task_id in overridden:
            raise ValueError(f"Duplicate subtask override for {task_id}")
        overridden.add(task_id)
        if task is None:
            if isinstance(model, PythonTask) and model.python_callable is None:
                raise ValueError(f"Unknown generated subtask {name}; new Python tasks require python_callable")
            if isinstance(model, SSHTask) and model.command is None:
                raise ValueError(f"Unknown generated subtask {name}; new SSH tasks require command")
            task = model.model_copy(update={"task_id": task_id}).instantiate(dag=dag)
            added.append(task)
        else:
            if not isinstance(task, model.operator):
                raise TypeError(f"Subtask {name} is {type(task).__name__}, incompatible with {model.operator.__name__}")
            for field in model.model_fields_set - {"operator", "task_id", "dependencies"}:
                if type(model).model_fields[field].exclude:
                    continue
                value = getattr(model, field)
                if field == "pool" and isinstance(value, Pool):
                    value = value.pool
                if field == "task_display_name":
                    field = "_task_display_name" if _airflow_3() else "_task_display_property_value"
                setattr(task, field, value)
        tasks[name] = task
        generated[task_id] = task

    for name, model in subtasks.items():
        if "dependencies" not in model.model_fields_set:
            continue
        task = tasks[name]
        for parent_id in tuple(task.upstream_task_ids):
            dag.get_task(parent_id).downstream_task_ids.discard(task.task_id)
        task.upstream_task_ids.clear()
        for dependency in model.dependencies or []:
            dependency, attribute = dependency if isinstance(dependency, tuple) else (dependency, None)
            parent = tasks.get(dependency) or generated.get(dependency) or dag.task_dict.get(dependency)
            if parent is None:
                raise ValueError(f"Unknown dependency {dependency} for Supervisor subtask {name}")
            if attribute:
                parent = getattr(parent, attribute)
            parent >> task
    dag.topological_sort()
    owned = {task.task_id for task in dag.tasks if task.task_id not in existing_tasks}
    supervisor._subtask_roots = [
        task for task in dag.tasks if task.task_id in owned and not task.upstream_task_ids & owned
    ]
    supervisor._subtask_leaves = [
        supervisor.unconfigure_supervisor,
        *(task for task in added if not task.downstream_task_ids & owned),
    ]
