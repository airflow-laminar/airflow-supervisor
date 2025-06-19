from airflow.models.dag import DAG
from airflow_balancer import Host

from airflow_supervisor import SupervisorSSH, SupervisorSSHAirflowConfiguration


class TestSSH:
    def test_ssh_setup(self, supervisor_airflow_ssh_configuration):
        assert supervisor_airflow_ssh_configuration is not None
        assert isinstance(supervisor_airflow_ssh_configuration, SupervisorSSHAirflowConfiguration)
        assert supervisor_airflow_ssh_configuration.ssh_operator_args.ssh_hook.remote_host == "localhost"

    def test_ssh_overrides(self, supervisor_airflow_ssh_configuration):
        dag = DAG(dag_id="test_dag", default_args={}, schedule=None, params={})
        inst = SupervisorSSH(
            dag=dag,
            cfg=supervisor_airflow_ssh_configuration,
            host=Host(name="test-host"),
        )
        assert inst._cfg.ssh_operator_args.ssh_hook.remote_host == "test-host"
