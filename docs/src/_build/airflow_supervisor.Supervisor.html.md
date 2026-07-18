# airflow_supervisor.Supervisor

### *class* airflow_supervisor.Supervisor(dag: DAG, cfg: [SupervisorAirflowConfiguration](airflow_supervisor.SupervisorAirflowConfiguration.md#airflow_supervisor.SupervisorAirflowConfiguration), \*\*kwargs)

Bases: `object`

#### \_\_init_\_(dag: DAG, cfg: [SupervisorAirflowConfiguration](airflow_supervisor.SupervisorAirflowConfiguration.md#airflow_supervisor.SupervisorAirflowConfiguration), \*\*kwargs)

### Methods

| [`__init__`](#airflow_supervisor.Supervisor.__init__)(dag, cfg, \*\*kwargs)   |    |
|-------------------------------------------------------------------------------|----|
| `get_base_operator_kwargs`()                                                  |    |
| `get_step_kwargs`(step)                                                       |    |
| `get_step_operator`(step)                                                     |    |
| `initialize_tasks`()                                                          |    |
| `set_downstream`(other)                                                       |    |
| `set_upstream`(other)                                                         |    |
| `setup_dag`()                                                                 |    |
| `update_relative`(other[, upstream, edge_modifier])                           |    |

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
