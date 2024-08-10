from pydantic import ValidationError
from pytest import raises

from airflow_supervisor import ProgramConfiguration


def test_inst():
    with raises(ValidationError):
        ProgramConfiguration()
    ProgramConfiguration(command="echo 'test'")


def test_cfg():
    c = ProgramConfiguration(command="echo 'test'")
    assert c.to_cfg("name").strip() == "[program:name]\ncommand=echo 'test'"
