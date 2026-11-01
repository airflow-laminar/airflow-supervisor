---
myst:
  heading_anchors: 3
---

# How to view existing Supervisor instances in Airflow

Install `airflow-supervisor` in the collection workers and the Airflow webserver
or API server. Restart the server to load the **Supervisor Viewer** plugin.
Workers need XML-RPC access to each instance; page requests read stored snapshots.

## Configure a collection DAG in Python

Give each instance a stable key, including separate keys for instances on the
same host. Reuse the configuration from a local `Supervisor` or remote
`SupervisorSSH` lifecycle. For instances managed elsewhere, provide connection
settings and `program={}`; collection reads all supervised processes, including
event listeners.

```python
from datetime import datetime, timezone

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow_supervisor import SupervisorViewerConfiguration, collect_supervisor_status

inventory = SupervisorViewerConfiguration(
    instances={
        "worker-a/main": {"cfg": local_cfg},
        "worker-a/secondary": {"cfg": secondary_cfg},
        "worker-b/main": {"cfg": ssh_cfg},
    },
)

with DAG(
    dag_id="supervisor-observations",
    schedule="* * * * *",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
) as dag:
    PythonOperator(
        task_id="collect",
        python_callable=collect_supervisor_status,
        op_kwargs={"cfg": inventory.model_dump(mode="json")},
    )
```

For local lifecycles, set `cfg.host` to an address reachable from the collector
worker. A loopback address identifies the collector's host. SSH lifecycle daemon
commands still use SSH; this collector uses the same XML-RPC endpoint as program
monitoring and performs no SSH operations.

Run only one collection DAG per snapshot key. Use `max_active_runs=1` to prevent
its runs from overwriting each other concurrently.

## Configure collection with airflow-config

Start with
[`examples/supervisor_viewer/config/instances.yaml`](https://github.com/airflow-laminar/airflow-supervisor/blob/main/examples/supervisor_viewer/config/instances.yaml).
Replace its disposable endpoint settings with your instance configurations.
The collection task is an ordinary `PythonTask`:

```yaml
collect:
  _target_: airflow_pydantic.PythonTask
  python_callable: airflow_supervisor.collect_supervisor_status
  op_kwargs:
    cfg: ${extensions.supervisor_viewer}
```

Load the configuration through the usual `airflow-config` loader and register
its DAGs. Inline and YAML definitions use the same collector and snapshot.

## Link to workload runs and logs

Set `run_url` and `log_url` on an instance when its Airflow association is known:

```python
inventory.instances["worker-b/main"].run_url = existing_run_url
inventory.instances["worker-b/main"].log_url = task_instance.log_url
```

Use URLs from the Airflow installation managing that workload. Airflow 2 uses
grid query parameters; Airflow 3 uses run/task paths. The viewer preserves these
URLs and does not guess a run or select the latest run automatically. Update
them when the associated run changes. Missing associations display
`No Airflow links configured`.

Enable log forwarding on the workload lifecycle or run a
[retained-service health task](observability.md). Link to that task's log.
The status collector does not copy process logs into its own task log. Native
Supervisor logs remain available through the existing Supervisor/Multivisor
interfaces; their control endpoints are separate from the Airflow viewer.

## Change the snapshot key

Set `variable_key` on `SupervisorViewerConfiguration` and set
`AIRFLOW_SUPERVISOR_SNAPSHOT_KEY` to the same value on the Airflow webserver or
API server. Restart the server after changing its environment.

Open `/airflow-supervisor/` using an Airflow account with website-view access.
The page shows the configured snapshot as one operations view; Airflow enforces
its normal DAG permissions when a run/log link is opened. Set a collection
interval shorter than `max_age` so delayed or stopped collection becomes visible
as `STALE`.
