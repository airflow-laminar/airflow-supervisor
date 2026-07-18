# airflow-supervisor

Run and monitor supervisord-managed jobs from Apache Airflow.

[![Build Status](https://github.com/airflow-laminar/airflow-supervisor/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/airflow-laminar/airflow-supervisor/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/airflow-laminar/airflow-supervisor/branch/main/graph/badge.svg)](https://codecov.io/gh/airflow-laminar/airflow-supervisor)
[![License](https://img.shields.io/github/license/airflow-laminar/airflow-supervisor)](https://github.com/airflow-laminar/airflow-supervisor)
[![PyPI](https://img.shields.io/pypi/v/airflow-supervisor.svg)](https://pypi.python.org/pypi/airflow-supervisor)

```python
from airflow import DAG
from airflow_supervisor import ProgramConfiguration, Supervisor, SupervisorAirflowConfiguration

dag = DAG(dag_id="nightly-supervisor", schedule="@daily")
config = SupervisorAirflowConfiguration(
    working_dir="/var/tmp/nightly-supervisor",
    program={
        "nightly": ProgramConfiguration(command="python /opt/jobs/nightly.py"),
    },
)
Supervisor(dag=dag, cfg=config)
```

The generated lifecycle creates a dedicated supervisord instance, starts and
monitors programs with `airflow-ha`, handles retriggers, and optionally stops and
removes the instance. `SupervisorSSH` manages the same lifecycle remotely.

## Documentation

- [Tutorial: run a supervised job from Airflow](docs/src/tutorial.md)
- [How-to guides](docs/src/how-to.md)
- [Why Airflow delegates process ownership](docs/src/explanation.md)
- [API reference](docs/src/api.md)

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
