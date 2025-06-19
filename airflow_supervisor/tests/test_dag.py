from airflow.models.dag import DAG

from airflow_supervisor import Supervisor, SupervisorAirflowConfiguration


class TestDag:
    def test_instantiation(self, supervisor_airflow_configuration: SupervisorAirflowConfiguration):
        dag = DAG(dag_id="test_dag", default_args={}, schedule=None, params={})
        s = Supervisor(dag=dag, cfg=supervisor_airflow_configuration)
        assert len(dag.tasks) == 17
        assert dag.catchup is False
        assert dag.concurrency == 1
        assert dag.max_active_tasks == 1
        assert dag.max_active_runs == 1

        assert s.configure_supervisor in dag.tasks
        assert s.configure_supervisor in dag.tasks
        assert s.start_supervisor in dag.tasks
        assert s.start_programs in dag.tasks
        assert s.check_programs in dag.tasks
        assert s.restart_programs in dag.tasks
        assert s.stop_programs in dag.tasks
        assert s.stop_supervisor in dag.tasks
        assert s.unconfigure_supervisor in dag.tasks

        for task in dag.tasks:
            assert task.dag == dag, f"Task {task.task_id} is not associated with the DAG"
            assert task.pool == supervisor_airflow_configuration.airflow.pool, (
                f"Task {task.task_id} does not have the correct pool set"
            )
