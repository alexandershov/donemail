import email
import smtplib
import subprocess
import threading

from mock import ANY, Mock
import pytest

from donemail import donemail, main

BOB = 'bob@example.com'


@pytest.fixture(autouse=True)
def monkeypatch_smtplib(monkeypatch):
    mock_smtp_class = Mock()
    mock_smtp_class.return_value = Mock()
    monkeypatch.setattr('smtplib.SMTP', mock_smtp_class)


@donemail(BOB)
def add(x, y):
    return x + y


@donemail(BOB, subject='decorator', body='decorator body')
def mul(x, y):
    return x * y


@pytest.fixture(params=[add, mul])
def donemailed_function(request):
    return request.param


def test_context_manager():
    with donemail(BOB):
        pass
    assert_sent_email(to_addrs=[BOB])


def test_context_manager_subject_body():
    with donemail(BOB, subject='with', body='with body'):
        pass
    assert_sent_email(to_addrs=[BOB], subject='with', body='with body')


def assert_num_emails(expected_num_emails):
    assert get_mock_smtp().sendmail.call_count == expected_num_emails


def assert_sent_email(from_addr=ANY, to_addrs=ANY, subject=ANY, body=ANY):
    mock_smtp = get_mock_smtp()
    mock_smtp.sendmail.assert_called_once_with(from_addr, to_addrs, ANY)
    _, _, mime_string = mock_smtp.sendmail.call_args[0]
    mime_message = email.message_from_string(mime_string)
    assert subject == mime_message['Subject']
    assert body == mime_message.get_payload()


def get_mock_smtp():
    return smtplib.SMTP()


def test_decorator():
    add(1, y=2)
    assert_sent_email(to_addrs=[BOB], subject='add(1, y=2) returned 3')


def test_decorator_subject_body():
    mul(1, y=2)
    assert_sent_email(to_addrs=[BOB], subject='decorator', body='decorator body')


def test_decorator_exception(donemailed_function):
    with pytest.raises(TypeError):
        add(1, None)
    assert_sent_email(to_addrs=[BOB],
                      subject='add(1, None) raised TypeError',
                      # checking that body ignores decorator frame
                      body=~contains('donemail_function'))
    assert_sent_email(body=contains('TypeError'))


class contains(object):
    def __init__(self, substring, inverted=False):
        self._substring = substring
        self._inverted = inverted

    def __invert__(self):
        return contains(self._substring, inverted=not self._inverted)

    def __eq__(self, string):
        if self._inverted:
            return self._substring not in string
        return self._substring in string


def test_context_manager_exception():
    with pytest.raises(ZeroDivisionError):
        with donemail(BOB):
            1 / 0
    assert_sent_email(to_addrs=[BOB],
                      subject='block raised ZeroDivisionError',
                      body=contains('ZeroDivisionError'))


def test_decorator_with_exception():
    @donemail(BOB)
    def divide(x, y):
        return x / y

    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
    assert_sent_email(to_addrs=[BOB])


# TODO: move these tests to a separate (integration) directory

@pytest.fixture
def process():
    return subprocess.Popen(['sleep', '0.5'])


def test_wait_pid(process):
    donemail_wait(process, BOB)
    assert_sent_email(to_addrs=[BOB],
                      subject='process with pid {:d} exited'.format(process.pid))


def donemail_wait(process, to_addr, subject='', body=''):
    cmd_args = ['wait', '--subject', subject, '--body', body, to_addr, str(process.pid)]
    waiting_thread = threading.Thread(target=main, args=[cmd_args])
    waiting_thread.start()
    process.wait()
    waiting_thread.join()


def test_wait_pid_subject_body(process):
    donemail_wait(process, BOB, subject='wait', body='wait body')
    assert_sent_email(to_addrs=[BOB], subject='wait', body='wait body')


def test_wait_pid_that_doesnt_exist():
    pid_that_doesnt_exist = 2 ** 31 - 1
    process = Mock(pid=pid_that_doesnt_exist)
    donemail_wait(process, BOB)
    assert_num_emails(0)


@pytest.mark.parametrize('args, expected_email_attrs', [
    (['run', BOB, 'true'], dict(to_addrs=[BOB], subject='`true` exited with status code 0')),
    (['run', BOB, 'false'], dict(to_addrs=[BOB], subject='`false` exited with status code 1')),
    (['run', '--subject', 'run', '--body', 'run body', BOB, 'true'],
     dict(to_addrs=[BOB], subject='run', body='run body')),
])
def test_run(args, expected_email_attrs):
    main(args)
    assert_sent_email(**expected_email_attrs)
