# airflow_supervisor.SupervisorTask

### *pydantic model* airflow_supervisor.SupervisorTask[[source]](../../../_modules/airflow_supervisor/config/task.html.md#SupervisorTask)

Bases: `Task`, [`SupervisorTaskArgs`](airflow_supervisor.SupervisorTaskArgs.html.md#airflow_supervisor.SupervisorTaskArgs)

#### *field* operator *: Annotated[type, BeforeValidator(func=get_import_path, json_schema_input_type=PydanticUndefined), PlainSerializer(func=serialize_path_as_string, return_type=str, when_used=json)]* *= 'airflow_supervisor.Supervisor'*
