import socket
from tempfile import NamedTemporaryFile
from time import sleep
from typing import Iterator

from pytest import fixture

from airflow_supervisor import AirflowConfiguration, ProgramConfiguration, SupervisorAirflowConfiguration


@fixture(scope="module")
def open_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


@fixture(scope="module")
def permissioned_open_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


@fixture(scope="module")
def supervisor_airflow_configuration(open_port: int) -> Iterator[SupervisorAirflowConfiguration]:
    with NamedTemporaryFile("w", suffix=".cfg") as tf:
        cfg = SupervisorAirflowConfiguration(
            airflow=AirflowConfiguration(port=f"*:{open_port}"),
            path=tf.name,
            program={
                "test": ProgramConfiguration(
                    command="bash -c 'sleep 1; exit 1'",
                )
            },
        )
        yield cfg


@fixture(scope="module")
def permissioned_supervisor_airflow_configuration(
    permissioned_open_port: int,
) -> Iterator[SupervisorAirflowConfiguration]:
    with NamedTemporaryFile("w", suffix=".cfg") as tf:
        cfg = SupervisorAirflowConfiguration(
            airflow=AirflowConfiguration(
                port=f"*:{permissioned_open_port}", username="user1", password="testpassword1"
            ),
            path=tf.name,
            program={
                "test": ProgramConfiguration(
                    command="bash -c 'sleep 1; exit 1'",
                )
            },
        )
        yield cfg


@fixture(scope="module")
def supervisor_instance(
    supervisor_airflow_configuration: SupervisorAirflowConfiguration,
) -> Iterator[SupervisorAirflowConfiguration]:
    cfg = supervisor_airflow_configuration
    cfg.write()
    cfg.start(daemon=False)
    for _ in range(5):
        if not cfg.running():
            sleep(1)
    yield cfg
    cfg.kill()


@fixture(scope="module")
def permissioned_supervisor_instance(
    permissioned_supervisor_airflow_configuration: SupervisorAirflowConfiguration,
) -> Iterator[SupervisorAirflowConfiguration]:
    cfg = permissioned_supervisor_airflow_configuration
    cfg.write()
    cfg.start(daemon=False)
    for _ in range(5):
        if not cfg.running():
            sleep(1)
    yield cfg
    cfg.kill()
