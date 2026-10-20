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
