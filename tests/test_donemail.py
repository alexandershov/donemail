from mock import ANY, Mock
import pytest
import smtplib

from donemail import donemail

BOB = 'bob@example.com'


@pytest.fixture(autouse=True)
def monkeypatch_smtplib(monkeypatch):
    mock_smtp_class = Mock()
    mock_smtp_class.return_value = Mock()
    monkeypatch.setattr('smtplib.SMTP', mock_smtp_class)


def test_context_manager():
    assert_num_emails(0)
    with donemail(BOB):
        pass
    assert_sent_email(ANY, [BOB], ANY)


def assert_num_emails(expected_num_emails):
    assert get_mock_smtp().sendmail.call_count == expected_num_emails


def assert_sent_email(from_addr, to_addrs, msg):
    get_mock_smtp().sendmail.assert_called_once_with(from_addr, to_addrs, msg)


def get_mock_smtp():
    return smtplib.SMTP()


def test_decorator():
    @donemail(BOB)
    def add(x, y):
        return x + y

    assert_num_emails(0)
    add(1, y=2)
    assert_sent_email(ANY, [BOB], ANY)


def test_context_manager_with_exception():
    assert_num_emails(0)
    with pytest.raises(ZeroDivisionError):
        with donemail(BOB):
            1 / 0
    assert_sent_email(ANY, [BOB], ANY)


def test_decorator_with_exception():
    @donemail(BOB)
    def divide(x, y):
        return x / y

    assert_num_emails(0)
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
    assert_sent_email(ANY, [BOB], ANY)

