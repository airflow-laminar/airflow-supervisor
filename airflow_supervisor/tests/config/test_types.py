from pytest import raises

from airflow_supervisor.config.base import _is_octal, _is_username, _is_username_or_usernamegroup


def test_is_octal():
    is_octal = _is_octal(4)
    assert is_octal("0700") == "0700"
    with raises(AssertionError):
        assert is_octal("0800")
    with raises(AssertionError):
        assert is_octal("1800")
    with raises(AssertionError):
        assert is_octal("000")


def test_is_username():
    assert _is_username("test")
    with raises(AssertionError):
        assert _is_username("test@123")
    with raises(AssertionError):
        assert _is_username("test:hey")


def test_is_username_or_usernamegroup():
    assert _is_username_or_usernamegroup("test")
    assert _is_username_or_usernamegroup("test:hey")
    with raises(AssertionError):
        assert _is_username_or_usernamegroup("test@123")
