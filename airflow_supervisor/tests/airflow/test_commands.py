from subprocess import check_call

from airflow_supervisor.airflow.commands import start_supervisor, stop_supervisor, write_supervisor_config
from airflow_supervisor.config import SupervisorAirflowConfiguration


def test_command():
    assert check_call(["_airflow_supervisor_command", "--help"]) == 0


def test_write(supervisor_airflow_configuration: SupervisorAirflowConfiguration):
    json = supervisor_airflow_configuration.model_dump_json()
    assert write_supervisor_config(json, _exit=False)
    assert supervisor_airflow_configuration._pydantic_path.read_text().strip() == json
    supervisor_airflow_configuration.rmdir()


def test_start_stop(supervisor_airflow_configuration: SupervisorAirflowConfiguration):
    json = supervisor_airflow_configuration.model_dump_json()
    assert write_supervisor_config(json, _exit=False)
    assert supervisor_airflow_configuration._pydantic_path.read_text().strip() == json
    assert start_supervisor(supervisor_airflow_configuration._pydantic_path, _exit=False)
    assert stop_supervisor(supervisor_airflow_configuration._pydantic_path, _exit=False)
    supervisor_airflow_configuration.rmdir()
