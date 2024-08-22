import socket
from tempfile import NamedTemporaryFile
from time import sleep

from pytest import fixture

from airflow_supervisor import AirflowConfiguration, ProgramConfiguration, SupervisorAirflowConfiguration, SupervisorRemoteXMLRPCClient


@fixture
def open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


@fixture
def supervisor_instance(open_port):
    with NamedTemporaryFile("w", suffix=".cfg") as tf:
        cfg = SupervisorAirflowConfiguration(
            airflow=AirflowConfiguration(port=f"*:{open_port}"),
            path=tf.name,
            program={
                "test": ProgramConfiguration(
                    command="sleep 1 && exit 1",
                )
            },
        )
        cfg.write()
        cfg.start(daemon=False)
        for _ in range(5):
            if not cfg.running():
                sleep(1)
        yield cfg
        cfg.kill()


def test_supervisor_client(supervisor_instance):
    client = SupervisorRemoteXMLRPCClient(supervisor_instance)
    print(client.getProcessInfo("test"))
    sleep(0.5)
    print(client.startAllProcesses())
    sleep(0.5)
    print(client.getProcessInfo("test"))
    sleep(0.5)
    print(client.getProcessInfo("test"))
    sleep(0.5)
    print(client.getProcessInfo("test"))
    print(client.startProcess("test"))
    sleep(0.5)
    print(client.startProcess("test"))
    sleep(0.5)
    print(client.stopAllProcesses())
    sleep(0.5)
    print(client.startProcess("test"))
    sleep(0.5)
    print(client.stopAllProcesses())
    sleep(0.5)
    print(client.stopProcess("test"))
    sleep(0.5)
