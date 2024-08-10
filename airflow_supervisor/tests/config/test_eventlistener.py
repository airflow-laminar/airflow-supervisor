from pydantic import ValidationError
from pytest import raises

from airflow_supervisor import EventListenerConfiguration


def test_inst():
    with raises(ValidationError):
        EventListenerConfiguration()
    with raises(ValidationError):
        EventListenerConfiguration(stdout_capture_maxbytes=10)
    EventListenerConfiguration(command="echo 'test'")


def test_cfg():
    c = EventListenerConfiguration(command="echo 'test'")
    assert c.to_cfg("name").strip() == "[eventlistener:name]\ncommand=echo 'test'"
