from airflow.models.dag import DAG


class TestSSH:
    def test_ssh_setup(self, supervisor_airflow_ssh_configuration):
        from airflow_supervisor import SupervisorSSHAirflowConfiguration

        assert supervisor_airflow_ssh_configuration is not None
        assert isinstance(supervisor_airflow_ssh_configuration, SupervisorSSHAirflowConfiguration)
        assert supervisor_airflow_ssh_configuration.ssh_operator_args.ssh_hook.remote_host == "localhost"

    def test_ssh_overrides(self, supervisor_airflow_ssh_configuration):
        from airflow_pydantic import Host

        from airflow_supervisor import SupervisorSSH

        dag = DAG(dag_id="test_dag", default_args={}, schedule=None, params={})
        inst = SupervisorSSH(
            dag=dag,
            cfg=supervisor_airflow_ssh_configuration,
            host=Host(name="test-host"),
        )
        assert inst._cfg.ssh_operator_args.ssh_hook.remote_host == "test-host"
