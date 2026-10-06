# airflow-supervisor

Run and monitor supervisord-managed jobs from Apache Airflow.

[![Build Status](https://github.com/airflow-laminar/airflow-supervisor/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/airflow-laminar/airflow-supervisor/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/airflow-laminar/airflow-supervisor/branch/main/graph/badge.svg)](https://codecov.io/gh/airflow-laminar/airflow-supervisor)
[![License](https://img.shields.io/github/license/airflow-laminar/airflow-supervisor)](https://github.com/airflow-laminar/airflow-supervisor)
[![PyPI](https://img.shields.io/pypi/v/airflow-supervisor.svg)](https://pypi.python.org/pypi/airflow-supervisor)

Manage a dedicated supervisord instance on an Airflow worker or an SSH host.
Define its programs directly in a Python DAG or in `airflow-config` YAML.

```python
from datetime import datetime, timezone

from airflow import DAG
from airflow_supervisor import ProgramConfiguration, Supervisor, SupervisorAirflowConfiguration

with DAG(
    dag_id="nightly-supervisor",
    schedule="@daily",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
) as dag:
    supervisor = Supervisor(
        dag=dag,
        cfg=SupervisorAirflowConfiguration(
            working_dir="/var/tmp/nightly-supervisor",
            port="127.0.0.1:9001",
            program={"nightly": ProgramConfiguration(command="/bin/sleep 5")},
        ),
    )
```

The lifecycle writes configuration, starts supervisord and its programs, monitors
program state with `airflow-ha`, and stops and removes the instance on successful
completion. `SupervisorSSH` runs configuration and daemon commands over SSH;
program control and checks use the remote XML-RPC endpoint.

## Documentation

Start with the [tutorial](docs/src/tutorial.md) to run a self-contained local job
and check its cleanup. For an existing deployment, choose a how-to guide:

| Execution    | Inline Python                                                                | `airflow-config` YAML                                                                    |
| ------------ | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Local worker | [Run a local job](docs/src/how-to.md#how-to-run-a-local-job-in-python)       | [Configure a local job](docs/src/how-to.md#how-to-run-a-local-job-with-airflow-config)   |
| SSH host     | [Run a job over SSH](docs/src/how-to.md#how-to-run-a-job-over-ssh-in-python) | [Configure an SSH job](docs/src/how-to.md#how-to-run-a-job-over-ssh-with-airflow-config) |

The [API reference](docs/src/api.md) describes configuration fields, defaults,
and DAG constraints. [Why Airflow delegates process ownership](docs/src/explanation.md)
explains worker placement, SSH and XML-RPC, and the Python/YAML configuration
choices.

Use the [log forwarding and health-check guide](docs/src/observability.md) to
collect program output in task logs and monitor retained services between runs.

Published documentation is available at
[airflow-laminar.github.io/airflow-supervisor](https://airflow-laminar.github.io/airflow-supervisor/).

## Ecosystem

- [supervisor-pydantic](https://github.com/airflow-laminar/supervisor-pydantic) supplies supervisord models and lifecycle tools.
- [systemd-pydantic](https://github.com/airflow-laminar/systemd-pydantic) and [cron-pydantic](https://github.com/airflow-laminar/cron-pydantic) model alternative runtimes.
- [airflow-systemd](https://github.com/airflow-laminar/airflow-systemd) provides the analogous systemd lifecycle.
- [airflow-cron](https://github.com/airflow-laminar/airflow-cron) converts cron jobs into ordinary Airflow tasks.
- [airflow-pydantic](https://github.com/airflow-laminar/airflow-pydantic) supplies declarative task, host, and connection models.
- [airflow-config](https://github.com/airflow-laminar/airflow-config) produces YAML-driven DAGs.

> [!NOTE]
> This library was generated using [copier](https://copier.readthedocs.io/en/stable/) from the [Base Python Project Template repository](https://github.com/python-project-templates/base).
