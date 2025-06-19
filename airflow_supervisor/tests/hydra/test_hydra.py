from getpass import getuser
from pathlib import Path
from unittest.mock import patch

from airflow_balancer.testing import pools
from airflow_config import load_config
from airflow_pydantic import SSHOperatorArgs

from airflow_supervisor import SupervisorSSHAirflowConfiguration


def test_hydra_config():
    with (
        patch("supervisor_pydantic.config.supervisor.gettempdir") as p1,
    ):
        with pools():
            pth = Path(__file__).resolve().parent.parent.parent.parent / ".pytest_cache"
            p1.return_value = str(pth)
            cfg = load_config("config", "config")
            assert "balancer" in cfg.extensions
            assert "supervisor" in cfg.extensions

            supervisor_cfg: SupervisorSSHAirflowConfiguration = cfg.extensions["supervisor"]

            # Basic Supervisor checks
            assert supervisor_cfg.command_prefix == ""
            assert supervisor_cfg.working_dir == pth / f"supervisor-{getuser()}-sleep-echo"
            assert supervisor_cfg.inet_http_server.port == "*:9001"
            assert supervisor_cfg.supervisorctl.serverurl == "http://localhost:9001/"

            assert "sleep" in supervisor_cfg.program
            assert "echo" in supervisor_cfg.program
            assert supervisor_cfg.program["sleep"].command == "sleep 1000"
            assert supervisor_cfg.program["echo"].command == 'echo "hello"'

            # SSH Operator checks
            ssh_args: SSHOperatorArgs = supervisor_cfg.ssh_operator_args
            assert ssh_args is not None
            assert ssh_args.cmd_timeout == 63
