from airflow_supervisor import UnixHttpServerConfiguration


def test_inst():
    UnixHttpServerConfiguration()
    UnixHttpServerConfiguration(file="/a/test/file")
    UnixHttpServerConfiguration(file="/a/test/file", username="test")
    UnixHttpServerConfiguration(file="/a/test/file", username="test", chmod="0777")


def test_cfg():
    c = UnixHttpServerConfiguration()
    assert c.to_cfg().strip() == """[unix_http_server]"""

    c = UnixHttpServerConfiguration(
        file="/a/test/file",
        chmod="0777",
        chown="test",
        username="test",
        password="testpw",
    )
    assert (
        c.to_cfg()
        == """[unix_http_server]
file=/a/test/file
chmod=0777
chown=test
username=test
password=testpw
"""
    )
