from pydantic import ValidationError
from pytest import raises

from airflow_supervisor import FcgiProgramConfiguration


def test_inst():
    with raises(ValidationError):
        FcgiProgramConfiguration()
    with raises(ValidationError):
        FcgiProgramConfiguration(socket="test")
    with raises(ValidationError):
        FcgiProgramConfiguration(command="test")
    FcgiProgramConfiguration(command="echo 'test'", socket="test")


def test_cfg():
    c = FcgiProgramConfiguration(command="echo 'test'", socket="test")
    assert c.to_cfg("name").strip() == "[fcgi-program:name]\ncommand=echo 'test'\nsocket=test"
