import pytest
import donemail

BOB = 'bob@example.com'


@pytest.fixture(autouse=True)
def monkeypatch_send_email(monkeypatch):
    monkeypatch.setattr('donemail.send_email', MockSendEmail())


class MockSendEmail(object):
    def __init__(self):
        self.sent_emails = []

    def __call__(self, to, subject, message):
        self.sent_emails.append((to, subject, message))


def test_context_manager():
    assert_num_emails(0)
    with donemail.donemail(BOB):
        pass
    assert_num_emails(1)


def assert_num_emails(expected_num_emails):
    assert len(donemail.send_email.sent_emails) == expected_num_emails


def test_decorator():
    @donemail.donemail(BOB)
    def add(x, y):
        return x + y

    assert_num_emails(0)
    add(1, y=2)
    assert_num_emails(1)


def test_context_manager_with_exception():
    assert_num_emails(0)
    with pytest.raises(ZeroDivisionError):
        with donemail.donemail(BOB):
            1 / 0
    assert_num_emails(1)


def test_decorator_with_exception():
    @donemail.donemail(BOB)
    def divide(x, y):
        return x / y

    assert_num_emails(0)
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
    assert_num_emails(1)

