# airflow_supervisor.Supervisor

### *class* airflow_supervisor.Supervisor(dag: DAG, cfg: [SupervisorAirflowConfiguration](airflow_supervisor.SupervisorAirflowConfiguration.html.md#airflow_supervisor.SupervisorAirflowConfiguration), \*\*kwargs)[[source]](../../../_modules/airflow_supervisor/airflow/local.html.md#Supervisor)

Bases: `object`

#### \_\_init_\_(dag: DAG, cfg: [SupervisorAirflowConfiguration](airflow_supervisor.SupervisorAirflowConfiguration.html.md#airflow_supervisor.SupervisorAirflowConfiguration), \*\*kwargs)[[source]](../../../_modules/airflow_supervisor/airflow/local.html.md#Supervisor.__init__)

### Methods

| [`__init__`](#airflow_supervisor.Supervisor.__init__)(dag, cfg, \*\*kwargs)   |                                                                             |
|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| `get_base_operator_kwargs`()                                                  |                                                                             |
| `get_step_kwargs`(step)                                                       |                                                                             |
| `get_step_operator`(step)                                                     |                                                                             |
| `initialize_tasks`()                                                          |                                                                             |
| `program_operator`(program, action, \*\*kwargs)                               | Create a discrete start, stop, or restart task for a managed program group. |
| `set_downstream`(other)                                                       |                                                                             |
| `set_upstream`(other)                                                         |                                                                             |
| `setup_dag`()                                                                 |                                                                             |
| `update_relative`(other[, upstream, edge_modifier])                           |                                                                             |

### Attributes

| `check_programs`         |                                                                           |
|--------------------------|---------------------------------------------------------------------------|
| `configure_supervisor`   |                                                                           |
| `leaves`                 | Return the leaves of the DAG.                                             |
| `program_tasks`          | Discrete start, delay, and stop tasks, keyed by Supervisor program group. |
| `restart_programs`       |                                                                           |
| `roots`                  | Return the roots of the DAG.                                              |
| `start_programs`         |                                                                           |
| `start_supervisor`       |                                                                           |
| `stop_programs`          |                                                                           |
| `stop_supervisor`        |                                                                           |
| `supervisor_client`      |                                                                           |
| `unconfigure_supervisor` |                                                                           |
