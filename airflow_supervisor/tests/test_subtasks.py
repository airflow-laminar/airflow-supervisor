from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from airflow_pydantic import PythonTask, SSHTask, WaitSensor
from hydra.utils import instantiate
from omegaconf import OmegaConf

from airflow_supervisor import (
    Supervisor,
    SupervisorAirflowConfiguration,
    SupervisorSSH,
    SupervisorSSHAirflowConfiguration,
    SupervisorSSHTask,
    SupervisorTask,
)


@pytest.mark.parametrize(
    "task_type,config_type",
    [(SupervisorTask, SupervisorAirflowConfiguration), (SupervisorSSHTask, SupervisorSSHAirflowConfiguration)],
)
def test_subtask_models_survive_serialization(tmp_path, task_type, config_type):
    task = task_type(
        task_id="service",
        cfg=config_type(working_dir=tmp_path, program={"A": {"command": "sleep 1"}}),
        subtasks={"start-A": PythonTask(retries=2), "wait": WaitSensor(time_to_wait=600)},
    )
    data = task.model_dump(exclude_unset=True)
    restored = task_type.model_validate_json(task.model_dump_json(exclude_unset=True))
    for value in (task_type.model_validate(data), restored):
        assert isinstance(value.subtasks["start-A"], PythonTask)
        assert isinstance(value.subtasks["wait"], WaitSensor)
        assert value.subtasks["start-A"].retries == 2
        assert value.subtasks["wait"].time_to_wait == 600
        assert "python_callable" not in value.subtasks["start-A"].model_fields_set


@pytest.mark.parametrize(
    "task_type,config_type",
    [(SupervisorTask, SupervisorAirflowConfiguration), (SupervisorSSHTask, SupervisorSSHAirflowConfiguration)],
)
def test_hydra_accepts_normal_task_models(tmp_path, task_type, config_type):
    task = instantiate(
        OmegaConf.create(
            {
                "_target_": f"airflow_supervisor.{task_type.__name__}",
                "task_id": "service",
                "cfg": {
                    "_target_": f"airflow_supervisor.{config_type.__name__}",
                    "working_dir": str(tmp_path),
                    "program": {"A": {"command": "sleep 1"}},
                },
                "subtasks": {"start-A": {"_target_": "airflow_pydantic.PythonTask", "retries": 3, "retry_delay": 15}},
            }
        )
    )
    assert isinstance(task.subtasks["start-A"], PythonTask)
    assert task.subtasks["start-A"].retry_delay == timedelta(seconds=15)


@pytest.fixture
def dag_type(has_airflow):
    from airflow.models.dag import DAG

    return DAG


@pytest.mark.parametrize(
    "operator,config_type",
    [(Supervisor, SupervisorAirflowConfiguration), (SupervisorSSH, SupervisorSSHAirflowConfiguration)],
)
def test_overrides_preserve_generated_actions_and_insert_delay(tmp_path, dag_type, operator, config_type):
    cfg = config_type(working_dir=tmp_path, program={name: {"command": "sleep 1"} for name in "ABC"})
    dag = dag_type(dag_id="overrides", schedule=None)
    lifecycle = operator(
        dag=dag,
        cfg=cfg,
        subtasks={
            "start-A": PythonTask(retries=2, retry_delay=15, task_display_name="Start A"),
            "wait-after-A": WaitSensor(time_to_wait=600, deferrable=True, dependencies=["start-A"]),
            "start-B": PythonTask(retries=3, dependencies=["wait-after-A"]),
            "start-C": PythonTask(dependencies=["start-B"]),
            "stop-B": PythonTask(dependencies=["check-programs.stop_pass"]),
            "stop-A": PythonTask(dependencies=["stop-B"]),
        },
    )
    start_a = lifecycle.program_tasks["A"].start
    assert start_a.retries == 2 and start_a.retry_delay == timedelta(seconds=15)
    assert start_a.task_display_name == "Start A"
    assert start_a.python_callable.func.__name__ == "start"
    assert lifecycle.program_tasks["B"].start.upstream_task_ids == {"overrides-wait-after-A"}
    assert dag.get_task("overrides-wait-after-A").upstream_task_ids == {"overrides-start-A"}
    assert lifecycle.program_tasks["A"].stop.upstream_task_ids == {"overrides-stop-B"}
    assert lifecycle.program_tasks["B"].stop.upstream_task_ids == {"overrides-check-programs-stop-pass"}
    assert cfg.program_lifecycle is None
    assert sum(task.task_id == "overrides-start-A" for task in dag.tasks) == 1
    dag.topological_sort()


