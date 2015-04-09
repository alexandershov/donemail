import email
import smtplib

from mock import ANY, Mock
import pytest

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
    assert_sent_email(to_addrs=[BOB])


def assert_num_emails(expected_num_emails):
    assert get_mock_smtp().sendmail.call_count == expected_num_emails


def assert_sent_email(from_addr=ANY, to_addrs=ANY, subject=ANY, message=ANY):
    mock_smtp = get_mock_smtp()
    mock_smtp.sendmail.assert_called_once_with(from_addr, to_addrs, ANY)
    _, _, mime_string = mock_smtp.sendmail.call_args[0]
    mime_message = email.message_from_string(mime_string)
    assert subject == mime_message['Subject']
    assert message == mime_message.get_payload()


def get_mock_smtp():
    return smtplib.SMTP()


def test_decorator():
    assert_num_emails(0)
    add(1, y=2)
    assert_sent_email(to_addrs=[BOB], subject='add(1, y=2) returned 3')


@donemail(BOB)
def add(x, y):
    return x + y


def test_context_manager_with_exception():
    assert_num_emails(0)
    with pytest.raises(ZeroDivisionError):
        with donemail(BOB):
            1 / 0
    assert_sent_email(to_addrs=[BOB])


def test_decorator_with_exception():
    @donemail(BOB)
    def divide(x, y):
        return x / y

    assert_num_emails(0)
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
    assert_sent_email(to_addrs=[BOB])

