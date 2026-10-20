# Tutorial: run your first supervised job

We will run a five-second job under supervisord, monitor it from Airflow, and
remove its configuration when it finishes.

Use an initialized Airflow 2 environment on a Unix host, with all tasks
running on that host. Port 9001 must be available, and the Airflow user must be
able to write `/var/tmp/airflow-supervisor-demo`.

## Install the integration

In the Airflow environment, run:

```bash
pip install 'airflow-supervisor[airflow]' supervisor
```

Check that the daemon is available:

```bash
supervisord --version
```

The command prints the installed Supervisor version.

## Create the DAG

Save this as `supervisor_demo.py` in your Airflow DAG folder:

```python
from datetime import datetime, timezone

from airflow import DAG
from airflow_supervisor import ProgramConfiguration, Supervisor, SupervisorAirflowConfiguration

with DAG(
    dag_id="supervisor-demo",
    schedule=None,
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
) as dag:
    supervisor = Supervisor(
        dag=dag,
        cfg=SupervisorAirflowConfiguration(
            working_dir="/var/tmp/airflow-supervisor-demo",
            port="127.0.0.1:9001",
            program={"demo": ProgramConfiguration(command="/bin/sleep 5")},
        ),
    )
```

List the generated tasks:

```bash
airflow tasks list supervisor-demo
```

Look for `supervisor-demo-configure-supervisor`,
`supervisor-demo-start-programs`, and `supervisor-demo-check-programs`.
The DAG also contains restart, shutdown, cleanup, and failure-handling tasks.

## Run the job

Execute one DAG run locally:

```bash
airflow dags test supervisor-demo 2025-01-01
```

The configure task writes `supervisord.conf` and `pydantic.json`. The startup
tasks launch supervisord and `/bin/sleep`. After the program exits with status 0,
the check task takes its success branch. The shutdown tasks stop the daemon and
remove the working directory. The DAG run finishes with state `success`;
restart and force-kill branches are skipped during this run.

Check that cleanup completed:

```bash
test ! -d /var/tmp/airflow-supervisor-demo && echo "Cleanup complete"
```

You should see `Cleanup complete`.

For your own jobs, follow the [local and SSH guides](how-to.md). The
[configuration reference](api.md) lists lifecycle and monitoring settings.
