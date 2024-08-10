from pydantic import ValidationError
from pytest import raises

from airflow_supervisor import GroupConfiguration


def test_inst():
    with raises(ValidationError):
        GroupConfiguration()
    GroupConfiguration(programs=["test"])


def test_cfg():
    c = GroupConfiguration(programs=["test"])
    assert c.to_cfg("name").strip() == "[group:name]\nprograms=test"
