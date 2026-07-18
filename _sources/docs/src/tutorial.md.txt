# Tutorial: run a supervised job from Airflow

In this tutorial, we will define a supervisord-managed job in `airflow-config`
YAML and load it as an Airflow DAG.

## Install the packages

For Airflow 3, run:

```bash
pip install 'airflow-supervisor[airflow3]' airflow-config supervisor
```

Use the `airflow` extra instead when running Airflow 2. The Airflow worker must
be allowed to launch the configured command and write the working directory.

## Define the DAG

Create `config/supervisor.yaml`:

```yaml
dags:
  nightly-supervisor:
    schedule: "@daily"
    start_date: "2024-01-01"
    catchup: false
    tasks:
      run-nightly:
        _target_: airflow_supervisor.SupervisorTask
        cfg:
          working_dir: /var/tmp/nightly-supervisor
          port: "127.0.0.1:9001"
          stop_on_exit: true
          cleanup: true
          program:
            nightly:
              command: python /opt/jobs/nightly.py
```

## Load the configuration

Create `nightly_supervisor.py` in the DAG folder:

```python
from airflow_config import load_config

config = load_config("config", "supervisor")
config.generate_in_mem()
```

## Inspect the lifecycle

Parse the DAG folder:

```bash
airflow dags list | grep nightly-supervisor
airflow tasks list nightly-supervisor
```

The task list includes configure, daemon start, program start, check, restart,
program stop, daemon stop, and unconfigure steps.

Trigger the DAG in a test environment containing `/opt/jobs/nightly.py`. The
check step remains active while the program runs and completes after supervisord
reports an accepted exit status.

You have now connected a declarative Airflow DAG to a dedicated process manager.
