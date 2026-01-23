# Examples

This page provides comprehensive examples of using `airflow-supervisor` for various use cases.

## Basic Local Supervisor

The simplest example runs a supervisor instance on the same machine as the Airflow worker:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow_supervisor import (
    SupervisorAirflowConfiguration,
    Supervisor,
    ProgramConfiguration,
)

# Define the programs to supervise
cfg = SupervisorAirflowConfiguration(
    port=9001,
    working_dir="/data/supervisor/my-service",
    program={
        "my-app": ProgramConfiguration(
            command="python /app/server.py",
            stdout_logfile="/var/log/my-app/output.log",
            stderr_logfile="/var/log/my-app/error.log",
        ),
    },
)

with DAG(
    dag_id="basic-supervisor-dag",
    schedule=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=cfg)
```

## Multiple Programs

Supervise multiple programs within a single supervisor instance:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow_supervisor import (
    SupervisorAirflowConfiguration,
    Supervisor,
    ProgramConfiguration,
)

cfg = SupervisorAirflowConfiguration(
    port=9002,
    working_dir="/data/supervisor/multi-service",
    program={
        "web-server": ProgramConfiguration(
            command="gunicorn app:app --bind 0.0.0.0:8000",
            directory="/app/web",
        ),
        "celery-worker": ProgramConfiguration(
            command="celery -A tasks worker --loglevel=info",
            directory="/app/tasks",
        ),
        "redis": ProgramConfiguration(
            command="redis-server /etc/redis.conf",
        ),
    },
)

with DAG(
    dag_id="multi-program-supervisor",
    schedule=timedelta(hours=12),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=cfg)
```

## Remote Supervisor via SSH

Manage a supervisor instance on a remote machine using SSH:

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

cfg = SupervisorSSHAirflowConfiguration(
    port=9001,
    working_dir="/opt/services/my-app",
    program={
        "my-app": ProgramConfiguration(
            command="/opt/services/my-app/run.sh",
        ),
    },
    ssh_operator_args=SSHOperatorArgs(
        ssh_hook=SSHHook(
            remote_host="app-server.example.com",
            username="deploy",
            key_file="/home/airflow/.ssh/id_rsa",
        ),
        cmd_timeout=300,
    ),
    command_prefix="source /etc/profile &&",
)

