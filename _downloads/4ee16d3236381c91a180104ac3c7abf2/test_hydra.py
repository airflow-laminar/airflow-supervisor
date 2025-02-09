from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from airflow_supervisor import load_airflow_config


def test_hydra_config():
    with (
        patch("supervisor_pydantic.config.supervisor.gettempdir") as p1,
        patch("supervisor_pydantic.config.supervisor.datetime") as p2,
    ):
        pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
        p1.return_value = str(pth)
        p2.now.return_value = datetime(2000, 1, 1, 0, 0, 0, 1, tzinfo=UTC)

        cfg = load_airflow_config(
            "config", overrides=["+program=[sleep,echo]", "+rpcinterface=standard", "+inet_http_server=local"]
        )
        assert (
            cfg.to_cfg().strip()
            == """[inet_http_server]
port=*:9001

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
directory={dir}/sleep

[program:echo]
command=echo
autostart=false
startsecs=1
autorestart=false
exitcodes=0
stopsignal=TERM
stopwaitsecs=30
directory={dir}/echo

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface""".format(
                dir=str(pth / "supervisor-2000-01-01T00-00-00")
            )
        )
