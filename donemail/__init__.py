from email.mime.text import MIMEText
from functools import wraps
from itertools import chain
import smtplib
import argparse
import os
import socket
import subprocess
import sys
import time
import traceback
import errno

# TODO: refactor everything
# TODO: write docstrings

__all__ = ['donemail']


class donemail(object):
    # TODO: allow to configure smtp connection
    def __init__(self, to, subject='', body='', sender=''):
        self._to = to
        self._subject = subject
        self._body = body
        self._sender = sender or _get_default_sender()

    def __call__(self, function):
        @wraps(function)
        def donemail_function(*args, **kwargs):
            call_str = _make_call_str(function, args, kwargs)
            try:
                result = function(*args, **kwargs)
            except Exception as exc:
                exc_type, exc_value, tb = sys.exc_info()
                subject = '{} raised {}'.format(call_str, exc_type.__name__)
                # tb_next is to hide the fact that we're inside of the decorator
                body = '\n'.join(traceback.format_exception(exc_type, exc_value, tb.tb_next))
                self.send_email(subject, body)
                raise exc_type, exc_value, tb.tb_next
            else:
                self.send_email('{} returned {!r}'.format(call_str, result))
                return result

        return donemail_function

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_value is not None:
            subject = 'block raised {}'.format(exc_type.__name__)
            body = '\n'.join(traceback.format_exception(exc_type, exc_value, tb))
            self.send_email(subject, body)
        else:
            self.send_email(subject='done')

    def send_email(self, subject='', body=''):
        msg = MIMEText(self._body or body)
        # TODO: do we need both msg['To'] and sendmail(..., [self._to], ...)?
        msg['To'] = self._to
        msg['From'] = self._sender
        msg['Subject'] = self._subject or subject
        # TODO: handle bad connection gracefully
        s = smtplib.SMTP('localhost')
        try:
            s.sendmail(self._sender, [self._to], msg.as_string())
        finally:
            s.quit()


def main(cmd_args=None):
    parser = argparse.ArgumentParser(prog='donemail')
    subparsers = parser.add_subparsers()
    parent_parser = _get_parent_parser()

    wait_parser = subparsers.add_parser(
        'wait', parents=[parent_parser],
        help='send an email after the process with the specified pid exits')
    wait_parser.add_argument('--poll-interval', type=float, default=1.0,
                             help='sleep duration (in seconds) between pid checks')
    wait_parser.add_argument('pid', type=int, help='pid to wait for')
    wait_parser.set_defaults(func=_wait_pid)

    run_parser = subparsers.add_parser(
        'run', parents=[parent_parser],
        help='run a command and send an email after a command exits')
    run_parser.add_argument('command', help='command to execute')
    run_parser.add_argument('command_args', nargs=argparse.REMAINDER, help='command arguments')
    run_parser.set_defaults(func=_run_command)
    args = parser.parse_args(cmd_args)
    donemail_obj = donemail(to=args.email, body=args.body, subject=args.subject)
    args.func(args, donemail_obj)


def _email(s):
    if '@' not in s:
        raise argparse.ArgumentTypeError(
            'email should contain @. Got: {!r}'.format(s))
    return s


def _pid_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError as exc:
        if exc.errno == errno.ESRCH:  # no such process
            return False
        elif exc.errno == errno.EPERM:  # process exists, but is not killable
            return True
        return False


def _wait_pid(args, donemail_obj):
    if not _pid_exists(args.pid):
        sys.exit('pid {:d} doesn\'t exist'.format(args.pid))
    sys.stderr.write('waiting for pid {:d} to finish\n'.format(args.pid))

    while _pid_exists(args.pid):
        time.sleep(args.poll_interval)
    subject = 'process with pid {:d} exited'.format(args.pid)
    donemail_obj.send_email(subject)


def _run_command(args, donemail_obj):
    cmd = [args.command] + args.command_args
    status_code = subprocess.call(cmd)
    subject = '`{}` exited with status code {:d}'.format(
        ' '.join(cmd), status_code)
    donemail_obj.send_email(subject)


def _make_call_str(function, args, kwargs):
    args_part = map(repr, args)
    kwargs_part = ['{}={!r}'.format(name, value)
                   for name, value in kwargs.viewitems()]
    all_args_part = ', '.join(chain(args_part, kwargs_part))
    return '{}({})'.format(function.__name__, all_args_part)


def _get_default_sender():
    return 'donemail@{}'.format(socket.gethostname())


def _get_parent_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('email', type=_email, help='address to send email to')
    parser.add_argument('--subject', help='subject of the email')
    parser.add_argument('--body', help='body of the email')
    return parser