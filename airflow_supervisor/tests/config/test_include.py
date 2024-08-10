from pydantic import ValidationError
from pytest import raises

from airflow_supervisor import IncludeConfiguration


def test_inst():
    with raises(ValidationError):
        IncludeConfiguration()
    IncludeConfiguration(files=[""])


def test_cfg():
    c = IncludeConfiguration(files=["a/test/file", "another/test/file"])
    assert c.to_cfg().strip() == "[include]\nfiles=a/test/file another/test/file"
