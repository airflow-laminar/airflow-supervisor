# airflow-supervisor

[Apache Airflow](https://airflow.apache.org) utilities for running long-running or always-on jobs with [supervisord](http://supervisord.org)

[![Build Status](https://github.com/timkpaine/airflow-supervisor/actions/workflows/build.yml/badge.svg)](https://github.com/timkpaine/airflow-supervisor/actions?query=workflow%3A%22Build+Status%22)
[![codecov](https://codecov.io/gh/timkpaine/airflow-supervisor/branch/main/graph/badge.svg)](https://codecov.io/gh/timkpaine/airflow-supervisor)
[![License](https://img.shields.io/github/license/timkpaine/airflow-supervisor)](https://github.com/timkpaine/airflow-supervisor)
[![PyPI](https://img.shields.io/pypi/v/airflow-supervisor.svg)](https://pypi.python.org/pypi/airflow-supervisor)

## Overview

This library provides a configuration-driven way of generating [supervisor](http://supervisord.org) configurations and airflow [operators](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/operators.html)/[sensors](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) for long-running or always-on jobs. Configuration is managed by [Pydantic](https://pydantic.dev), [Hydra](https://hydra.cc), and [OmegaConf](https://omegaconf.readthedocs.io/).

## How To: Use in Airflow

`airflow-supervisor` can be installed in your airflow server environment and imported in your dag files. It provides two convenient top level DAG subclasses:

- `SupervisorLocal`: creates a DAG representing a local supervisor instance running on the airflow worker node (underlying task will use `PythonOperator` and `BashOperator` to communicate between airflow and supervisor)
- `SupervisorRemote`: creates a DAG representing a remote supervisor instance running on another machine (underlying tasks will use `SSHOperator` to communicate between airflow and supervisor)

We expose DAGs composed of a variety of tasks and sensors, which are exposed as a discrete pipeline of steps:
1. Setup `supervisord` configuration
2. Start the `supervisord` daemon
3. Start the supervised programs with `supervisorctl`
4. Start sensors to query the programs' state via [supervisor's XML-RPC API](http://supervisord.org/api.html)
5. Evaluate and take action according to the program's state changes
6. Restart programs if necessary
7. Tear down the sensors from (4)
8. Stop the supervised programs from (3)
9. Stop the `supervisord` daemon from (2)
10. Remove configuration from (1)

This setup provides maximal configureability with a minimal requirements on the machine (for example, no requirements on an existing `supervisord` daemon via e.g. `systemd`). It also lets you hook your own tasks into any step of the process. For example, if we detect a process has died in step (5), you could configure your own task to take some custom action before/instead of the default restart of step 6.

Here is a nice overview of the DAG, with annotations for code paths and the actions taken by Supervisor:

<img src="https://raw.githubusercontent.com/airflow-laminar/airflow-supervisor/main/docs/img/overview.png" />

More docs and code examples coming soon!

### Example Dag:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow_supervisor import (
    Supervisor,
    SupervisorAirflowConfiguration,
    ProgramConfiguration,
    AirflowConfiguration,
)


# Create supervisor configuration
cfg = SupervisorAirflowConfiguration(
    airflow=AirflowConfiguration(port="*:9091"),
    working_dir="/data/airflow/supervisor",
    config_path="/data/airflow/supervisor/supervisor.conf",
    program={
        "test": ProgramConfiguration(
            command="bash -c 'sleep 14400; exit 1'",
        )
    },
)

# Create DAG as normal
with DAG(
    dag_id="test-supervisor",
    schedule=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    # Link supervisor config to dag
    supervisor = Supervisor(dag=dag, cfg=cfg)
```

## Example DAG: [`airflow-config`](https://github.com/airflow-laminar/airflow-config)


```yaml
# @package _global_
_target_: airflow_config.Configuration
default_args:
  _target_: airflow_config.DefaultArgs
  retries: 0
  depends_on_past: false
all_dags:
  _target_: airflow_config.DagArgs
  start_date: "2024-01-01"
  catchup: false
extensions:
  supervisor:
    _target_: airflow_supervisor.SupervisorAirflowConfiguration
    airflow:
      _target_: airflow_supervisor.AirflowConfiguration
      port: "*:9091"
    working_dir: "/data/airflow/supervisor"
    config_path: "/data/airflow/supervisor/supervisor.conf"
    program:
      test:
        _target_: airflow_supervisor.ProgramConfiguration
        command: "bash -c 'sleep 14400; exit 1'"
```

```python
from datetime import timedelta
from airflow_config import load_config, DAG
from airflow_supervisor import Supervisor

config = load_config(config_name="airflow")

with DAG(
    dag_id="test-supervisor",
    schedule=timedelta(days=1),
    config=config,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=config.extensions["supervisor"])
```

## How To: Use as a supervisord configuration frontend

This library can be used outside airflow as a generic supervisord configuration framework, with the static typing benefits that entails. For an example, look at the [hydra configuration test](./airflow_supervisor/tests/hydra/test_hydra.py). This example generates a supervisor configuration file by composing independent hydra configs.
