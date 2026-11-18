from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

pytest.importorskip("airflow")

from airflow.exceptions import AirflowSkipException
from airflow.models.dag import DAG
from airflow.models.taskinstance import TaskInstance
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.ti_deps.dep_context import DepContext
from airflow.ti_deps.deps.trigger_rule_dep import TriggerRuleDep
from airflow_pydantic import PythonTask
from airflow_pydantic.migration import _airflow_3

from airflow_supervisor import (
    Supervisor,
    SupervisorAirflowConfiguration,
    SupervisorSSH,
    SupervisorSSHAirflowConfiguration,
)


@pytest.fixture(
    params=[(Supervisor, SupervisorAirflowConfiguration), (SupervisorSSH, SupervisorSSHAirflowConfiguration)]
)
def controlled_dag(request, tmp_path):
    operator, config_type = request.param
    dag = DAG(dag_id="manual-controls", schedule=None)
    before, after = (EmptyOperator(task_id=name, dag=dag) for name in ("before", "after"))
    cfg = config_type(working_dir=tmp_path, program={"A": {"command": "sleep 1"}, "B": {"command": "sleep 1"}})
    lifecycle = operator(
        dag=dag,
        cfg=cfg,
        task_id="service",
        subtasks={"start-A": PythonTask(trigger_rule="all_done"), "stop-A": PythonTask(trigger_rule="all_done")},
    )
    before >> lifecycle >> after
    return dag, operator


def control_tasks(dag):
    return [task for task in dag.tasks if "-control-" in task.task_id or "-force-kill" in task.task_id]


def test_control_branches_are_disconnected_and_normally_skipped(controlled_dag):
    dag, operator = controlled_dag
    controls = control_tasks(dag)
    control_ids = {task.task_id for task in controls}
    guards = [task for task in controls if task.task_id.endswith((".trigger", "-force-kill-dag"))]
    assert len(guards) == 10
    for guard in guards:
        assert not guard.upstream_task_ids
        with pytest.raises(AirflowSkipException):
            guard.python_callable()
    for task in controls:
        assert task.upstream_task_ids | task.downstream_task_ids <= control_ids
        if task not in guards:
            assert task.trigger_rule == "all_success"
            assert len(task.upstream_task_ids & {guard.task_id for guard in guards}) == 1
    assert dag.get_task("service-start-A").trigger_rule == "all_done"
    assert dag.get_task("service-stop-A").trigger_rule == "all_done"
    assert isinstance(dag.get_task("service-force-kill"), SSHOperator if operator is SupervisorSSH else PythonOperator)
    assert not getattr(dag, "_generated_dags", {})
    dag.topological_sort()


def test_airflow_trigger_rules_require_the_selected_guard_to_succeed(controlled_dag):
    try:
        from airflow.serialization.serialized_objects import DagSerialization as Serializer
    except ImportError:
        from airflow.serialization.serialized_objects import SerializedDAG as Serializer

    dag, _ = controlled_dag
    serializer: Any = Serializer
    serialized = serializer.deserialize_dag(serializer.serialize_dag(dag))
    controls = control_tasks(dag)
    guards = {task.task_id for task in controls if task.task_id.endswith((".trigger", "-force-kill-dag"))}
    ti_kwargs: dict[str, Any] = {"dag_version_id": uuid4()} if _airflow_3() else {}
    for selected in (None, "service-control-start-A.trigger"):
        for task in controls:
            if task.task_id in guards:
                continue
            source = serialized.get_task(task.task_id)
            ti = TaskInstance(task=source, run_id="manual__controls", **ti_kwargs)
            finished = []
            for parent in task.upstream_task_ids:
                upstream = TaskInstance(
                    task=serialized.get_task(parent),
                    run_id="manual__controls",
                    state="skipped" if parent in guards and parent != selected else "success",
                    **ti_kwargs,
                )
                finished.append(upstream)
            with patch.object(ti, "get_dagrun", return_value=SimpleNamespace(dag_id=dag.dag_id, run_id=ti.run_id)):
                ready = TriggerRuleDep().is_met(ti=ti, session=Mock(), dep_context=DepContext(finished_tis=finished))
            assert ready is (selected in task.upstream_task_ids)
