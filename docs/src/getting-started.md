# Getting Started

## Overview

`airflow-supervisor` provides **Apache Airflow operators and configuration** for running long-running or always-on jobs with [supervisord](http://supervisord.org). It builds on [supervisor-pydantic](https://github.com/airflow-laminar/supervisor-pydantic) for configuration management and is designed to work seamlessly with [airflow-config](https://github.com/airflow-laminar/airflow-config) for YAML-driven DAG definitions.

**Key Benefits:**

- **Long-Running Jobs**: Run services that need to stay up beyond Airflow's task execution model
- **Always-On Services**: Keep daemon processes running with automatic monitoring
- **Configuration-Driven**: Define supervisor configurations in YAML using airflow-config
- **High Availability**: Built on [airflow-ha](https://github.com/airflow-laminar/airflow-ha) for fault tolerance and retrigger capabilities
- **Remote Execution**: Support for both local and SSH-based supervisor management

> [!NOTE]
> This library builds on [supervisor-pydantic](https://github.com/airflow-laminar/supervisor-pydantic), which provides Pydantic configuration models for all supervisor structures. It is designed to work with [airflow-config](https://github.com/airflow-laminar/airflow-config) for YAML-driven DAG definitions.

## Installation

Install airflow-supervisor from PyPI:

```bash
pip install airflow-supervisor
```

For use with Apache Airflow 2.x:

```bash
pip install airflow-supervisor[airflow]
```

For use with Apache Airflow 3.x:

```bash
pip install airflow-supervisor[airflow3]
```

## Basic Usage

### Local Supervisor DAG

The simplest use case is running a supervisor instance on the Airflow worker node:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow_supervisor import SupervisorAirflowConfiguration, Supervisor, ProgramConfiguration

# Create supervisor configuration
cfg = SupervisorAirflowConfiguration(
    working_dir="/data/airflow/supervisor",
    config_path="/data/airflow/supervisor/supervisor.conf",
    program={
        "my-service": ProgramConfiguration(
            command="python my_service.py",
        )
    },
)

# Create DAG
with DAG(
    dag_id="my-supervisor-dag",
    schedule=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=cfg)
```

### Remote Supervisor via SSH

For managing supervisor on remote machines:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow_pydantic import SSHOperatorArgs
from airflow_supervisor import (
    SupervisorSSHAirflowConfiguration,
    SupervisorSSH,
    ProgramConfiguration,
)

# Create SSH-enabled supervisor configuration
cfg = SupervisorSSHAirflowConfiguration(
    port=9001,
    working_dir="/data/supervisor",
    program={
        "my-service": ProgramConfiguration(
            command="python my_service.py",
        )
    },
    ssh_operator_args=SSHOperatorArgs(
        ssh_hook=SSHHook(
            remote_host="my-server.example.com",
            username="airflow",
            key_file="/path/to/key",
        ),
    ),
)

with DAG(
    dag_id="remote-supervisor-dag",
    schedule=timedelta(hours=8),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    supervisor = SupervisorSSH(dag=dag, cfg=cfg)
```

## Configuration-Driven DAGs with airflow-config

The recommended approach is using [airflow-config](https://github.com/airflow-laminar/airflow-config) for fully declarative DAG definitions:

```yaml
# config/supervisor/my-service.yaml
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
    port: 9091
    working_dir: "/data/airflow/supervisor"
    program:
      my-service:
        _target_: airflow_supervisor.ProgramConfiguration
        command: "python my_service.py"
```

```python
# dags/my_supervisor_dag.py
from datetime import timedelta
from airflow_config import load_config, DAG
from airflow_supervisor import Supervisor

config = load_config("config/supervisor", "my-service")

with DAG(
    dag_id="my-supervisor-dag",
    schedule=timedelta(days=1),
    config=config,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=config.extensions["supervisor"])
```

## DAG Lifecycle

When you create a Supervisor DAG, it orchestrates the following lifecycle:

1. **Configure** - Write supervisord configuration file
2. **Start Supervisor** - Launch the supervisord daemon
3. **Start Programs** - Start supervised programs via supervisorctl
4. **Monitor** - Continuously check program status via XML-RPC API
5. **Handle Failures** - Restart programs on failure (via airflow-ha)
6. **Stop Programs** - Gracefully stop supervised programs
7. **Stop Supervisor** - Shut down the supervisord daemon
8. **Cleanup** - Remove configuration files

The DAG structure provides hooks at each step for custom actions.

## Configuration Options

### SupervisorAirflowConfiguration

Key configuration options for `SupervisorAirflowConfiguration`:

| Option | Type | Description |
|--------|------|-------------|
| `check_interval` | timedelta | Interval between program status checks (default: 5s) |
| `check_timeout` | timedelta | Timeout for status checks (default: 8 hours) |
| `runtime` | timedelta | Maximum runtime of the supervisor job |
| `endtime` | time | End time of the job |
| `stop_on_exit` | bool | Stop programs when DAG finishes (default: True) |
| `cleanup` | bool | Remove config files on completion (default: True) |
| `restart_on_retrigger` | bool | Restart programs on HA retrigger (default: False) |
| `pool` | str | Airflow pool for task scheduling |

### ProgramConfiguration

Supervisor program configuration (from supervisor-pydantic):

| Option | Type | Description |
|--------|------|-------------|
| `command` | str | The command to run |
| `autostart` | bool | Start automatically (default: False for Airflow) |
| `autorestart` | bool | Restart on exit (default: False) |
| `startsecs` | int | Seconds to consider started (default: 1) |
| `exitcodes` | list | Expected exit codes (default: [0]) |
| `stopsignal` | str | Signal to stop (default: TERM) |
| `stdout_logfile` | Path | Standard output log file |
| `stderr_logfile` | Path | Standard error log file |

## Next Steps

- See [Examples](examples.md) for more detailed use cases
- Consult the [API Reference](API.md) for complete API documentation
- Visit [supervisor-pydantic](https://airflow-laminar.github.io/supervisor-pydantic/) for supervisor configuration details
