---
myst:
  heading_anchors: 3
---

# How to forward program logs and check retained services

Forward a program's stdout and stderr into Airflow task logs during its lifecycle.
For services retained between DAG runs, use a separate scheduled health task to
check the existing supervisord instance and run Airflow's failure callbacks.

## Forward logs in an inline Python DAG

Complete the [local worker setup](how-to.md#how-to-run-a-local-job-in-python).
Save this DAG in the DAG folder, choosing a writable directory and unused port:

```python
import logging
from datetime import datetime, timezone

from airflow import DAG
from airflow_supervisor import ProgramConfiguration, Supervisor, SupervisorAirflowConfiguration


def report_failure(context):
    ti = context["task_instance"]
    failure = ti.xcom_pull(key="supervisor_failure", task_ids=ti.task_id)
    if failure is None:
        failure = ti.xcom_pull(key="supervisor_failure", task_ids=f"{ti.dag_id}-check-programs")
    logging.getLogger(__name__).error("Supervisor task %s failed: %s", ti.task_id, failure)


with DAG(
    dag_id="logged-supervisor",
    schedule=None,
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
) as dag:
    supervisor = Supervisor(
        dag=dag,
        on_failure_callback=report_failure,
        cfg=SupervisorAirflowConfiguration(
            working_dir="/var/tmp/logged-supervisor",
            port="127.0.0.1:9010",
            forward_logs=True,
            program={
                "batch": ProgramConfiguration(
                    command="/bin/sh -c 'echo batch-started; echo diagnostic >&2; sleep 2'",
                ),
            },
        ),
    )
```

Trigger `logged-supervisor`. Open its check task's log and look for lines like
`[supervisor batch:batch stdout] batch-started` and
`[supervisor batch:batch stderr] diagnostic`. Program output is also drained
around restart, stop, and cleanup, so inspect the relevant lifecycle task's log
when diagnosing those operations.

Replace `report_failure` with your existing alert callback or call your alert
transport from that function. Direct callbacks on `Supervisor` and
`SupervisorSSH` apply to their generated tasks. DAG `default_args` callbacks
also work. An alert runs when its Airflow task fails; a failed workload can first
take the configured retrigger path before an Airflow failure occurs.

## Forward logs with airflow-config

Install `airflow-config` in the DAG parsing environment. Create
`config/logged_supervisor.yaml` beside the loader:

```yaml
# @package _global_
_target_: airflow_config.Configuration

dags:
  logged-supervisor:
    schedule: null
    start_date: "2025-01-01"
    catchup: false
    tasks:
      run:
        _target_: airflow_supervisor.SupervisorTask
        cfg:
          working_dir: /var/tmp/logged-supervisor
          port: "127.0.0.1:9010"
          forward_logs: true
          program:
            batch:
              command: "/bin/sh -c 'echo batch-started; echo diagnostic >&2; sleep 2'"
```

Save `logged_supervisor.py` in the DAG folder:

```python
"""Generate Airflow DAGs from the logged supervisor configuration."""

from airflow_config import load_config

config = load_config("config", "logged_supervisor")
config.generate_in_mem()
```

Deploy either this loader or the inline DAG for that DAG ID. Run
`airflow tasks list logged-supervisor` to check discovery, then trigger the DAG
and inspect its task logs.

For SSH, enable the same `forward_logs` field on
`SupervisorSSHAirflowConfiguration` or on `SupervisorSSHTask.cfg`. Follow the
[SSH setup](how-to.md#how-to-run-a-job-over-ssh-in-python), including direct
worker access to the authenticated XML-RPC endpoint. Both execution modes read
program logs through XML-RPC; SSH handles the remote lifecycle commands.

## Schedule a health check between runs

First deploy a persistent service using the
[retained-service settings](how-to.md#how-to-keep-a-service-running-between-dag-runs).
Keep its endpoint and program names stable. A watchdog needs the same connection
and workload configuration, but never starts, stops, or removes that instance.

For an existing local instance with a program named `api` on port 9011, save this
DAG. Replace the connection, directory, and command with the retained service's
configuration, and connect `report_failure` to your alert transport:

```python
import logging
from datetime import datetime, timezone

from airflow import DAG
from airflow_pydantic.airflow import PythonOperator
from airflow_supervisor import ProgramConfiguration, SupervisorAirflowConfiguration, check_supervisor_health


def report_failure(context):
    ti = context["task_instance"]
    status = ti.xcom_pull(key="supervisor_process_status", task_ids=ti.task_id)
    logging.getLogger(__name__).error("Supervisor health task failed: %s; status=%s", context.get("exception"), status)


with DAG(
    dag_id="supervisor-watchdog",
    schedule="*/5 * * * *",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
) as dag:
    health = PythonOperator(
        task_id="health",
        python_callable=check_supervisor_health,
        on_failure_callback=report_failure,
        op_kwargs={
            "cfg": SupervisorAirflowConfiguration(
                working_dir="/var/tmp/retained-supervisor",
                port="127.0.0.1:9011",
                forward_logs=True,
                program={"api": ProgramConfiguration(command="/opt/services/api")},
            ),
        },
    )
```

By default, every workload must be `STARTING` or `RUNNING`. Empty, stopped,
failed, and unreachable instances fail the health task. For a finite job whose
successful completion is healthy, add `"require_running": False` to
`op_kwargs`; this accepts states allowed by the configured exit codes.

Use `host`, `port`, `username`, and `password` matching the remote XML-RPC
endpoint to monitor an SSH-managed instance. The watchdog only needs XML-RPC
access; it does not open an SSH session or reconfigure the manager.

## Define the watchdog in airflow-config

Create `config/supervisor_watchdog.yaml` beside the loader. Adapt `cfg` to the
existing instance:

```yaml
# @package _global_
_target_: airflow_config.Configuration
_convert_: all

dags:
  supervisor-watchdog:
    schedule: "*/5 * * * *"
    start_date: "2025-01-01"
    catchup: false
    max_active_runs: 1
    tasks:
      health:
        _target_: airflow_pydantic.PythonTask
        python_callable: airflow_supervisor.check_supervisor_health
        op_kwargs:
          cfg:
            working_dir: /var/tmp/retained-supervisor
            port: "127.0.0.1:9011"
            forward_logs: true
            program:
              api:
                command: /opt/services/api
```

Save `supervisor_watchdog.py` in the DAG folder:

```python
"""Generate Airflow DAGs for the supervisor watchdog."""

from airflow_config import load_config

config = load_config("config", "supervisor_watchdog")
config.generate_in_mem()
```

Use your existing Airflow failure callback configuration on the `health` task
or DAG `default_args`. To use the callback from the Python example, save its
function and `logging` import in an importable `alerts.py` module and add this
field to the `health` task:

```yaml
on_failure_callback: alerts.report_failure
```

The same field can be set on the active lifecycle's `run` task. Make the module
available in the DAG parsing and worker environments. For completed finite jobs, add
`require_running: false` alongside `cfg` under `op_kwargs`.

## Set read limits and inspect diagnostics

Log forwarding is opt-in: `forward_logs` defaults to `False`. Each poll reads
`log_chunk_size` bytes per program stream, defaulting to 65,536 bytes, with up to
three extra bytes to finish a UTF-8 character at the boundary. Set
it on `cfg` in Python or YAML; accepted values are 1 through 1,048,576. Final
drains read at most 16 chunks per stream and warn when they reach that bound.
Log read failures warn without changing an otherwise healthy task's result;
status and lifecycle failures still fail through their existing paths.

XCom stores cursors and compact process metadata, rather than log contents.
`supervisor_log_offsets` tracks stream positions. Watchdog runs reuse cursors
from earlier runs so a scheduled check can collect new output. If a log file
shrinks below its stored cursor, forwarding resets that cursor and warns.
XML-RPC does not identify file replacements; rotation to a file of the same
size or larger can go undetected and omit output. Forwarding does
not guarantee complete delivery after large output bursts or between checks;
retain Supervisor logs according to your operational needs.

Inspect `supervisor_process_status` for each program's name, group, state,
exit status, spawn error, and PID. `supervisor_failure` retains the last unhealthy
process snapshot even if a later poll reports recovery. Unreachable instances
may have no process snapshot; use the task exception in the failure callback.
Event listeners are excluded from workload completion and health checks.

Supervisord owns log capture between Airflow polls. Airflow forwarding runs
while a lifecycle task or scheduled watchdog executes. A five-minute watchdog
can miss a crash that recovers between checks; callbacks report Airflow task
failures rather than every Supervisor state transition.
