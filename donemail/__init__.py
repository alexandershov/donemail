from email.mime.text import MIMEText
from functools import wraps
from itertools import starmap, chain
import smtplib
import argparse
import os
import subprocess
import sys
import time


def send_email(to, subject, message):
    sender = 'donemail@example.com'
    msg = MIMEText(message)
    msg['To'] = to
    msg['From'] = sender
    msg['Subject'] = subject
    s = smtplib.SMTP('localhost')
    s.sendmail(sender, [to], msg.as_string())
    s.quit()


class donemail(object):
    def __init__(self, to, subject='', message=''):
        self._to = to
        self._subject = subject
        self._message = message

    def __call__(self, function):
        @wraps(function)
        def donemail_function(*args, **kwargs):
            result = function(*args, **kwargs)
            # TODO: catch, send, and reraise exceptions
            if not self._subject:
                subject = '{function}({args}) returned {result!r}'.format(
                    function=function.__name__,
                    args=format_call_args(args, kwargs),
                    result=result)
            else:
                subject = self._subject
            send_email(self._to, subject, self._message)
            return result

        return donemail_function

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: send exception info
        send_email(self._to, self._subject or 'done', self._message)


def main():
    parser = argparse.ArgumentParser(prog='donemail')
    parser.add_argument('email', type=email)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pid', type=int)
    group.add_argument('command', nargs='?')
    parser.add_argument('command_args', nargs=argparse.REMAINDER)
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
        subject = '{} exited with status_code = {:d}'.format(
            ' '.join(cmd), status_code)

    send_email(args.email, subject, '')


def email(s):
    if '@' not in s:
        raise ValueError('email should have @ in it. Got: <{}>'.format(s))
    return s


def pid_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    # TODO: check OSError.errno to handle case when we don't have permission
    # to send a signal to pid
    except OSError:
        return False


def wait_pid(pid, poll_interval_sec=5):
    while pid_exists(pid):
        time.sleep(poll_interval_sec)


def format_call_args(args, kwargs):
    pos_args_part = map('{!r}'.format, args)
    kw_args_part = starmap('{}={!r}'.format, kwargs.iteritems())
    return ', '.join(chain(pos_args_part, kw_args_part))