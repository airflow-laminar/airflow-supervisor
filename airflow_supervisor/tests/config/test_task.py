"""Tests for SupervisorTask and SupervisorTaskArgs configurations."""

from unittest.mock import patch

import pytest
from airflow_pydantic.migration import _airflow_3

from airflow_supervisor import ProgramConfiguration, SupervisorAirflowConfiguration
from airflow_supervisor.config import SupervisorOperator, SupervisorOperatorArgs, SupervisorTask, SupervisorTaskArgs


class TestSupervisorTaskArgs:
    def test_supervisor_task_args_instantiation(self):
        """Test basic SupervisorTaskArgs instantiation."""
        with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
            p1.return_value = "/tmp"
            cfg = SupervisorAirflowConfiguration(
                port=9001,
                program={
                    "test": ProgramConfiguration(command="echo hello"),
                },
            )
            args = SupervisorTaskArgs(cfg=cfg)
            assert args.cfg == cfg

    def test_supervisor_operator_args_alias(self):
        """Test SupervisorOperatorArgs is an alias for SupervisorTaskArgs."""
        assert SupervisorOperatorArgs is SupervisorTaskArgs


class TestSupervisorTask:
    def test_supervisor_task_default_operator(self):
        """Test SupervisorTask default operator path."""
        from airflow_supervisor import Supervisor

        with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
            p1.return_value = "/tmp"
            cfg = SupervisorAirflowConfiguration(
                port=9001,
                program={
                    "test": ProgramConfiguration(command="echo hello"),
                },
            )
            task = SupervisorTask(task_id="test-task", cfg=cfg)
            # operator is resolved to the actual class
            assert task.operator == Supervisor

    def test_supervisor_operator_alias(self):
        """Test SupervisorOperator is an alias for SupervisorTask."""
        assert SupervisorOperator is SupervisorTask

    @pytest.mark.skipif(_airflow_3() is None, reason="Airflow not installed")
    def test_supervisor_task_with_dag(self):
        """Test SupervisorTask integration with DAG."""

        with patch("supervisor_pydantic.config.supervisor.gettempdir") as p1:
            p1.return_value = "/tmp"
            cfg = SupervisorAirflowConfiguration(
                port=9001,
                pool="test-pool",
                program={
                    "test": ProgramConfiguration(command="echo hello"),
                },
            )
            task = SupervisorTask(task_id="test-task", cfg=cfg)
            assert task.cfg == cfg