with DAG(
    dag_id="remote-supervisor-dag",
    schedule=timedelta(hours=8),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    supervisor = SupervisorSSH(dag=dag, cfg=cfg)
```

## Always-On Service

Configure a service that stays running and doesn't stop when the DAG completes:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow_supervisor import (
    SupervisorAirflowConfiguration,
    Supervisor,
    ProgramConfiguration,
)

cfg = SupervisorAirflowConfiguration(
    port=9003,
    working_dir="/data/supervisor/always-on",
    program={
        "persistent-service": ProgramConfiguration(
            command="python /app/daemon.py",
        ),
    },
    # Don't stop the service when DAG completes
    stop_on_exit=False,
    cleanup=False,
    # Restart when DAG is re-triggered
    restart_on_initial=True,
    restart_on_retrigger=True,
)

with DAG(
    dag_id="always-on-supervisor",
    schedule=timedelta(hours=1),  # Check every hour
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=cfg)
```

## Time-Limited Job with Runtime

Run a job for a maximum duration:

```python
from airflow import DAG
from datetime import timedelta, datetime, time
from airflow_supervisor import (
    SupervisorAirflowConfiguration,
    Supervisor,
    ProgramConfiguration,
)

cfg = SupervisorAirflowConfiguration(
    port=9004,
    working_dir="/data/supervisor/batch-job",
    program={
        "batch-process": ProgramConfiguration(
            command="python /app/batch_processor.py",
        ),
    },
    # Run for maximum 4 hours
    runtime=timedelta(hours=4),
    # Or end at specific time
    endtime=time(18, 0),  # 6 PM
)

with DAG(
    dag_id="time-limited-supervisor",
    schedule="0 9 * * *",  # Start at 9 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=cfg)
```

## Using Airflow Pools

Control concurrency with Airflow pools:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow_supervisor import (
    SupervisorAirflowConfiguration,
    Supervisor,
    ProgramConfiguration,
)

cfg = SupervisorAirflowConfiguration(
    port=9005,
    working_dir="/data/supervisor/pooled-job",
    program={
        "resource-intensive": ProgramConfiguration(
            command="python /app/heavy_compute.py",
        ),
    },
    # Use specific Airflow pool
    pool="gpu-workers",
)

with DAG(
    dag_id="pooled-supervisor",
    schedule=timedelta(hours=2),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=cfg)
```

## Configuration-Driven with airflow-config

### Basic YAML Configuration

```yaml
# config/supervisor/web-service.yaml
_target_: airflow_config.Configuration

default_args:
  _target_: airflow_config.DefaultArgs
  retries: 0
  depends_on_past: false

all_dags:
  _target_: airflow_config.DagArgs
  start_date: "2024-01-01"
  catchup: false
  tags:
    - supervisor
    - production

extensions:
  supervisor:
    _target_: airflow_supervisor.SupervisorAirflowConfiguration
    port: 9091
    working_dir: "/data/supervisor/web-service"
    check_interval: 10  # seconds
    check_timeout: 28800  # 8 hours
    program:
      web-server:
        _target_: airflow_supervisor.ProgramConfiguration
        command: "gunicorn app:app --bind 0.0.0.0:8080"
        directory: "/app"
        stdout_logfile: "/var/log/web-server/output.log"
        stderr_logfile: "/var/log/web-server/error.log"
```

```python
# dags/web_service_supervisor.py
from datetime import timedelta
from airflow_config import load_config, DAG
from airflow_supervisor import Supervisor

config = load_config("config/supervisor", "web-service")

with DAG(
    dag_id="web-service-supervisor",
    schedule=timedelta(hours=12),
    config=config,
) as dag:
    supervisor = Supervisor(dag=dag, cfg=config.extensions["supervisor"])
```

### SSH with Host from airflow-balancer

When using [airflow-balancer](https://github.com/airflow-laminar/airflow-balancer) for dynamic host selection:

```yaml
# config/supervisor/distributed-service.yaml
_target_: airflow_config.Configuration

extensions:
  balancer:
    _target_: airflow_balancer.BalancerConfiguration
    hosts:
      - _target_: airflow_pydantic.Host
        name: "server-1.example.com"
        pool: "compute-pool"
      - _target_: airflow_pydantic.Host
        name: "server-2.example.com"
        pool: "compute-pool"

  supervisor:
    _target_: airflow_supervisor.SupervisorSSHAirflowConfiguration
    port: 9001
    working_dir: "/opt/services/distributed"
    program:
      worker:
        _target_: airflow_supervisor.ProgramConfiguration
        command: "python /opt/services/worker.py"
    ssh_operator_args:
      _target_: airflow_pydantic.SSHOperatorArgs
      cmd_timeout: 120

dags:
  distributed-supervisor:
    schedule: "0 */4 * * *"
    tasks:
      run-service:
        _target_: airflow_supervisor.SupervisorSSHTask
        task_id: run-service
        cfg: ${extensions.supervisor}
        host:
          _target_: airflow_pydantic.HostQuery
          balancer: ${extensions.balancer}
          kind: select
```

## Chaining with Other Tasks

Supervisor DAGs can be chained with other Airflow tasks:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow_supervisor import (
    SupervisorAirflowConfiguration,
    Supervisor,
    ProgramConfiguration,
)

def setup_environment():
    # Setup code here
    pass

def cleanup_environment():
    # Cleanup code here
    pass

cfg = SupervisorAirflowConfiguration(
    port=9006,
    working_dir="/data/supervisor/chained",
    program={
        "my-service": ProgramConfiguration(command="python service.py"),
    },
)

with DAG(
    dag_id="chained-supervisor",
    schedule=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    # Pre-supervisor setup
    setup = PythonOperator(
        task_id="setup",
        python_callable=setup_environment,
    )

    # Supervisor job
    supervisor = Supervisor(dag=dag, cfg=cfg)

    # Post-supervisor cleanup
    cleanup = PythonOperator(
        task_id="cleanup",
        python_callable=cleanup_environment,
    )

    # Chain the tasks
    setup >> supervisor >> cleanup
```

## Custom Check Intervals

Configure monitoring frequency for different use cases:

```python
from airflow import DAG
from datetime import timedelta, datetime
from airflow_supervisor import (
    SupervisorAirflowConfiguration,
    Supervisor,
    ProgramConfiguration,
)

# High-frequency monitoring for critical services
critical_cfg = SupervisorAirflowConfiguration(
    port=9007,
    working_dir="/data/supervisor/critical",
    program={
        "critical-service": ProgramConfiguration(command="python critical.py"),
    },
    check_interval=timedelta(seconds=2),  # Check every 2 seconds
    check_timeout=timedelta(hours=24),    # 24-hour timeout
)

# Low-frequency monitoring for batch jobs
batch_cfg = SupervisorAirflowConfiguration(
    port=9008,
    working_dir="/data/supervisor/batch",
    program={
        "batch-job": ProgramConfiguration(command="python batch.py"),
    },
    check_interval=timedelta(minutes=1),  # Check every minute
    check_timeout=timedelta(hours=8),     # 8-hour timeout
)

with DAG(
    dag_id="monitoring-examples",
    schedule=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    critical = Supervisor(dag=dag, cfg=critical_cfg)
    # Note: Typically you'd have separate DAGs for different services
```

## Integration Notes

### supervisor-pydantic

`airflow-supervisor` builds on [supervisor-pydantic](https://github.com/airflow-laminar/supervisor-pydantic), which provides:

- Pydantic models for all supervisor configuration sections
- XML-RPC client for supervisor communication
- Convenience utilities for supervisor management

### airflow-config

For YAML-driven DAG definitions, use [airflow-config](https://github.com/airflow-laminar/airflow-config):

- Hydra-based configuration management
- Per-environment overrides
- Integration with airflow-pydantic models

### airflow-ha

High availability features come from [airflow-ha](https://github.com/airflow-laminar/airflow-ha):

- Automatic retrigger on failure
- Runtime and endtime constraints
- Reference date handling

### airflow-balancer

For dynamic host selection, integrate with [airflow-balancer](https://github.com/airflow-laminar/airflow-balancer):

- Host pool management
- Dynamic host and port selection
- Load balancing across machines
