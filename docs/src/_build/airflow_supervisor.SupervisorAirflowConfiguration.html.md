# airflow_supervisor.SupervisorAirflowConfiguration

### *pydantic model* airflow_supervisor.SupervisorAirflowConfiguration

Bases: [`SupervisorConvenienceConfiguration`](airflow_supervisor.SupervisorConvenienceConfiguration.md#airflow_supervisor.SupervisorConvenienceConfiguration)

Settings that MUST be set when running in airflow

#### *field* check_interval *: timedelta* *= datetime.timedelta(seconds=5)*

Interval between supervisor program status checks

#### *field* check_timeout *: timedelta* *= datetime.timedelta(seconds=28800)*

Timeout to wait for supervisor program status checks

#### *field* runtime *: timedelta | None* *= None*

Max runtime of Supervisor job

#### *field* endtime *: time | None* *= None*

End time of Supervisor job

#### *field* maxretrigger *: int | None* *= None*

Max number of retriggers of Supervisor job (e.g. max number of checks separated by check_interval)

#### *field* reference_date *: Literal['start_date', 'logical_date', 'data_interval_end']* *= 'data_interval_end'*

Reference date for the job. NOTE: Airflow schedules after end of date interval, so data_interval_end is the default

#### *field* pool *: str | Pool | None* *= None*

Other Airflow Configuration

Airflow pool to use for the job. If not set, the job will use the default pool, or the pool from a balancer host.

#### *field* stop_on_exit *: bool | None* *= True*

Stop supervisor on dag completion

#### *field* cleanup *: bool | None* *= True*

Cleanup supervisor folder on dag completion. Note: stop_on_exit must be True

#### *field* restart_on_initial *: bool | None* *= False*

Restart the job when the DAG is run directly via airflow (NOT retriggered). This is useful for jobs that do not shutdown

#### *field* restart_on_retrigger *: bool | None* *= False*

Restart the job when the DAG is retriggered. This is useful for jobs that do not shutdown
