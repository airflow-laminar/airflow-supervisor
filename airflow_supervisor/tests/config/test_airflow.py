from airflow_supervisor import AirflowConfiguration, ProgramConfiguration, SupervisorAirflowConfiguration


def test_airflow_inst():
    SupervisorAirflowConfiguration(
        airflow=AirflowConfiguration(port="*:9001"),
        program={
            "test": ProgramConfiguration(
                command="sleep 1 && exit 1",
            )
        },
    )
