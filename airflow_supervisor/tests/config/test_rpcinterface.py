from airflow_supervisor import RpcInterfaceConfiguration


def test_inst():
    RpcInterfaceConfiguration()
    RpcInterfaceConfiguration(rpcinterface_factory="a.test.module")


def test_cfg():
    c = RpcInterfaceConfiguration(rpcinterface_factory="a.test.module")
    assert c.to_cfg("name").strip() == "[rpcinterface:name]\nsupervisor.rpcinterface_factory=a.test.module"
