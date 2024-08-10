from airflow_supervisor import InetHttpServerConfiguration


def test_inst():
    InetHttpServerConfiguration()
    InetHttpServerConfiguration(port="127.0.0.1:8000")
    InetHttpServerConfiguration(port="127.0.0.1:8000", username="test")
    InetHttpServerConfiguration(port="127.0.0.1:8000", username="test", password="testpw")


def test_cfg():
    c = InetHttpServerConfiguration()
    assert c.to_cfg().strip() == """[inet_http_server]"""

    c = InetHttpServerConfiguration(port="127.0.0.1:8000", username="test", password="testpw")
    assert (
        c.to_cfg()
        == """[inet_http_server]
port=127.0.0.1:8000
username=test
password=testpw
"""
    )
