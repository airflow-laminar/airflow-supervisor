from pydantic import ValidationError
from pytest import raises

from airflow_supervisor import RpcInterfaceConfiguration


def test_inst():
    with raises(ValidationError):
        RpcInterfaceConfiguration()
    RpcInterfaceConfiguration(supervisor_rpcinterface_factory="a.test.module")


def test_cfg():
    c = RpcInterfaceConfiguration(supervisor_rpcinterface_factory="a.test.module")
    assert c.to_cfg("name").strip() == "[rpcinterface:name]\nsupervisor_rpcinterface_factory=a.test.module"
