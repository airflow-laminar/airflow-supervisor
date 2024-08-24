from pathlib import Path

from airflow_supervisor import AirflowConfiguration, ProgramConfiguration, SupervisorAirflowConfiguration

if __name__ == "__main__":
    path = Path(__file__).parent.parent.parent
    cfg = SupervisorAirflowConfiguration(
        airflow=AirflowConfiguration(port="*:9090"),
        working_dir=path,
        path=path,
        program={
            "test": ProgramConfiguration(
                command="bash -c 'sleep 60; exit 1'",
            )
        },
    )
    print(cfg._pydantic_path)
    cfg._write_self()
