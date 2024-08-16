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

More docs and code examples coming soon!

## How To: Use as a supervisord configuration frontend

This library can be used outside airflow as a generic supervisord configuration framework, with the static typing benefits that entails. For an example, look at the [hydra configuration test](./airflow_supervisor/tests/hydra/test_hydra.py). This example generates a supervisor configuration file by composing independent hydra configs.
