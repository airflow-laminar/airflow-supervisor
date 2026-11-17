"""Generated task IDs follow the lifecycle task ID, which defaults to the DAG ID."""

from typing import Any, cast
from unittest.mock import patch

import pytest

pytest.importorskip("airflow")

from airflow.models.dag import DAG

from airflow_supervisor import (
    ProgramConfiguration,
    Supervisor,
    SupervisorAirflowConfiguration,
    SupervisorSSH,
    SupervisorSSHAirflowConfiguration,
    SupervisorTask,
    create_supervisor_control_dags,
)


@pytest.fixture
def cfg():
    with patch("supervisor_pydantic.config.supervisor.gettempdir", return_value="/tmp"):
        yield SupervisorAirflowConfiguration(
            port="*:9001", program={"test": ProgramConfiguration(command="echo hello")}
        )


@pytest.fixture
def ssh_cfg():
    with patch("supervisor_pydantic.config.supervisor.gettempdir", return_value="/tmp"):
        yield SupervisorSSHAirflowConfiguration(
            port="*:9001", program={"test": ProgramConfiguration(command="echo hello")}
        )


def test_lifecycle_without_task_id_keeps_dag_prefixed_ids(cfg):
    dag = DAG(dag_id="service", schedule=None)
    Supervisor(dag=dag, cfg=cfg)
    assert "service-check-programs" in dag.task_ids
    assert all(task_id.startswith("service-") for task_id in dag.task_ids)


def test_lifecycles_in_one_dag_are_named_by_their_task_ids(ssh_cfg):
    dag = DAG(dag_id="service", schedule=None)
    SupervisorSSH(dag=dag, cfg=ssh_cfg, task_id="service-a")
    SupervisorSSH(dag=dag, cfg=ssh_cfg.model_copy(deep=True), task_id="service-b")
    for instance in ("a", "b"):
        assert f"service-{instance}-check-programs" in dag.task_ids
        assert f"service-{instance}-configure-supervisor" in dag.task_ids
    assert not {task_id for task_id in dag.task_ids if task_id.startswith("service-check")}


def test_lifecycles_keep_the_dag_task_limit(ssh_cfg):
    dag = DAG(dag_id="service", schedule=None, max_active_tasks=8)
    SupervisorSSH(dag=dag, cfg=ssh_cfg, task_id="service-a")
    SupervisorSSH(dag=dag, cfg=ssh_cfg.model_copy(deep=True), task_id="service-b")
    assert dag.max_active_tasks == 8


def test_configured_tasks_pass_their_key_as_the_lifecycle_id(cfg):
    dag = DAG(dag_id="service", schedule=None)
    for name in ("service-a", "service-b"):
        SupervisorTask(task_id=name, cfg=cfg.model_copy(deep=True)).instantiate(dag=dag)
    assert {"service-a-check-programs", "service-b-check-programs"} <= set(dag.task_ids)


def test_program_lifecycles_scope_controls_to_their_task_ids(cfg):
    dag = DAG(dag_id="service", schedule=None)
    lifecycles = [
        Supervisor(dag=dag, cfg=cfg.model_copy(deep=True, update={"program_lifecycle": {}}), task_id=name)
        for name in ("service-a", "service-b")
    ]
    assert cast(Any, dag)._supervisor_lifecycles == lifecycles
    assert {"service-a-start-test", "service-b-start-test"} <= set(dag.task_ids)
    first, second = (supervisor._program_lifecycle for supervisor in lifecycles)
    assert first is not None and second is not None
    assert first._control_key("test") != second._control_key("test")
    controls = create_supervisor_control_dags(dag)
    assert {"service-a-restart-test", "service-b-restart-test", "service-a-force-kill", "service-b-force-kill"} <= set(
        controls
    )
