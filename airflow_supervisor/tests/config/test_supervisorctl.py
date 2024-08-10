from airflow_supervisor import SupervisorctlConfiguration


def test_inst():
    SupervisorctlConfiguration()


def test_cfg():
    c = SupervisorctlConfiguration(username="test", password="testpw")
    assert c.to_cfg().strip() == "[supervisorctl]\nusername=test\npassword=testpw"
