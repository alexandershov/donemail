from email.mime.text import MIMEText
from functools import wraps
from itertools import starmap, chain
import smtplib
import argparse
import os
import socket
import subprocess
import sys
import time
import errno

# TODO: refactor everything
# TODO: write docstrings
import traceback


class donemail(object):
    def __init__(self, to, sender='', subject='', message=''):
        self._to = to
        self._subject = subject
        self._message = message
        self._sender = sender or 'donemail@{}'.format(socket.gethostname())

    def __call__(self, function):
        @wraps(function)
        def donemail_function(*args, **kwargs):
            call_str = '{function}({args})'.format(
                function=function.__name__, args=format_call_args(args, kwargs))
            raised = False
            try:
                result = function(*args, **kwargs)
                subject = '{} returned {!r}'.format(call_str, result)
                message = ''
            except Exception as exc:
                raised = True
                exc_type, exc_value, tb = sys.exc_info()
                subject = '{} raised {}'.format(call_str, exc_type.__name__)
                # tb_next is to hide the fact that we're inside of the decorator
                message = '\n'.join(traceback.format_tb(tb.tb_next))
            self.send_email(self._subject or subject,
                            self._message or message)
            if raised:
                # tb_next is to hide the fact that we're inside of the decorator
                raise exc_type, exc_value, tb.tb_next
            return result

        return donemail_function

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            subject = 'raised an exception {!r}'.format(exc_val)
            message = ''
        else:
            # TODO: clean up every self._subject or '' and '' or self._subject
            subject = self._subject or 'done'
            message = self._message or ''
        self.send_email(subject, message)

    def send_email(self, subject='', message=''):
        msg = MIMEText(message or self._message)
        # TODO: do we need both msg['To'] and sendmail(..., [self._to], ...)?
        msg['To'] = self._to
        msg['From'] = self._sender
        msg['Subject'] = subject or self._subject
        s = smtplib.SMTP('localhost')
        s.sendmail(self._sender, [self._to], msg.as_string())
        s.quit()


def main():
    parser = argparse.ArgumentParser(prog='donemail')
    parser.add_argument('email', type=email, help='address to send email to')
    parser.add_argument('--subject', help='subject of the email')
    parser.add_argument('--message', help='message of the email')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pid', type=int, help='pid to wait for')
    group.add_argument('command', nargs='?', help='command to execute')
    parser.add_argument('command_args', nargs=argparse.REMAINDER,
                        help='command arguments')
    args = parser.parse_args()

    if args.pid is not None:
        if not pid_exists(args.pid):
            sys.exit('pid {:d} doesn\'t exist'.format(args.pid))
        sys.stderr.write('waiting for pid {:d} to finish\n'.format(args.pid))
        wait_pid(args.pid)
        subject = 'pid {:d} exited'.format(args.pid)
    else:
        # TODO: send stdin and stderr if status_code != 0
        cmd = [args.command] + args.command_args
        status_code = subprocess.call(cmd)
        subject = '{} exited with the code = {:d}'.format(
            ' '.join(cmd), status_code)
    donemail(to=args.email, message=args.message,
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


def wait_pid(pid, poll_interval_sec=5):
    while pid_exists(pid):
        time.sleep(poll_interval_sec)


def format_call_args(args, kwargs):
    args_part = map(repr, args)
    kwargs_part = ['{}={!r}'.format(name, value)
                   for name, value in kwargs.viewitems()]
    return ', '.join(chain(args_part, kwargs_part))