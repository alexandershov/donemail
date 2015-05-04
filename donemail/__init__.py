from collections import namedtuple
from email.mime.text import MIMEText
from functools import wraps
from itertools import chain
import argparse
import errno
import logging
import os
import smtplib
import socket
import subprocess
import sys
import time
import traceback

import six


__all__ = ['donemail']


class _SMTPConnectError(Exception):
    pass


class _Address(namedtuple('_Address', ['host', 'port'])):
    __slots__ = ()

    @classmethod
    def from_string(cls, host_port):
        """
        :param host_port: string of the form host:port. E.g: 'localhost:25'
        """
        host, _, port_s = host_port.partition(':')
        if not port_s:
            raise ValueError('bad address: {!r} doesn\'t have a port'.format(host_port))
        try:
            int(port_s)
        except ValueError as exc:
            six.raise_from(ValueError('bad port: {!r} (not an integer)'.format(port_s)), exc)
        return cls(host=host, port=int(port_s))

    def __str__(self):
        return '{}:{}'.format(self.host, self.port)


_DEFAULT_SMTP_ADDRESS = _Address.from_string('localhost:25')


class donemail(object):
    def __init__(self, to, subject='', body='', sender='', smtp_address=_DEFAULT_SMTP_ADDRESS):
        """
        :param to: email address to send emails to
        :param subject: subject of the email. Will be set to appropriate value if not specified.
          Appropriate value for the:
          * decorator (@donemail) is 'function X returned Y'
            or 'function X raised Y' if decoratee raised an exception.
          * context manager (with donemail(...)) is 'done'
            or 'block raised Y' if block raised an exception.
          * command line invocation (donemail wait) is
            'process with pid X exited'.
          * command line invocation (donemail run) is
            'X exited with status code Y'
        :param body: body of the email. Will be set to appropriate value if not specified.
          Appropriate value for the:
          * decorator (@donemail) is empty string
            or a traceback if decoratee raised an exception.
          * context manager (with donemail(...)) is empty string
            or a traceback if block raised an exception.
          * command line invocation (donemail wait) is empty string.
          * command line invocation (donemail run) is empty string.
        :param sender: sender of the email. 'donemail@your-host' by default.
        :param smtp_address: tuple (host, port)
        """
        self._to = to
        self._subject = subject
        self._body = body
        self._sender = sender or _get_default_sender()
        self._smtp_address = _Address(*smtp_address)

    def __call__(self, function):
        """
        A decorator. Return a version of function that sends an email on completion/exception.
        Decorated function reraises all exceptions raised by function.
        See donemail.__init__ for more details on email subject/body.

        :param function: function to decorate
        :return: function that sends an email on completion/exception.
        """

        @wraps(function)
        def donemail_function(*args, **kwargs):
            call_str = _make_call_str(function, args, kwargs)
            # noinspection PyBroadException
            try:
                result = function(*args, **kwargs)
            except Exception:
                exc_type, exc_value, tb = sys.exc_info()
                subject = '{} raised {}'.format(call_str, exc_type.__name__)
                # tb_next is to hide the fact that we're inside of the decorator
                body = '\n'.join(traceback.format_exception(exc_type, exc_value, tb.tb_next))
                self.send_email(subject, body)
                six.reraise(exc_type, exc_value, tb.tb_next)
            else:
                self.send_email('{} returned {!r}'.format(call_str, result))
                return result

        return donemail_function

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        """
        Send an email with the exception (if any) details.
        See donemail.__init__ for more details on email subject/body.
        """
        if exc_value is not None:
            subject = 'block raised {}'.format(exc_type.__name__)
            body = '\n'.join(traceback.format_exception(exc_type, exc_value, tb))
            self.send_email(subject, body)
        else:
            self.send_email(subject='done')

    def send_email(self, subject='', body=''):
        """
        Send an email to self._to
        Catch, log and don't reraise smtp errors (when server isn't running on
        the specified host:port etc)

        :param subject: if self._subject is empty then this will be a subject of the email
        :param body: if self._body is empty then this will be a body of the email
        """
        msg = MIMEText(self._body or body)
        msg['To'] = self._to
        msg['From'] = self._sender
        msg['Subject'] = self._subject or subject
        try:
            self._send_message(msg)
        except Exception:
            logging.exception('donemail couldn\'t sent an email')

    def _send_message(self, msg):
        try:
            s = smtplib.SMTP(self._smtp_address.host, self._smtp_address.port)
        except Exception:
            raise _SMTPConnectError('can\'t connect to smtp server on {}'.format(
                self._smtp_address))
        try:
            s.sendmail(self._sender, self._to, msg.as_string())
        finally:
            s.quit()


