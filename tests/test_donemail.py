from mock import Mock
import pytest

from donemail import donemail

BOB = 'bob@example.com'


@pytest.fixture(autouse=True)
def monkeypatch_send_email(monkeypatch):
    monkeypatch.setattr(donemail, 'send_email', Mock())


def test_context_manager():
    assert_num_emails(0)
    with donemail(BOB):
        pass
    assert_num_emails(1)


def assert_num_emails(expected_num_emails):
    assert donemail.send_email.call_count == expected_num_emails


def test_decorator():
    @donemail(BOB)
    def add(x, y):
        return x + y

    assert_num_emails(0)
    add(1, y=2)
    assert_num_emails(1)


def test_context_manager_with_exception():
    assert_num_emails(0)
    with pytest.raises(ZeroDivisionError):
        with donemail(BOB):
            1 / 0
    assert_num_emails(1)


def test_decorator_with_exception():
    @donemail(BOB)
    def divide(x, y):
        return x / y

    assert_num_emails(0)
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
    assert_num_emails(1)

