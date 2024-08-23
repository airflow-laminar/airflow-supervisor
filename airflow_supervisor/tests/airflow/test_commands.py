from subprocess import check_call

from airflow_supervisor.config import SupervisorAirflowConfiguration


def test_command():
    assert check_call(["_airflow_supervisor_command", "--help"]) == 0


def test_write(supervisor_airflow_configuration: SupervisorAirflowConfiguration):
    json = supervisor_airflow_configuration.model_dump_json()
    assert check_call(["_airflow_supervisor_command", "configure-supervisor", json]) == 0
    assert supervisor_airflow_configuration.config_path.read_text().strip() == supervisor_airflow_configuration.to_cfg().strip()
