from getpass import getuser
from pathlib import Path
from unittest.mock import patch

from airflow_supervisor import AirflowConfiguration, ProgramConfiguration, SupervisorAirflowConfiguration


def test_airflow_inst():
    with (
        patch("supervisor_pydantic.config.supervisor.gettempdir") as p1,
    ):
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        c = SupervisorAirflowConfiguration(
            airflow=AirflowConfiguration(port="*:9001"),
            program={
                "test": ProgramConfiguration(
                    command="sleep 1 && exit 1",
                )
            },
        )
        assert str(c.working_dir) == str(pth / f"supervisor-{getuser()}-test")
        assert str(c.config_path) == str(pth / f"supervisor-{getuser()}-test" / "supervisor.cfg")


def test_airflow_cfg_roundtrip_json():
    with (
        patch("supervisor_pydantic.config.supervisor.gettempdir") as p1,
    ):
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        c = SupervisorAirflowConfiguration(
            airflow=AirflowConfiguration(port="*:9001"),
            program={
                "test": ProgramConfiguration(
                    command="sleep 1 && exit 1",
                )
            },
        )
        assert c.model_validate_json(c.model_dump_json()) == c
