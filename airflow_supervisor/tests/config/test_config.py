from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
from pytest import raises

from airflow_supervisor import (
    EventListenerConfiguration,
    FcgiProgramConfiguration,
    GroupConfiguration,
    IncludeConfiguration,
    InetHttpServerConfiguration,
    ProgramConfiguration,
    RpcInterfaceConfiguration,
    SupervisorConfiguration,
    SupervisorctlConfiguration,
    SupervisordConfiguration,
    UnixHttpServerConfiguration,
)
from airflow_supervisor.config import _generate_supervisor_config_path


def test_generate_supervisor_config_path():
    with patch("airflow_supervisor.config.gettempdir") as p1, patch("airflow_supervisor.config.datetime") as p2:
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        p2.now.return_value = datetime(2000, 1, 1, 0, 0, 0, 1, tzinfo=UTC)
        tmp = _generate_supervisor_config_path()
        assert str(tmp) == str(pth / "supervisor-2000-01-01T00:00:00")


def test_inst():
    with raises(ValidationError):
        SupervisorConfiguration()
    with patch("airflow_supervisor.config.gettempdir") as p1, patch("airflow_supervisor.config.datetime") as p2:
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        p2.now.return_value = datetime(2000, 1, 1, 0, 0, 0, 1, tzinfo=UTC)
        c = SupervisorConfiguration(program={"test": ProgramConfiguration(command="test")})
        assert str(c.path) == str(pth / "supervisor-2000-01-01T00:00:00")


def test_cfg():
    c = SupervisorConfiguration(program={"test": ProgramConfiguration(command="test")})
    assert c.to_cfg().strip() == "[program:test]\ncommand=test"


def test_cfg_all():
    c = SupervisorConfiguration(
        unix_http_server=UnixHttpServerConfiguration(
            file="/a/test/file",
            chmod="0777",
            chown="test",
            username="test",
            password="testpw",
        ),
        inet_http_server=InetHttpServerConfiguration(port="127.0.0.1:8000", username="test", password="testpw"),
        supervisord=SupervisordConfiguration(directory="/test"),
        supervisorctl=SupervisorctlConfiguration(username="test", password="testpw"),
        include=IncludeConfiguration(files=["a/test/file", "another/test/file"]),
        program={"test": ProgramConfiguration(command="test")},
        group={"testgroup": GroupConfiguration(programs=["test"])},
        fcgiprogram={"testfcgi": FcgiProgramConfiguration(command="echo 'test'", socket="test")},
        eventlistener={"testeventlistener": EventListenerConfiguration(command="echo 'test'")},
        rpcinterface={"testrpcinterface": RpcInterfaceConfiguration(supervisor_rpcinterface_factory="a.test.module")},
    )
    print(c.to_cfg().strip())
    assert (
        c.to_cfg().strip()
        == """[unix_http_server]
file=/a/test/file
chmod=0777
chown=test
username=test
password=testpw

[inet_http_server]
port=127.0.0.1:8000
username=test
password=testpw

[supervisord]
directory=/test

[supervisorctl]
username=test
password=testpw

[include]
files=a/test/file another/test/file

[program:test]
command=test

[group:testgroup]
programs=test

[fcgi-program:testfcgi]
command=echo 'test'
socket=test

[eventlistener:testeventlistener]
command=echo 'test'

[rpcinterface:testrpcinterface]
supervisor_rpcinterface_factory=a.test.module"""
    )
