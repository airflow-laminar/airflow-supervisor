# airflow-supervisor

[Apache Airflow](https://airflow.apache.org) utilities for running long-running or always-on jobs with [supervisord](http://supervisord.org)

[![Build Status](https://github.com/timkpaine/airflow-supervisor/actions/workflows/build.yml/badge.svg)](https://github.com/timkpaine/airflow-supervisor/actions?query=workflow%3A%22Build+Status%22)
[![codecov](https://codecov.io/gh/timkpaine/airflow-supervisor/branch/main/graph/badge.svg)](https://codecov.io/gh/timkpaine/airflow-supervisor)
[![License](https://img.shields.io/github/license/timkpaine/airflow-supervisor)](https://github.com/timkpaine/airflow-supervisor)
[![PyPI](https://img.shields.io/pypi/v/airflow-supervisor.svg)](https://pypi.python.org/pypi/airflow-supervisor)

## Overview

This library provides a configuration-driven way of generating [supervisor](http://supervisord.org) configurations and airflow [operators](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/operators.html)/[sensors](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) for long-running or always-on jobs. Configuration is managed by [Pydantic](https://pydantic.dev), [Hydra](https://hydra.cc), and [OmegaConf](https://omegaconf.readthedocs.io/).

## How To: Use in Airflow

Docs coming soon!

## How To: Use as a standalone supervisord frontend

This library can be used outside airflow as a generic supervisord configuration framework, with the static typing benefits that entails. For an example, look at the [hydra configuration test](./airflow_supervisor/tests/hydra/test_hydra.py). This example generates a supervisor configuration file by composing independent hydra configs.
