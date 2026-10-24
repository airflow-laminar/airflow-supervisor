from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from hydra.utils import instantiate
from omegaconf import OmegaConf

from airflow_supervisor import Supervisor, SupervisorAirflowConfiguration, SupervisorSSHAirflowConfiguration


@pytest.mark.parametrize("config_type", [SupervisorAirflowConfiguration, SupervisorSSHAirflowConfiguration])
@pytest.mark.parametrize("via_hydra", [False, True])
@pytest.mark.parametrize(
    "preset,runtime,stop,cleanup,restart",
    [
        ("always_on", timedelta(days=7), False, False, True),
        ("daily", timedelta(days=1), True, True, False),
        ("half_day", timedelta(hours=12), True, False, False),
    ],
)
def test_preset_defaults_and_round_trip(tmp_path, config_type, via_hydra, preset, runtime, stop, cleanup, restart):
    data = {"preset": preset, "working_dir": str(tmp_path), "program": {"demo": {"command": "sleep 1"}}}
    cfg = (
        instantiate(OmegaConf.create({"_target_": f"airflow_supervisor.{config_type.__name__}", **data}))
        if via_hydra
        else config_type(**data)
    )
    assert cfg.runtime == runtime
    assert cfg.stop_on_exit is stop
    assert cfg.cleanup is cleanup
    assert cfg.restart_on_initial is restart
    assert cfg.restart_on_retrigger is False
    assert cfg.check_interval == timedelta(seconds=30)
    assert cfg.check_timeout == timedelta(hours=8)
    assert cfg.endtime == (time(20) if preset == "half_day" else None)
    assert cfg.maxretrigger == (10 if preset == "half_day" else None)
    assert config_type.model_validate_json(cfg.model_dump_json()) == cfg


def test_explicit_values_override_preset_without_mutating_input(tmp_path):
    data = {
        "preset": "always_on",
        "working_dir": tmp_path,
        "program": {"demo": {"command": "sleep 1"}},
        "runtime": None,
        "check_interval": 5,
        "restart_on_initial": False,
        "stop_on_exit": True,
        "cleanup": True,
    }
    original = data.copy()
    cfg = SupervisorAirflowConfiguration.model_validate(data)
    assert cfg.runtime is None
    assert cfg.check_interval == timedelta(seconds=5)
    assert cfg.restart_on_initial is False
    assert cfg.stop_on_exit is True and cfg.cleanup is True
    assert data == original


def test_unknown_preset_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="preset"):
        SupervisorAirflowConfiguration.model_validate(
            {"preset": "unknown", "working_dir": tmp_path, "program": {"demo": {"command": "sleep 1"}}}
        )


@pytest.mark.parametrize("preset", ["always_on", "daily", "half_day"])
def test_preset_controls_lifecycle_and_restart(tmp_path, has_airflow, preset):
    from airflow.providers.standard.operators.python import PythonOperator
    from airflow_pydantic import skip
    from airflow_pydantic.airflow import DAG

    cfg = SupervisorAirflowConfiguration(preset=preset, working_dir=tmp_path, program={"demo": {"command": "sleep 1"}})
    with DAG(dag_id="preset-check", schedule=None) as dag:
        supervisor = Supervisor(dag=dag, cfg=cfg)
    stop, cleanup = supervisor.stop_programs, supervisor.unconfigure_supervisor
    assert isinstance(stop, PythonOperator) and isinstance(cleanup, PythonOperator)
    assert (stop.python_callable is skip) is (preset == "always_on")
    assert (cleanup.python_callable is skip) is (preset != "daily")
    supervisor.check_programs._check_end_conditions = Mock(return_value=None)
    for retrigger in (0, 1):
        context = {"dag_run": SimpleNamespace(conf={f"{supervisor.check_programs.task_id}-retrigger": retrigger})}
        with patch("airflow_supervisor.airflow.local.start_programs", return_value=True) as start:
            supervisor.get_step_kwargs("start-programs")["python_callable"](**context)
        assert start.call_args.kwargs["restart"] is (preset == "always_on" and retrigger == 0)
