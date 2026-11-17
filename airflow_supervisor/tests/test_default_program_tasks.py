from typing import Any, cast

import pytest

pytest.importorskip("airflow")

from airflow.models.dag import DAG
from airflow_pydantic import PythonTask, WaitSensor

from airflow_supervisor import (
    Supervisor,
    SupervisorAirflowConfiguration,
    SupervisorSSH,
    SupervisorSSHAirflowConfiguration,
    create_supervisor_control_dags,
)


@pytest.mark.parametrize(
    "operator,config_type",
    [(Supervisor, SupervisorAirflowConfiguration), (SupervisorSSH, SupervisorSSHAirflowConfiguration)],
)
def test_default_program_tasks_expose_controls(tmp_path, operator, config_type):
    cfg = config_type(working_dir=tmp_path, program={"A": {"command": "sleep 1"}, "B": {"command": "sleep 1"}})
    dag = DAG(dag_id="main", schedule=None)
    supervisor = operator(dag=dag, cfg=cfg, task_id="service")
    assert set(supervisor.program_tasks) == {"A", "B"}
    assert {"service-start-A", "service-delay-A", "service-stop-A", "service-start-B"} <= set(dag.task_ids)
    controls = cast(Any, dag)._generated_dags
    assert {"service-start-A", "service-stop-A", "service-restart-A", "service-restart-B", "service-force-kill"} <= set(
        controls
    )
    assert all(type(control.timetable).__name__ == "NullTimetable" for control in controls.values())


def test_explicit_null_retains_grouped_lifecycle(tmp_path):
    cfg = SupervisorAirflowConfiguration(
        working_dir=tmp_path, program={"A": {"command": "sleep 1"}}, program_lifecycle=None
    )
    dag = DAG(dag_id="legacy", schedule=None)
    supervisor = Supervisor(dag=dag, cfg=cfg)
    assert supervisor.program_tasks == {}
    assert supervisor.restart_programs.task_id == "legacy-restart-programs"
    assert not getattr(dag, "_generated_dags", {})


def test_control_dags_follow_subtask_order_delays_and_retries(tmp_path):
    cfg = SupervisorAirflowConfiguration(working_dir=tmp_path, program={name: {"command": "sleep 1"} for name in "ABC"})
    dag = DAG(dag_id="main", schedule=None)
    supervisor = Supervisor(
        dag=dag,
        cfg=cfg,
        task_id="service",
        subtasks={
            "start-A": PythonTask(retries=2),
            "wait-after-A": WaitSensor(time_to_wait=600, dependencies=["start-A"]),
            "start-B": PythonTask(dependencies=["wait-after-A"], retries=3),
            "start-C": PythonTask(dependencies=["start-B"]),
            "stop-C": PythonTask(dependencies=["shutdown"]),
            "stop-B": PythonTask(dependencies=["stop-C"]),
            "stop-A": PythonTask(dependencies=["stop-B"]),
        },
    )
    controls = cast(Any, dag)._generated_dags
    start, stop, restart = (controls[f"service-{action}-programs"] for action in ("start", "stop", "restart"))
    assert start.get_task("start-B").upstream_task_ids == {"wait-after-A"}
    assert start.get_task("wait-after-A").upstream_task_ids == {"start-A"}
    assert start.get_task("wait-after-A").time_to_wait == 600
    assert start.get_task("start-B").retries == 3
    assert start.get_task("start-A").retries == 2
    assert stop.get_task("stop-A").upstream_task_ids == {"stop-B"}
    assert stop.get_task("stop-B").upstream_task_ids == {"stop-C"}
    assert {"stop-A", "stop-B", "stop-C"} <= restart.get_task("delay-A").upstream_task_ids
    assert supervisor.program_tasks["B"].start.upstream_task_ids == {"service-wait-after-A"}
    for control in controls.values():
        control.topological_sort()


@pytest.mark.parametrize("task_type", ["SupervisorTask", "SupervisorSSHTask"])
@pytest.mark.parametrize("generation", ["memory", "file"])
def test_yaml_generation_registers_ordered_program_controls(tmp_path, task_type, generation):
    from airflow_config import Configuration
    from airflow_pydantic.migration import _airflow_3

    automatic_controls = hasattr(Configuration, "_register_generated_dags")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "services.yaml").write_text(
        f"""# @package _global_
dags:
  ordered:
    schedule: null
    tasks:
      service:
        _target_: airflow_supervisor.{task_type}
        cfg:
          working_dir: {tmp_path / "service"}
          program:
            A: {{command: sleep 1}}
            B: {{command: sleep 1}}
            C: {{command: sleep 1}}
        subtasks:
          start-A:
            _target_: airflow_pydantic.PythonTask
            retries: 2
          wait-after-A:
            _target_: airflow_pydantic.WaitSensor
            time_to_wait: 600
            dependencies: [start-A]
          start-B:
            _target_: airflow_pydantic.PythonTask
            dependencies: [wait-after-A]
            retries: 3
          start-C:
            _target_: airflow_pydantic.PythonTask
            dependencies: [start-B]
          stop-C:
            _target_: airflow_pydantic.PythonTask
            dependencies: [shutdown]
          stop-B:
            _target_: airflow_pydantic.PythonTask
            dependencies: [stop-C]
          stop-A:
            _target_: airflow_pydantic.PythonTask
            dependencies: [stop-B]
"""
    )
    config = Configuration.load("config", "services", basepath=str(tmp_path))
    namespace: dict[str, Any] = {}
    if generation == "memory":
        namespace.update(config=config, directory=tmp_path)
        exec("config.generate_in_mem(directory)", namespace)  # noqa: S102
        main = namespace["ordered"]
        if not automatic_controls:
            namespace.update(create_supervisor_control_dags(main))
    else:
        config.generate(tmp_path, airflow_major_version=3 if _airflow_3() else 2)
        if not automatic_controls:
            path = tmp_path / "ordered.py"
            path.write_text(
                path.read_text()
                + "\nfrom airflow_supervisor import create_supervisor_control_dags\n"
                + "globals().update(create_supervisor_control_dags(dag))\n"
            )
        exec(compile((tmp_path / "ordered.py").read_text(), "ordered.py", "exec"), namespace)  # noqa: S102
        main = namespace["dag"]
    assert main.get_task("service-start-B").upstream_task_ids == {"service-wait-after-A"}
    assert main.get_task("service-stop-A").upstream_task_ids == {"service-stop-B"}
    assert namespace["service-restart-A"].get_task("restart")
    controls = namespace["service-start-programs"]
    assert controls.get_task("start-B").upstream_task_ids == {"wait-after-A"}
    assert controls.get_task("start-B").retries == 3
    assert namespace["service-start-A"].fileloc == main.fileloc
    assert sum(name.startswith("service-") and isinstance(value, DAG) for name, value in namespace.items()) == 13
    if generation == "file":
        from airflow.models.dagbag import DagBag

        bag = DagBag(collect_dags=False)
        bag.process_file(str(tmp_path / "ordered.py"), safe_mode=False)
        assert not bag.import_errors
        assert {
            "ordered",
            "service-start-A",
            "service-stop-B",
            "service-restart-C",
            "service-force-kill",
        } <= bag.dags.keys()
