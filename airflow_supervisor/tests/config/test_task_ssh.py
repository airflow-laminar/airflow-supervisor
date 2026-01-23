"""Tests for SupervisorSSHTask and SupervisorSSHTaskArgs configurations."""

from unittest.mock import patch

import pytest
from airflow_pydantic import Host, Port, SSHOperatorArgs

from airflow_supervisor import ProgramConfiguration
from airflow_supervisor.config import (
    SupervisorSSHAirflowConfiguration,
    SupervisorSSHOperator,
    SupervisorSSHOperatorArgs,
    SupervisorSSHTask,
    SupervisorSSHTaskArgs,
)


@pytest.fixture
def ssh_config():
    """Create an SSH configuration fixture."""
    with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
        p1.return_value = "/tmp"
        try:
            from airflow.providers.ssh.hooks.ssh import SSHHook

            cfg = SupervisorSSHAirflowConfiguration(
                port=9001,
                program={
                    "test": ProgramConfiguration(command="echo hello"),
                },
                ssh_operator_args=SSHOperatorArgs(
                    ssh_hook=SSHHook(remote_host="localhost"),
                ),
            )
            yield cfg
        except ImportError:
            pytest.skip("SSHHook not available")


class TestSupervisorSSHTaskArgs:
    def test_supervisor_ssh_task_args_instantiation(self, ssh_config):
        """Test basic SupervisorSSHTaskArgs instantiation."""
        args = SupervisorSSHTaskArgs(cfg=ssh_config)
        assert args.cfg == ssh_config

    def test_supervisor_ssh_operator_args_alias(self):
        """Test SupervisorSSHOperatorArgs is an alias for SupervisorSSHTaskArgs."""
        assert SupervisorSSHOperatorArgs is SupervisorSSHTaskArgs

    def test_supervisor_ssh_task_args_with_host(self, ssh_config):
        """Test SupervisorSSHTaskArgs with Host."""
        host = Host(name="test-host", pool="test-pool")
        args = SupervisorSSHTaskArgs(cfg=ssh_config, host=host)
        assert args.host == host

    def test_supervisor_ssh_task_args_with_port(self, ssh_config):
        """Test SupervisorSSHTaskArgs with Port."""
        port = Port(host_name="test-host", port=9002)
        args = SupervisorSSHTaskArgs(cfg=ssh_config, port=port)
        assert args.port == port

    def test_supervisor_ssh_task_args_with_host_dict(self, ssh_config):
        """Test SupervisorSSHTaskArgs with Host as dict."""
        host_dict = {"name": "test-host", "pool": "test-pool"}
        args = SupervisorSSHTaskArgs(cfg=ssh_config, host=host_dict)
        assert args.host is not None
        assert args.host.name == "test-host"

    def test_supervisor_ssh_task_args_with_port_dict(self, ssh_config):
        """Test SupervisorSSHTaskArgs with Port as dict."""
        port_dict = {"host_name": "test-host", "port": 9002}
        args = SupervisorSSHTaskArgs(cfg=ssh_config, port=port_dict)
        assert args.port is not None
        assert args.port.port == 9002


class TestSupervisorSSHTask:
    def test_supervisor_ssh_task_default_operator(self, ssh_config):
        """Test SupervisorSSHTask default operator path."""
        from airflow_supervisor import SupervisorSSH

        task = SupervisorSSHTask(task_id="test-task", cfg=ssh_config)
        # operator is resolved to the actual class
        assert task.operator == SupervisorSSH

    def test_supervisor_ssh_operator_alias(self):
        """Test SupervisorSSHOperator is an alias for SupervisorSSHTask."""
        assert SupervisorSSHOperator is SupervisorSSHTask

    def test_supervisor_ssh_task_with_host_and_port(self, ssh_config):
        """Test SupervisorSSHTask with Host and Port."""
        host = Host(name="test-host", pool="test-pool")
        port = Port(host_name="test-host", port=9002)
        task = SupervisorSSHTask(
            task_id="test-task",
            cfg=ssh_config,
            host=host,
            port=port,
        )
        assert task.host == host
        assert task.port == port
