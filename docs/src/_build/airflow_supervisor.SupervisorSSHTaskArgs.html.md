# airflow_supervisor.SupervisorSSHTaskArgs

### *pydantic model* airflow_supervisor.SupervisorSSHTaskArgs

Bases: `TaskArgs`

#### *field* cfg *: [SupervisorSSHAirflowConfiguration](airflow_supervisor.SupervisorSSHAirflowConfiguration.md#airflow_supervisor.SupervisorSSHAirflowConfiguration)* *[Required]*

#### *field* host *: Host | BalancerHostQueryConfiguration | Annotated[object, BeforeValidator(func=get_import_path, json_schema_input_type=PydanticUndefined), PlainSerializer(func=serialize_path_as_string, return_type=str, when_used=json)] | None* *= None*

The host to connect to for SSH, if not otherwise provided in configs

#### *field* host_foo *: Annotated[object, BeforeValidator(func=get_import_path, json_schema_input_type=PydanticUndefined), PlainSerializer(func=serialize_path_as_string, return_type=str, when_used=json)] | None* *= None*

#### *field* port *: Port | BalancerPortQueryConfiguration | Annotated[object, BeforeValidator(func=get_import_path, json_schema_input_type=PydanticUndefined), PlainSerializer(func=serialize_path_as_string, return_type=str, when_used=json)] | None* *= None*

The port to user for Supervisor, if not otherwise provided in configs

#### *field* port_foo *: Annotated[object, BeforeValidator(func=get_import_path, json_schema_input_type=PydanticUndefined), PlainSerializer(func=serialize_path_as_string, return_type=str, when_used=json)] | None* *= None*