def test_ssh_overrides_keep_generated_command_and_hook(tmp_path, dag_type):
    from airflow.providers.ssh.operators.ssh import SSHOperator

    cfg = SupervisorSSHAirflowConfiguration(working_dir=tmp_path, program={"A": {"command": "sleep 1"}})
    lifecycle = SupervisorSSH(
        dag=dag_type(dag_id="ssh-options", schedule=None),
        cfg=cfg,
        subtasks={"configure-supervisor": SSHTask(cmd_timeout=120, retries=2)},
    )
    configure = lifecycle.configure_supervisor
    assert isinstance(configure, SSHOperator)
    assert configure.cmd_timeout == 120 and configure.retries == 2
    assert "_supervisor_convenience configure-supervisor" in configure.command
    assert "program" in configure.command


def test_empty_dependencies_clear_only_selected_upstream_edges(tmp_path, dag_type):
    cfg = SupervisorAirflowConfiguration(working_dir=tmp_path, program={name: {"command": "sleep 1"} for name in "AB"})
    dag = dag_type(dag_id="clear-edges", schedule=None)
    lifecycle = Supervisor(dag=dag, cfg=cfg, subtasks={"start-A": PythonTask(dependencies=[])})
    assert not lifecycle.program_tasks["A"].start.upstream_task_ids
    assert "clear-edges-start-A" not in lifecycle.program_tasks["A"].delay.downstream_task_ids
    assert lifecycle.program_tasks["B"].start.upstream_task_ids == {"clear-edges-delay-B"}


def test_local_subtask_name_can_begin_with_dag_prefix(tmp_path, dag_type):
    cfg = SupervisorAirflowConfiguration(working_dir=tmp_path, program={"A": {"command": "sleep 1"}})
    lifecycle = Supervisor(
        dag=dag_type(dag_id="start", schedule=None), cfg=cfg, subtasks={"start-A": PythonTask(retries=2)}
    )
    assert lifecycle.program_tasks["A"].start.task_id == "start-start-A"
    assert lifecycle.program_tasks["A"].start.retries == 2


def test_explicit_shutdown_dependencies_can_replace_reverse_start_order(tmp_path, dag_type):
    cfg = SupervisorAirflowConfiguration(
        working_dir=tmp_path,
        program={name: {"command": "sleep 1"} for name in "AB"},
        program_lifecycle={"B": {"start_after": ["A"]}},
    )
    dag = dag_type(dag_id="independent-order", schedule=None)
    lifecycle = Supervisor(
        dag=dag,
        cfg=cfg,
        subtasks={
            "stop-A": PythonTask(dependencies=["shutdown"]),
            "stop-B": PythonTask(dependencies=["stop-A"]),
        },
    )
    assert lifecycle.program_tasks["A"].stop.upstream_task_ids == {"independent-order-shutdown"}
    assert lifecycle.program_tasks["B"].stop.upstream_task_ids == {"independent-order-stop-A"}
    dag.topological_sort()


def test_outer_dependencies_cover_added_roots_and_leaves(tmp_path, dag_type):
    from airflow.providers.standard.operators.empty import EmptyOperator

    dag = dag_type(dag_id="outer-edges", schedule=None)
    before, after = EmptyOperator(task_id="before", dag=dag), EmptyOperator(task_id="after", dag=dag)
    cfg = SupervisorAirflowConfiguration(working_dir=tmp_path, program={"A": {"command": "sleep 1"}})
    lifecycle = Supervisor(
        dag=dag,
        cfg=cfg,
        subtasks={
            "prepare": PythonTask(python_callable=str, dependencies=[]),
            "configure-supervisor": PythonTask(dependencies=["prepare"]),
            "notify": PythonTask(python_callable=str, dependencies=["unconfigure-supervisor"]),
        },
    )
    before >> lifecycle >> after
    assert "before" in dag.get_task("outer-edges-prepare").upstream_task_ids
    assert "outer-edges-notify" in after.upstream_task_ids
    dag.topological_sort()


