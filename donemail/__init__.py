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

class donemail(object):
    def __init__(self, to, subject='', body='', sender=''):
        self._to = to
        self._subject = subject
        self._body = body
        self._sender = sender or donemail._get_default_sender()

    @staticmethod
    def _get_default_sender():
        return 'donemail@{}'.format(socket.gethostname())

    def __call__(self, function):
        @wraps(function)
        def donemail_function(*args, **kwargs):
            call_str = make_call_str(function, args, kwargs)
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
    parser.add_argument('email', type=email, help='address to send email to')
    parser.add_argument('--subject', help='subject of the email')
    parser.add_argument('--body', help='body of the email')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pid', type=int, help='pid to wait for')
    group.add_argument('command', nargs='?', help='command to execute')
    parser.add_argument('command_args', nargs=argparse.REMAINDER,
                        help='command arguments')
    args = parser.parse_args(cmd_args)

    if args.pid is not None:
        if not pid_exists(args.pid):
            sys.exit('pid {:d} doesn\'t exist'.format(args.pid))
        sys.stderr.write('waiting for pid {:d} to finish\n'.format(args.pid))
        wait_pid(args.pid)
        subject = 'process with pid {:d} exited'.format(args.pid)
    else:
        cmd = [args.command] + args.command_args
        status_code = subprocess.call(cmd)
        subject = '`{}` exited with status code {:d}'.format(
            ' '.join(cmd), status_code)
    donemail(to=args.email, body=args.body,
             subject=(args.subject or subject)).send_email()


def email(s):
    if '@' not in s:
        raise argparse.ArgumentTypeError(
            'email should contain @. Got: {!r}'.format(s))
    return s


def pid_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError as exc:
        if exc.errno == errno.ESRCH:  # no such process
            return False
        elif exc.errno == errno.EPERM:  # process exists, but is not killable
            return True
        return False


# TODO: make poll_interval_sec a command-line option
def wait_pid(pid, poll_interval_sec=1):
    while pid_exists(pid):
        time.sleep(poll_interval_sec)


def make_call_str(function, args, kwargs):
    args_part = map(repr, args)
    kwargs_part = ['{}={!r}'.format(name, value)
                   for name, value in kwargs.viewitems()]
    all_args_part = ', '.join(chain(args_part, kwargs_part))
    return '{}({})'.format(function.__name__, all_args_part)