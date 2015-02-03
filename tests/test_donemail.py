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
    assert len(donemail.send_email.sent_emails) == 0
    with donemail.donemail(BOB):
        pass
    assert len(donemail.send_email.sent_emails) == 1


def test_decorator():
    @donemail.donemail(BOB)
    def add(x, y):
        return x + y

    assert len(donemail.send_email.sent_emails) == 0
    add(1, 2)
    assert len(donemail.send_email.sent_emails) == 1