@pytest.mark.parametrize(
    "subtasks,error",
    [
        ({"start-typo": PythonTask(retries=2)}, "Unknown generated subtask"),
        ({"start-A": PythonTask(dependencies=["typo"])}, "Unknown dependency"),
        (
            {"start-A": PythonTask(dependencies=["start-B"]), "start-B": PythonTask(dependencies=["start-A"])},
            "cyclic|cycle",
        ),
        ({"start-A": PythonTask(task_id="other")}, "cannot change its task ID"),
        ({"start-A": PythonTask(), "invalid-start-A": PythonTask()}, "Duplicate subtask override"),
    ],
)
def test_invalid_overrides_fail_during_construction(tmp_path, dag_type, subtasks, error):
    cfg = SupervisorAirflowConfiguration(working_dir=tmp_path, program={name: {"command": "sleep 1"} for name in "AB"})
    with pytest.raises(Exception, match=error):
        Supervisor(dag=dag_type(dag_id="invalid", schedule=None), cfg=cfg, subtasks=subtasks)


def test_incompatible_operator_type_is_rejected(tmp_path, dag_type):
    cfg = SupervisorAirflowConfiguration(working_dir=tmp_path, program={"A": {"command": "sleep 1"}})
    with pytest.raises(TypeError, match="incompatible"):
        Supervisor(dag=dag_type(dag_id="wrong-type", schedule=None), cfg=cfg, subtasks={"start-A": SSHTask(retries=2)})


@pytest.mark.parametrize(
    "task_type,config_type",
    [(SupervisorTask, SupervisorAirflowConfiguration), (SupervisorSSHTask, SupervisorSSHAirflowConfiguration)],
)
def test_config_instantiation_and_rendered_source(tmp_path, dag_type, task_type, config_type):
    from airflow_config import Configuration
    from airflow_pydantic.migration import _airflow_3

    cfg = config_type(working_dir=tmp_path, program={name: {"command": "sleep 1"} for name in "AB"})
    task = task_type(
        task_id="service",
        cfg=cfg,
        subtasks={
            "start-A": PythonTask(retries=2),
            "wait": WaitSensor(time_to_wait=600, dependencies=["start-A"]),
            "start-B": PythonTask(dependencies=["wait"]),
        },
    )
    config = Configuration(dags={"render-subtasks": {"dag_id": "render-subtasks", "tasks": {"service": task}}})
    model = config.dags["render-subtasks"]
    source = model.render(airflow_major_version=3 if _airflow_3() else 2)
    namespace = {}
    exec(compile(source, "subtasks.py", "exec"), namespace)  # noqa: S102
    for dag in (model.instantiate(), namespace["dag"]):
        assert dag.get_task("render-subtasks-start-A").retries == 2
        assert dag.get_task("render-subtasks-start-B").upstream_task_ids == {"render-subtasks-wait"}


def test_dependency_overrides_do_not_stop_programs_during_retrigger(tmp_path, dag_type):
    from airflow.exceptions import AirflowSkipException
    from airflow_ha import Action, Result

    cfg = SupervisorAirflowConfiguration(working_dir=tmp_path, program={"A": {"command": "sleep 1"}})
    lifecycle = Supervisor(
        dag=dag_type(dag_id="safe-stop", schedule=None),
        cfg=cfg,
        subtasks={"stop-A": PythonTask(dependencies=["check-programs"])},
    )
    assert lifecycle._program_lifecycle is not None
    monitor = lifecycle.check_programs
    monitor._check_end_conditions = Mock(return_value=None)
    ti = Mock(xcom_pull=Mock(return_value=(Result.PASS, Action.RETRIGGER)))
    context = {"ti": ti, "dag_run": SimpleNamespace(conf={}, start_date=datetime.now(UTC)), "params": {}}
    with (
        patch.object(lifecycle.supervisor_client, "stopProcess") as stop,
        patch("airflow_supervisor.airflow.local.stop_supervisor") as daemon,
    ):
        with pytest.raises(AirflowSkipException):
            lifecycle._program_lifecycle._stop("A", **context)
        with pytest.raises(AirflowSkipException):
            lifecycle._run_step("stop-supervisor", context)
        stop.assert_not_called()
        daemon.assert_not_called()