def main(cmd_args=None):
    """
    CLI entry point to donemail. Wait for a pid or run a command.
    """
    parser = argparse.ArgumentParser(prog='donemail')
    subparsers = parser.add_subparsers()
    parent_parser = _get_parent_parser()

    wait_parser = subparsers.add_parser(
        'wait', parents=[parent_parser],
        help='send an email after the process with the specified pid exits')
    wait_parser.add_argument('--poll-interval', type=float, default=1.0,
                             help=_with_default('sleep duration (in seconds) between pid checks'))
    wait_parser.add_argument('pid', type=int, help='pid to wait for')
    wait_parser.set_defaults(func=_wait_pid)

    run_parser = subparsers.add_parser(
        'run', parents=[parent_parser],
        help='run a command and send an email after a command exits')
    run_parser.add_argument('command', help='command to execute')
    run_parser.add_argument('command_args', nargs=argparse.REMAINDER, help='command arguments')
    run_parser.set_defaults(func=_run_command)
    args = parser.parse_args(cmd_args)
    donemail_obj = donemail(to=args.email, body=args.body, subject=args.subject,
                            smtp_address=args.smtp)
    args.func(args, donemail_obj)


def _with_default(help_text):
    return help_text + ' (default: %(default)s)'


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
    """
    Send an email after the process with the specified pid exits.
    See donemail.__init__ for more details on email subject/body.
    """
    if not _pid_exists(args.pid):
        sys.exit('pid {:d} doesn\'t exist'.format(args.pid))
    sys.stderr.write('waiting for pid {:d} to finish\n'.format(args.pid))

    while _pid_exists(args.pid):
        time.sleep(args.poll_interval)
    subject = 'process with pid {:d} exited'.format(args.pid)
    donemail_obj.send_email(subject)


def _run_command(args, donemail_obj):
    """
    Run the specified command and send email after it exits.
    See donemail.__init__ for more details on email subject/body.
    """
    cmd = [args.command] + args.command_args
    status_code = subprocess.call(cmd)
    subject = '`{}` exited with status code {:d}'.format(
        ' '.join(cmd), status_code)
    donemail_obj.send_email(subject)


def _make_call_str(function, args, kwargs):
    args_part = map(repr, args)
    kwargs_part = ['{}={!r}'.format(name, value)
                   for name, value in six.viewitems(kwargs)]
    all_args_part = ', '.join(chain(args_part, kwargs_part))
    return '{}({})'.format(function.__name__, all_args_part)


def _get_default_sender():
    return 'donemail@{}'.format(socket.gethostname())


def _get_parent_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('email', type=_email, help='address to send email to')
    parser.add_argument('--subject', help='subject of the email')
    parser.add_argument('--body', help='body of the email')
    parser.add_argument('--smtp', default=_DEFAULT_SMTP_ADDRESS, type=_address,
                        help=_with_default('host:port of SMTP server'))
    return parser


def _address(host_port):
    try:
        return _Address.from_string(host_port)
    except ValueError as exc:
        six.raise_from(argparse.ArgumentTypeError(exc.message), exc)