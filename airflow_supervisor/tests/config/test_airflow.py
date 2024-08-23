from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from airflow_supervisor import AirflowConfiguration, ProgramConfiguration, SupervisorAirflowConfiguration


def test_airflow_inst():
    with (
        patch("airflow_supervisor.config.supervisor.gettempdir") as p1,
        patch("airflow_supervisor.config.supervisor.datetime") as p2,
    ):
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        p2.now.return_value = datetime(2000, 1, 1, 0, 0, 0, 1, tzinfo=UTC)
        c = SupervisorAirflowConfiguration(
            airflow=AirflowConfiguration(port="*:9001"),
            program={
                "test": ProgramConfiguration(
                    command="sleep 1 && exit 1",
                )
            },
        )
        assert str(c.working_dir) == str(pth / "supervisor-2000-01-01T00:00:00")
        assert str(c.config_path) == str(pth / "supervisor-2000-01-01T00:00:00" / "supervisor.cfg")


def test_airflow_cfg_roundtrip_json():
    with (
        patch("airflow_supervisor.config.supervisor.gettempdir") as p1,
        patch("airflow_supervisor.config.supervisor.datetime") as p2,
    ):
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        p2.now.return_value = datetime(2000, 1, 1, 0, 0, 0, 1, tzinfo=UTC)
        c = SupervisorAirflowConfiguration(
            airflow=AirflowConfiguration(port="*:9001"),
            program={
                "test": ProgramConfiguration(
                    command="sleep 1 && exit 1",
                )
            },
        )
        assert c.model_validate_json(c.model_dump_json()) == c
