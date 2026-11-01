from datetime import UTC, datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from airflow_supervisor import SupervisorViewerConfiguration, collect_supervisor_status

inventory = SupervisorViewerConfiguration(
    instances={
        name: {"cfg": {"host": "127.0.0.1", "port": f"*:{port}", "username": "demo", "password": "demo", "program": {}}}
        for name, port in [("host-a/primary", 19001), ("host-a/secondary", 19011), ("host-b/primary", 19021)]
    }
)

with DAG(
    dag_id="supervisor-observations",
    schedule="* * * * *",
    start_date=datetime(2025, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
) as dag:
    PythonOperator(task_id="collect", python_callable=collect_supervisor_status, op_kwargs={"cfg": inventory})
