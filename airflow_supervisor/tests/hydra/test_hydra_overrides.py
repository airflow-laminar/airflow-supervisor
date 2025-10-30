from getpass import getuser
from pathlib import Path
from unittest.mock import patch

import pytest

from airflow_supervisor import load_airflow_config, load_airflow_ssh_config

EXPECTED_CFG = """[inet_http_server]
port=*:9001
password=test

[supervisord]
logfile={dir}/supervisord.log
pidfile={dir}/supervisord.pid
nodaemon=false
directory={dir}
identifier=supervisor

[supervisorctl]
serverurl=http://localhost:9001/

[program:sleep]
command=sleep 1000
autostart=false
startsecs=1
autorestart=false
exitcodes=0
stopsignal=TERM
stopwaitsecs=30
stopasgroup=true
killasgroup=true
stdout_logfile={dir}/sleep/output.log
stderr_logfile={dir}/sleep/error.log
environment=HOME=/home/airflow,USER=airflow
directory={dir}/sleep

[program:echo]
command=echo "hello"
autostart=false
startsecs=1
autorestart=false
exitcodes=0
stopsignal=TERM
stopwaitsecs=30
stopasgroup=true
killasgroup=true
stdout_logfile={dir}/echo/output.log
stderr_logfile={dir}/echo/error.log
environment=HOME=/home/airflow,USER=airflow
directory={dir}/echo

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface"""


def test_hydra_overrides():
    with (
        patch("supervisor_pydantic.config.supervisor.gettempdir") as p1,
    ):
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        cfg = load_airflow_config(
            "config", overrides=["+program=[sleep,echo]", "+rpcinterface=standard", "+inet_http_server=local"]
        )
        assert cfg.to_cfg().strip() == EXPECTED_CFG.format(dir=str(pth / f"supervisor-{getuser()}-sleep-echo"))


def test_hydra_overrides_ssh():
    try:
        import airflow_supervisor.config.supervisor_ssh  # noqa: F401
    except ImportError:
        pytest.skip("airflow-balancer not available")
    with (
        patch("supervisor_pydantic.config.supervisor.gettempdir") as p1,
    ):
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        cfg = load_airflow_ssh_config(
            "config",
            "supervisor",
        )
        assert cfg.to_cfg().strip() == EXPECTED_CFG.format(dir=str(pth / f"supervisor-{getuser()}-sleep-echo"))
