"""Tests for the Supervisor local operator and its components."""

from unittest.mock import patch

import pytest
from airflow_pydantic.migration import _airflow_3


@pytest.fixture
def supervisor_configuration():
    """Create a Supervisor configuration fixture."""
    from airflow_supervisor import ProgramConfiguration, SupervisorAirflowConfiguration

    with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
        p1.return_value = "/tmp"
        cfg = SupervisorAirflowConfiguration(
            port=9001,
            pool="test-pool",
            stop_on_exit=True,
            cleanup=True,
            program={
                "test": ProgramConfiguration(command="echo hello"),
            },
        )
        yield cfg


@pytest.fixture
def supervisor_no_stop_configuration():
    """Create a Supervisor configuration with stop_on_exit=False."""
    from airflow_supervisor import ProgramConfiguration, SupervisorAirflowConfiguration

    with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
        p1.return_value = "/tmp"
        cfg = SupervisorAirflowConfiguration(
            port=9002,
            pool="test-pool",
            stop_on_exit=False,
            cleanup=False,
            program={
                "test": ProgramConfiguration(command="echo hello"),
            },
        )
        yield cfg


@pytest.fixture
def supervisor_no_cleanup_configuration():
    """Create a Supervisor configuration with cleanup=False."""
    from airflow_supervisor import ProgramConfiguration, SupervisorAirflowConfiguration

    with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
        p1.return_value = "/tmp"
        cfg = SupervisorAirflowConfiguration(
            port=9003,
            pool="test-pool",
            stop_on_exit=True,
            cleanup=False,
            program={
                "test": ProgramConfiguration(command="echo hello"),
            },
        )
        yield cfg


@pytest.fixture
def supervisor_restart_configuration():
    """Create a Supervisor configuration with restart options."""
    from airflow_supervisor import ProgramConfiguration, SupervisorAirflowConfiguration

    with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
        p1.return_value = "/tmp"
        cfg = SupervisorAirflowConfiguration(
            port=9004,
            pool="test-pool",
            restart_on_initial=True,
            restart_on_retrigger=True,
            program={
                "test": ProgramConfiguration(command="echo hello"),
            },
        )
        yield cfg


@pytest.mark.skipif(_airflow_3() is None, reason="Airflow not installed")
class TestSupervisorLocal:
    def test_supervisor_with_dict_config(self, supervisor_configuration):
        """Test Supervisor instantiation with dict config."""
        from airflow.models.dag import DAG

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_configuration.model_dump())
        assert s._cfg.port == supervisor_configuration.port

    def test_supervisor_no_stop_on_exit(self, supervisor_no_stop_configuration):
        """Test Supervisor with stop_on_exit=False creates skip operators."""
        from airflow.models.dag import DAG

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_no_stop", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_no_stop_configuration)
        # When stop_on_exit is False, stop/unconfigure operators become skip operators
        assert s.stop_programs is not None
        assert s.unconfigure_supervisor is not None

    def test_supervisor_no_cleanup(self, supervisor_no_cleanup_configuration):
        """Test Supervisor with cleanup=False creates skip unconfigure operator."""
        from airflow.models.dag import DAG

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_no_cleanup", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_no_cleanup_configuration)
        assert s.unconfigure_supervisor is not None
        assert s.stop_programs is not None

    def test_supervisor_restart_options(self, supervisor_restart_configuration):
        """Test Supervisor with restart options."""
        from airflow.models.dag import DAG

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_restart", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_restart_configuration)
        assert s.start_programs is not None
        # Restart options should be reflected in config
        assert s._cfg.restart_on_initial is True
        assert s._cfg.restart_on_retrigger is True

    def test_supervisor_operator_chaining(self, supervisor_configuration):
        """Test Supervisor operator chaining with << and >>."""
        from airflow.models.dag import DAG
        from airflow.operators.python import PythonOperator

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_chain", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_configuration)

        # Create a simple python operator to chain
        pre_op = PythonOperator(task_id="pre-task", python_callable=lambda: None, dag=dag)
        post_op = PythonOperator(task_id="post-task", python_callable=lambda: None, dag=dag)

        # Test >> operator
        result = s >> post_op
        assert result == post_op

        # Test << operator
        result = s << pre_op
        assert result is not None

    def test_supervisor_set_upstream_downstream(self, supervisor_configuration):
        """Test Supervisor set_upstream and set_downstream methods."""
        from airflow.models.dag import DAG
        from airflow.operators.python import PythonOperator

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_updown", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_configuration)

        upstream_op = PythonOperator(task_id="upstream-task", python_callable=lambda: None, dag=dag)
        downstream_op = PythonOperator(task_id="downstream-task", python_callable=lambda: None, dag=dag)

        s.set_upstream(upstream_op)
        s.set_downstream(downstream_op)

        assert upstream_op in dag.tasks
        assert downstream_op in dag.tasks

    def test_supervisor_leaves_and_roots(self, supervisor_configuration):
        """Test Supervisor leaves and roots properties."""
        from airflow.models.dag import DAG

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_lr", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_configuration)

        # leaves and roots should return the underlying operator's leaves/roots
        assert s.leaves is not None
        assert s.roots is not None

    def test_supervisor_update_relative(self, supervisor_configuration):
        """Test Supervisor update_relative method."""
        from airflow.models.dag import DAG
        from airflow.operators.python import PythonOperator

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_rel", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_configuration)

        other_op = PythonOperator(task_id="other-task", python_callable=lambda: None, dag=dag)

        # Test upstream=True
        result = s.update_relative(other_op, upstream=True)
        assert result == s

        # Test upstream=False
        result = s.update_relative(other_op, upstream=False)
        assert result == s

    def test_supervisor_client_property(self, supervisor_configuration):
        """Test Supervisor supervisor_client property."""
        from airflow.models.dag import DAG

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_client", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_configuration)

        client = s.supervisor_client
        assert client is not None

    def test_supervisor_get_base_operator_kwargs(self, supervisor_configuration):
        """Test Supervisor get_base_operator_kwargs method."""
        from airflow.models.dag import DAG

        from airflow_supervisor import Supervisor

        dag = DAG(dag_id="test_dag_kwargs", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_configuration)

        kwargs = s.get_base_operator_kwargs()
        assert "dag" in kwargs
        assert "pool" in kwargs
        assert kwargs["dag"] == dag
        assert kwargs["pool"] == "test-pool"
