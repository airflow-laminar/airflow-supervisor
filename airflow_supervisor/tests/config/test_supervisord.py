from airflow_supervisor import SupervisordConfiguration


def test_inst():
    SupervisordConfiguration()


def test_cfg():
    c = SupervisordConfiguration(directory="/test")
    assert c.to_cfg().strip() == "[supervisord]\ndirectory=/test"
