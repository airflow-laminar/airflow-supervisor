"""Extended tests for SupervisorSSH operator."""

from unittest.mock import patch

import pytest
from airflow_pydantic.migration import _airflow_3


@pytest.fixture
def ssh_configuration():
    """Create an SSH Supervisor configuration fixture."""
    try:
        from airflow.providers.ssh.hooks.ssh import SSHHook
    except ImportError:
        pytest.skip("SSHHook not available")

    from airflow_pydantic import SSHOperatorArgs

    from airflow_supervisor import ProgramConfiguration, SupervisorSSHAirflowConfiguration

    with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
        p1.return_value = "/tmp"
        cfg = SupervisorSSHAirflowConfiguration(
            port=9001,
            pool="test-pool",
            command_prefix="source /etc/profile &&",
            program={
                "test": ProgramConfiguration(command="echo hello"),
            },
            ssh_operator_args=SSHOperatorArgs(
                ssh_hook=SSHHook(remote_host="localhost"),
            ),
        )
        yield cfg


@pytest.mark.skipif(_airflow_3() is None, reason="Airflow not installed")
class TestSupervisorSSHExtended:
    def test_supervisor_ssh_command_prefix(self, ssh_configuration):
        """Test SupervisorSSH command prefix handling."""
        from airflow.models.dag import DAG

        from airflow_supervisor import SupervisorSSH

        dag = DAG(dag_id="test_ssh_dag_prefix", default_args={}, schedule=None, params={})
        s = SupervisorSSH(dag=dag, cfg=ssh_configuration)
        assert s._command_prefix == "source /etc/profile &&"

    def test_supervisor_ssh_with_port(self, ssh_configuration):
        """Test SupervisorSSH with Port object."""
        from airflow.models.dag import DAG
        from airflow_pydantic import Port

        from airflow_supervisor import SupervisorSSH

        port = Port(host_name="test-host", port=9005)
        dag = DAG(dag_id="test_ssh_dag_port", default_args={}, schedule=None, params={})
        s = SupervisorSSH(dag=dag, cfg=ssh_configuration, port=port)
        # The port should be set in the configuration
        assert s._cfg.port is not None

    def test_supervisor_ssh_with_port_dict(self, ssh_configuration):
        """Test SupervisorSSH with Port as dict."""
        from airflow.models.dag import DAG
        from airflow_pydantic import Port

        from airflow_supervisor import SupervisorSSH

        dag = DAG(dag_id="test_ssh_dag_port_dict", default_args={}, schedule=None, params={})
        port = Port(host_name="test-host", port=9006)
        s = SupervisorSSH(dag=dag, cfg=ssh_configuration, port=port)
        assert s._cfg.port is not None

    def test_supervisor_ssh_get_step_kwargs(self, ssh_configuration):
        """Test SupervisorSSH get_step_kwargs method."""
        from airflow.models.dag import DAG

        from airflow_supervisor import SupervisorSSH

        dag = DAG(dag_id="test_ssh_dag_kwargs", default_args={}, schedule=None, params={})
        s = SupervisorSSH(dag=dag, cfg=ssh_configuration)

        # Test SSH-specific steps
        configure_kwargs = s.get_step_kwargs("configure-supervisor")
        assert "command" in configure_kwargs

        start_kwargs = s.get_step_kwargs("start-supervisor")
        assert "command" in start_kwargs

        stop_kwargs = s.get_step_kwargs("stop-supervisor")
        assert "command" in stop_kwargs

        unconfigure_kwargs = s.get_step_kwargs("unconfigure-supervisor")
        assert "command" in unconfigure_kwargs

        forcekill_kwargs = s.get_step_kwargs("force-kill")
        assert "command" in forcekill_kwargs

    def test_supervisor_ssh_with_host_pool(self):
        """Test SupervisorSSH extracts pool from Host."""
        try:
            from airflow.providers.ssh.hooks.ssh import SSHHook
        except ImportError:
            pytest.skip("SSHHook not available")

        from airflow.models.dag import DAG
        from airflow_pydantic import Host, Pool, SSHOperatorArgs

        from airflow_supervisor import ProgramConfiguration, SupervisorSSH, SupervisorSSHAirflowConfiguration

        with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
            p1.return_value = "/tmp"
            cfg = SupervisorSSHAirflowConfiguration(
                port=9007,
                program={
                    "test": ProgramConfiguration(command="echo hello"),
                },
                ssh_operator_args=SSHOperatorArgs(
                    ssh_hook=SSHHook(remote_host="localhost"),
                ),
            )
            host = Host(name="test-host", pool="host-pool")
            dag = DAG(dag_id="test_ssh_dag_pool", default_args={}, schedule=None, params={})
            s = SupervisorSSH(dag=dag, cfg=cfg, host=host)
            # The pool should be extracted from the host (can be Pool or string)
            if isinstance(s._cfg.pool, Pool):
                assert s._cfg.pool.pool == "host-pool"
            else:
                assert s._cfg.pool == "host-pool"

    def test_supervisor_ssh_kwargs_override(self, ssh_configuration):
        """Test SupervisorSSH with kwargs override."""
        from airflow.models.dag import DAG

        from airflow_supervisor import SupervisorSSH

        dag = DAG(dag_id="test_ssh_dag_override", default_args={}, schedule=None, params={})
        s = SupervisorSSH(
            dag=dag,
            cfg=ssh_configuration,
            command_prefix="custom prefix &&",
        )
        assert s._command_prefix == "custom prefix &&"
