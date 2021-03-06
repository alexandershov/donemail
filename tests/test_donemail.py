import email
import smtplib
import subprocess
import threading

from mock import ANY, Mock
import six
import pytest

from donemail import donemail, main


BOB = 'bob@example.com'


@pytest.fixture(autouse=True)
def monkeypatch_smtplib(monkeypatch):
    monkeypatch.setattr('smtplib.SMTP', Mock())


@donemail(BOB)
def add(x, y):
    return x + y


@donemail(BOB, subject='decorator', body='decorator body')
def mul(x, y):
    return x * y


def test_context_manager():
    with donemail(BOB):
        pass
    assert_sent_email(to_addr=BOB)


def test_context_manager_subject_body():
    with donemail(BOB, subject='with', body='with body'):
        pass
    assert_sent_email(to_addr=BOB, subject='with', body='with body')


def assert_num_emails(expected_num_emails):
    assert get_mock_smtp().sendmail.call_count == expected_num_emails


def assert_sent_email(from_addr=ANY, to_addr=ANY, subject=ANY, body=ANY):
    mock_smtp = get_mock_smtp()
    mock_smtp.sendmail.assert_called_once_with(from_addr, to_addr, ANY)
    _, _, mime_string = mock_smtp.sendmail.call_args[0]
    mime_message = email.message_from_string(mime_string)
    assert subject == mime_message['Subject']
    assert body == mime_message.get_payload()


def get_mock_smtp():
    return smtplib.SMTP()


def test_decorator():
    add(1, y=2)
    assert_sent_email(to_addr=BOB, subject='add(1, y=2) returned 3')


def test_decorator_subject_body():
    mul(1, y=2)
    assert_sent_email(to_addr=BOB, subject='decorator', body='decorator body')


def test_decorator_exception():
    with pytest.raises(TypeError):
        add(1, None)
    assert_sent_email(to_addr=BOB,
                      subject='add(1, None) raised TypeError',
                      # checking that body ignores decorator frame
                      body=~Contains('donemail_function'))
    assert_sent_email(body=Contains('TypeError'))


class Contains(object):
    def __init__(self, substring, inverted=False):
        self._substring = substring
        self._inverted = inverted

    def __invert__(self):
        return Contains(self._substring, inverted=not self._inverted)

    def __eq__(self, string):
        if self._inverted:
            return self._substring not in string
        return self._substring in string


def test_context_manager_exception():
    with pytest.raises(ValueError):
        with donemail(BOB):
            raise ValueError
    assert_sent_email(to_addr=BOB,
                      subject='block raised ValueError',
                      body=Contains('ValueError'))


def test_decorator_with_exception():
    @donemail(BOB)
    def divide(x, y):
        return x / y

    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
    assert_sent_email(to_addr=BOB)


@pytest.fixture
def process():
    return subprocess.Popen(['sleep', '0.5'])


def test_wait_pid(process):
    donemail_wait(BOB, process)
    assert_sent_email(to_addr=BOB,
                      subject='process with pid {:d} exited'.format(process.pid))


def donemail_wait(to_addr, process, subject=None, body=None, poll_interval=0.1):
    options = make_options_list(subject=subject, body=body, poll_interval=poll_interval)
    cmd_args = ['wait'] + options + [to_addr, str(process.pid)]
    waiting_thread = threading.Thread(target=main, args=[cmd_args])
    waiting_thread.start()
    process.wait()
    waiting_thread.join()


def test_wait_pid_subject_body(process):
    donemail_wait(BOB, process, subject='wait', body='wait body')
    assert_sent_email(to_addr=BOB, subject='wait', body='wait body')


def test_wait_pid_that_doesnt_exist():
    pid_that_doesnt_exist = 2 ** 31 - 1
    donemail_wait(BOB, process=Mock(pid=pid_that_doesnt_exist))
    assert_num_emails(0)


def test_run_zero_status_code():
    donemail_run(BOB, ['true'])
    assert_sent_email(to_addr=BOB, subject='`true` exited with status code 0')


def test_run_non_zero_status_code():
    donemail_run(BOB, ['false'])
    assert_sent_email(to_addr=BOB, subject='`false` exited with status code 1')


def test_run_subject_body():
    donemail_run(BOB, ['true'], subject='run', body='run body')
    assert_sent_email(to_addr=BOB, subject='run', body='run body')


def donemail_run(to_addr, cmd, subject=None, body=None, smtp=None):
    options = make_options_list(subject=subject, body=body, smtp=smtp)
    args = ['run'] + options + [to_addr] + cmd
    main(args)


def make_options_list(**kwargs):
    options = []
    for name, value in six.viewitems(kwargs):
        if value:
            options.extend([make_option_name(name), str(value)])
    return options


def make_option_name(name):
    """
    'poll_interval' -> '--poll-interval'
    """
    return '--' + name.replace('_', '-')


def test_run_smtp_option():
    donemail_run(BOB, ['true'], smtp='localhost:3000')
    smtplib.SMTP.assert_called_once_with('localhost', 3000)


disable_default_smtplib_monkeypatch = pytest.mark.parametrize('monkeypatch_smtplib', [''])


@disable_default_smtplib_monkeypatch
def test_doesnt_raise_with_smtplib_connect_error(monkeypatch):
    monkeypatch.setattr('smtplib.SMTP', Mock(side_effect=Exception))
    add(1, y=2)


@disable_default_smtplib_monkeypatch
def test_doesnt_raise_with_smtplib_send_error(monkeypatch):
    mock_smtp_class = Mock()
    mock_smtp_class.return_value.sendmail = Exception
    monkeypatch.setattr('smtplib.SMTP', mock_smtp_class)
    add(1, y=2)


@disable_default_smtplib_monkeypatch
def test_doesnt_raise_with_smtplib_quit_error(monkeypatch):
    mock_smtp_class = Mock()
    mock_smtp_class.return_value.quit = Exception
    monkeypatch.setattr('smtplib.SMTP', mock_smtp_class)
    add(1, y=2)

