# airflow_supervisor.SupervisorSSH

### *class* airflow_supervisor.SupervisorSSH(dag: DAG, cfg: [SupervisorSSHAirflowConfiguration](airflow_supervisor.SupervisorSSHAirflowConfiguration.md#airflow_supervisor.SupervisorSSHAirflowConfiguration), host: Host = None, port: Port = None, \*\*kwargs)

Bases: [`Supervisor`](airflow_supervisor.Supervisor.md#airflow_supervisor.Supervisor)

#### \_\_init_\_(dag: DAG, cfg: [SupervisorSSHAirflowConfiguration](airflow_supervisor.SupervisorSSHAirflowConfiguration.md#airflow_supervisor.SupervisorSSHAirflowConfiguration), host: Host = None, port: Port = None, \*\*kwargs)

### Methods

| [`__init__`](#airflow_supervisor.SupervisorSSH.__init__)(dag, cfg[, host, port])   |    |
|------------------------------------------------------------------------------------|----|
| `get_base_operator_kwargs`()                                                       |    |
| `get_step_kwargs`(step)                                                            |    |
| `get_step_operator`(step)                                                          |    |
| `initialize_tasks`()                                                               |    |
| `set_downstream`(other)                                                            |    |
| `set_upstream`(other)                                                              |    |
| `setup_dag`()                                                                      |    |
| `update_relative`(other[, upstream, edge_modifier])                                |    |

### Attributes

| `check_programs`         |                               |
|--------------------------|-------------------------------|
| `configure_supervisor`   |                               |
| `leaves`                 | Return the leaves of the DAG. |
| `restart_programs`       |                               |
| `roots`                  | Return the roots of the DAG.  |
| `start_programs`         |                               |
| `start_supervisor`       |                               |
| `stop_programs`          |                               |
| `stop_supervisor`        |                               |
| `supervisor_client`      |                               |
| `unconfigure_supervisor` |                               |
