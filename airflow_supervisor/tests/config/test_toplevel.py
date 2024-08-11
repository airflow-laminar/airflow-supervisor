from pydantic import ValidationError
from pytest import raises

from airflow_supervisor import ProgramConfiguration, SupervisorConfiguration


def test_config_instantiation():
    with raises(ValidationError):
        c = SupervisorConfiguration()
    c = SupervisorConfiguration(program={"test": ProgramConfiguration(command="echo 'hello'")})
    assert c
