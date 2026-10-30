---
myst:
  heading_anchors: 3
---

# How-to guides

Run jobs on an Airflow worker or a remote SSH host, with configuration in Python
or `airflow-config` YAML.

| Execution    | Inline Python                                          | `airflow-config`                                               |
| ------------ | ------------------------------------------------------ | -------------------------------------------------------------- |
| Local worker | [Local Python DAG](#how-to-run-a-local-job-in-python)  | [Local YAML DAG](#how-to-run-a-local-job-with-airflow-config)  |
| SSH host     | [SSH Python DAG](#how-to-run-a-job-over-ssh-in-python) | [SSH YAML DAG](#how-to-run-a-job-over-ssh-with-airflow-config) |

## How to run a local job in Python

Install `airflow-supervisor[airflow]` and `supervisor` in your Airflow 2
environment. Use `airflow-supervisor[airflow3]` for Airflow 3.

Run every lifecycle task on the same host, with access to the same working
directory and supervisord endpoint. Use a single worker host or route this DAG
to a queue served by that host. Shared storage alone does not make a local
supervisord instance available on another worker.

Save this DAG in your DAG folder. Replace `/bin/sleep 5` with your job's command,
and choose a writable working directory and an unused port:

```python
from datetime import datetime, timezone

from airflow import DAG
from airflow_supervisor import ProgramConfiguration, Supervisor, SupervisorAirflowConfiguration

with DAG(
    dag_id="local-supervisor",
    schedule="@daily",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
) as dag:
    supervisor = Supervisor(
        dag=dag,
        cfg=SupervisorAirflowConfiguration(
            working_dir="/var/tmp/local-supervisor",
            port="127.0.0.1:9001",
            program={"batch": ProgramConfiguration(command="/bin/sleep 5")},
        ),
    )
```

Keep `Supervisor` construction inside the DAG context. Run
`airflow tasks list local-supervisor` to confirm that Airflow loaded its lifecycle
tasks, then trigger `local-supervisor`.

## How to run a local job with airflow-config

Use the same worker placement and package setup as the
[local Python guide](#how-to-run-a-local-job-in-python), and install
`airflow-config` in the DAG parsing environment.

Create `config/local_supervisor.yaml` beside your DAG loader:

```yaml
# @package _global_
_target_: airflow_config.Configuration

dags:
  local-supervisor:
    schedule: "@daily"
    start_date: "2025-01-01"
    catchup: false
    tasks:
      run:
        _target_: airflow_supervisor.SupervisorTask
        cfg:
          working_dir: /var/tmp/local-supervisor
          port: "127.0.0.1:9001"
          program:
            batch:
              command: /bin/sleep 5
```

Save `local_supervisor.py` in the DAG folder:

```python
"""Generate Airflow DAGs from the local supervisor configuration."""

from airflow_config import load_config

config = load_config("config", "local_supervisor")
config.generate_in_mem()
```

Run `airflow tasks list local-supervisor`, then trigger `local-supervisor`.
Deploy either this loader or the inline Python DAG for that DAG ID.

## How to run a job over SSH in Python

Install `airflow-supervisor[airflow]` in Airflow 2, or
`airflow-supervisor[airflow3]` in Airflow 3. These extras include the SSH provider.
On the remote host, install `supervisor-pydantic` and `supervisor`:

```bash
pip install supervisor-pydantic supervisor
```

Create an Airflow SSH connection named `supervisor-host` for `jobs.example.com`.
Its account needs permission to run the job and write the remote working
directory. Ensure `supervisord` and `_supervisor_convenience` are on the remote
non-interactive shell's `PATH`. For a remote virtual environment, set
`command_prefix` to its activation command, such as
`source /opt/supervisor-venv/bin/activate`.

Allow Airflow workers to reach the remote supervisord HTTP/XML-RPC endpoint on
port 9001. Restrict access to those workers. Set `SUPERVISOR_RPC_PASSWORD` in the
DAG parsing environment and worker environments. This password authenticates
XML-RPC requests separately from the SSH connection.

Save this DAG, replacing the host, working directory, and command:

```python
import os
from datetime import datetime, timezone

from airflow import DAG
from airflow_pydantic import SSHOperatorArgs
from airflow_supervisor import ProgramConfiguration, SupervisorSSH, SupervisorSSHAirflowConfiguration

with DAG(
    dag_id="ssh-supervisor",
    schedule="@daily",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
) as dag:
    supervisor = SupervisorSSH(
        dag=dag,
        cfg=SupervisorSSHAirflowConfiguration(
            working_dir="/var/tmp/ssh-supervisor",
            host="jobs.example.com",
            port="*:9001",
            username="airflow",
            password=os.environ["SUPERVISOR_RPC_PASSWORD"],
            ssh_operator_args=SSHOperatorArgs(ssh_conn_id="supervisor-host"),
            program={"batch": ProgramConfiguration(command="/bin/sleep 5")},
        ),
    )
```

Set `cfg.host` to the XML-RPC hostname and the SSH connection's host to the same
machine. `cfg.port` is the supervisord listen address, not the SSH port.
Run `airflow tasks list ssh-supervisor`, then trigger `ssh-supervisor`.

## How to run a job over SSH with airflow-config

Complete the remote package, SSH connection, XML-RPC network, and password
setup from the [SSH Python guide](#how-to-run-a-job-over-ssh-in-python).
Install `airflow-config` in the DAG parsing environment.

Create `config/ssh_supervisor.yaml` beside your DAG loader:

```yaml
# @package _global_
_target_: airflow_config.Configuration

dags:
  ssh-supervisor:
    schedule: "@daily"
    start_date: "2025-01-01"
    catchup: false
    tasks:
      run:
        _target_: airflow_supervisor.SupervisorSSHTask
        cfg:
          working_dir: /var/tmp/ssh-supervisor
          host: jobs.example.com
          port: "*:9001"
          username: airflow
          password: ${oc.env:SUPERVISOR_RPC_PASSWORD}
          ssh_operator_args:
            ssh_conn_id: supervisor-host
          program:
            batch:
              command: /bin/sleep 5
```

If the remote tools are in a virtual environment, add
`command_prefix: source /opt/supervisor-venv/bin/activate` under `cfg`.

Save `ssh_supervisor.py` in the DAG folder:

```python
"""Generate Airflow DAGs from the SSH supervisor configuration."""

from airflow_config import load_config

config = load_config("config", "ssh_supervisor")
config.generate_in_mem()
```

Run `airflow tasks list ssh-supervisor`, then trigger `ssh-supervisor`.
Deploy either this loader or the inline Python DAG for that DAG ID.

## How to limit monitoring

Set the polling interval, sensor timeout, and workload end condition under `cfg`
in either local or SSH YAML configuration:

```yaml
check_interval: 00:00:10
check_timeout: 08:00:00
runtime: 04:00:00
maxretrigger: 3
```

In Python, set `check_interval=timedelta(seconds=10)`,
`check_timeout=timedelta(hours=8)`, `runtime=timedelta(hours=4)`, and
`maxretrigger=3` on the configuration model, importing `timedelta` from
`datetime`. Use `check_timeout` for the sensor's time limit and `runtime` or
`endtime` to end monitoring through the lifecycle's stop branch. See the
[timing reference](api.md#monitoring-and-lifecycle-fields) for defaults and
reference dates.

## How to choose lifecycle defaults

Use a preset when several jobs need the same monitoring and cleanup settings:

```python
from airflow_supervisor import SupervisorAirflowConfiguration

cfg = SupervisorAirflowConfiguration(
    preset="always_on",
    working_dir="/var/tmp/service",
    program={"service": {"command": "/opt/service/bin/run"}},
)
```

`always_on` retains the service and its directory after a seven-day monitoring
window. Use `daily` for a one-day window that stops and cleans up on success, or
`half_day` for a 12-hour window ending by 20:00 that stops the service but keeps
its files. These windows are relative to the configured reference date.

For an `airflow-config` configuration, set the same field in the Supervisor model:

```yaml
_target_: airflow_supervisor.SupervisorAirflowConfiguration
preset: half_day
working_dir: /var/tmp/report
program:
  report:
    command: /opt/report/bin/run
check_interval: 15
```

Explicit settings override preset values. Both local and
`SupervisorSSHAirflowConfiguration` models accept presets. Refer to the
[preset reference](api.md#monitoring-and-lifecycle-fields) for restart flags,
timeouts, and cleanup settings; choose the DAG schedule separately.

## How to keep a service running between DAG runs

Set these fields on either configuration model, or under `cfg` in YAML:

```yaml
stop_on_exit: false
cleanup: false
restart_on_initial: true
restart_on_retrigger: true
runtime: 04:00:00
```

Use the same working directory and endpoint on each run. Set `runtime` or
`endtime` to end monitoring while the service remains active. A running service
with no end condition continues to occupy the monitoring task until its sensor
timeout. See the [timing reference](api.md#monitoring-and-lifecycle-fields) for
the reference date used to calculate those limits.

## How to select a host with airflow-balancer

Pass a selected `airflow-pydantic` `Host` or a `HostQuery` of kind `select` as
`SupervisorSSHTask.host`, outside `cfg`. Pass a `Port` or `PortQuery` as the
task's `port` to select the XML-RPC port. In inline Python, pass resolved `Host`
and `Port` objects to `SupervisorSSH`.

Keep the program configuration under `cfg`. If the selected host defines a pool
and `cfg.pool` is unset, its pool is assigned to the lifecycle tasks.

## How to chain the lifecycle with other tasks

In Python, connect existing Airflow tasks to the `Supervisor` or `SupervisorSSH`
object:

```python
prepare >> supervisor >> publish
```

In `airflow-config`, use the supervisor task's mapping key in dependencies:

```yaml
tasks:
  prepare:
    _target_: airflow_pydantic.BashTask
    bash_command: echo prepare
  run:
    _target_: airflow_supervisor.SupervisorTask
    dependencies: [prepare]
    cfg:
      working_dir: /var/tmp/chained-supervisor
      port: "127.0.0.1:9001"
      program:
        batch:
          command: /bin/sleep 5
  publish:
    _target_: airflow_pydantic.BashTask
    bash_command: echo publish
    dependencies: [run]
```

Upstream tasks precede configuration; downstream tasks follow unconfiguration.
Keep stop and cleanup enabled if downstream tasks should run with the default
`all_success` trigger rule. Disabling cleanup creates a skipped boundary task.

## How to order programs and tolerate an optional program's failure

Set `program_lifecycle` to create separate start, delay, and stop tasks. This
example starts A, waits ten minutes from A's process start, starts B, then C.
Shutdown follows C, B, A. C is disabled for the monitoring chain after three
consecutive failures; A and B keep running across recovery retriggers.

```python
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow_supervisor import Supervisor, SupervisorAirflowConfiguration, create_supervisor_control_dags

with DAG(
    dag_id="ordered-services",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
) as dag:
    service = Supervisor(
        dag=dag,
        cfg=SupervisorAirflowConfiguration(
            working_dir="/tmp/ordered-services",
            runtime=timedelta(hours=8),
            reference_date="start_date",
            program={
                "A": {"command": "/opt/services/a"},
                "B": {"command": "/opt/services/b"},
                "C": {"command": "/opt/services/c"},
            },
            program_lifecycle={
                "A": {},
                "B": {"start_after": ["A"], "start_delay": timedelta(minutes=10)},
                "C": {
                    "start_after": ["B"],
                    "required": False,
                    "max_consecutive_failures": 3,
                    "retries": 2,
                    "retry_delay": timedelta(seconds=30),
                },
            },
        ),
    )

globals().update(create_supervisor_control_dags(service))
```

The delay uses a rescheduling sensor, releasing its worker slot between checks.
An already-running B proceeds without repeating the delay on every retrigger.
Configure `restart_on_initial` or `restart_on_retrigger` only when those restarts
are intended; the defaults leave healthy programs running.

Airflow retries a failed start command twice in this example. If the final attempt
still fails, C consumes one failure from its program budget. Monitoring also counts
an observed process failure once until another start attempt. A healthy observation
resets the consecutive failure count. A fresh scheduled or manual run starts a new
budget; HA retriggers inherit it. An optional program's failure does not select the
DAG failure branch. Required program failures retain the failed retrigger path.

To use SSH, replace `Supervisor` and `SupervisorAirflowConfiguration` with
`SupervisorSSH` and `SupervisorSSHAirflowConfiguration`, adding the SSH settings from
the [SSH guide](#how-to-run-a-job-over-ssh-in-python). Program operations still use
XML-RPC, so workers need access to that endpoint.

For `airflow-config`, put the same policy under the task's `cfg`:

```yaml
dags:
  ordered-services:
    tasks:
      run:
        _target_: airflow_supervisor.SupervisorTask
        cfg:
          _target_: airflow_supervisor.SupervisorAirflowConfiguration
          working_dir: /tmp/ordered-services
          runtime: 28800
          reference_date: start_date
          program:
            A: {command: /opt/services/a}
            B: {command: /opt/services/b}
            C: {command: /opt/services/c}
          program_lifecycle:
            A: {}
            B: {start_after: [A], start_delay: 600}
            C:
              start_after: [B]
              required: false
              max_consecutive_failures: 3
              retries: 2
              retry_delay: 30
```

Use `SupervisorSSHTask` and `SupervisorSSHAirflowConfiguration` for SSH. After
generating the configured DAGs in memory, register controls from the native DAG:

```python
from airflow_config import load_config
from airflow_supervisor import create_supervisor_control_dags

load_config("config", "ordered_services").generate_in_mem()
globals().update(create_supervisor_control_dags(globals()["ordered-services"]))
```

## How to control a program independently

The registration above exports unscheduled `ordered-services-start-C`,
`ordered-services-stop-C`, and `ordered-services-restart-C` DAGs, with equivalent
controls for A and B. Aggregate `start-programs`, `stop-programs`, `restart-programs`,
and `force-kill` DAGs are also exported. Aggregate restart stops programs in shutdown
order, then starts them in startup order with the configured delays.

A stop control suspends that program through an Airflow Variable, so monitoring
does not immediately recover it. Start and restart controls re-enable it and reset
its failure budget. The stop intent persists across fresh runs until explicitly
re-enabled. Trigger one control operation at a time for a lifecycle; separate
control DAGs do not provide a transaction or distributed lock around remote actions.
The daemon must already exist for program controls. Force kill terminates the
daemon and remains an emergency operation, not an orderly shutdown.

To compose a control with other Airflow tasks, create it in another DAG:

```python
with DAG(dag_id="maintenance", schedule=None) as maintenance:
    stop_b = service.program_operator("B", "stop", dag=maintenance)
    restart_a = service.program_operator("A", "restart", dag=maintenance, retries=2)
    stop_b >> restart_a
```

Program stdout and stderr are forwarded by default during operations and
monitoring. Inspect the relevant task log; set `forward_logs=False` to opt out.
