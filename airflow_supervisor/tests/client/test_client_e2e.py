import xmlrpc
from time import sleep

import pytest

from airflow_supervisor import SupervisorAirflowConfiguration, SupervisorRemoteXMLRPCClient
from airflow_supervisor.client.xmlrpc import ProcessState


def _assert_client_actions(client: SupervisorRemoteXMLRPCClient):
    assert client.getProcessInfo("test").state == ProcessState.STOPPED
    sleep(0.5)
    assert client.startAllProcesses()["test"].state == ProcessState.RUNNING
    sleep(0.5)
    assert client.getProcessInfo("test").state == ProcessState.EXITED
    assert client.startProcess("test").state == ProcessState.RUNNING
    assert client.stopProcess("test").state == ProcessState.STOPPED
    assert client.startProcess("test").state == ProcessState.RUNNING
    assert client.stopAllProcesses()["test"].state == ProcessState.STOPPED


def test_supervisor_client(supervisor_instance: SupervisorAirflowConfiguration):
    client = SupervisorRemoteXMLRPCClient(supervisor_instance)
    _assert_client_actions(client=client)


def test_permissioned_supervisor_client_rejected(permissioned_supervisor_instance: SupervisorAirflowConfiguration):
    permissioned_supervisor_instance.airflow.username = "bad-username"
    client = SupervisorRemoteXMLRPCClient(permissioned_supervisor_instance)
    with pytest.raises(xmlrpc.client.ProtocolError):
        client.getProcessInfo("test")


def test_permissioned_supervisor_client(permissioned_supervisor_instance: SupervisorAirflowConfiguration):
    permissioned_supervisor_instance.airflow.username = "user1"
    client = SupervisorRemoteXMLRPCClient(permissioned_supervisor_instance)
    _assert_client_actions(client=client)
