# airflow_supervisor.SupervisorSSHAirflowConfiguration

### *pydantic model* airflow_supervisor.SupervisorSSHAirflowConfiguration[[source]](../../../_modules/airflow_supervisor/config/supervisor_ssh.html.md#SupervisorSSHAirflowConfiguration)

Bases: [`SupervisorAirflowConfiguration`](airflow_supervisor.SupervisorAirflowConfiguration.html.md#airflow_supervisor.SupervisorAirflowConfiguration)

#### *field* command_prefix *: str | None* *= ''*

#### *field* ssh_operator_args *: SSHTaskArgs | None* *= None*

SSH Operator arguments to use for remote execution.

#### *field* local_or_remote *: Literal['local', 'remote'] | None* *= 'remote'*

Location of supervisor, either local for same-machine or remote. If same-machine, communicates via Unix sockets by default, if remote, communicates via inet http server
