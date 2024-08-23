from time import sleep

from airflow_supervisor import SupervisorAirflowConfiguration, SupervisorRemoteXMLRPCClient


def test_supervisor_client(supervisor_instance: SupervisorAirflowConfiguration):
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
