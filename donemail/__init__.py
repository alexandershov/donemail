from email.mime.text import MIMEText
from functools import wraps
import smtplib

# TODO: add tests


def send_email(to, subject, message):
    # TODO: send real email
    print('sending email to={}, subject={}, message={}'.format(
        to, subject, message
    ))
    return
    sender = 'donemail@example.com'
    msg = MIMEText(message)
    msg['To'] = to
    msg['From'] = sender
    msg['Subject'] = subject
    s = smtplib.SMTP('localhost')
    s.sendmail(sender, [to], msg.as_string())
    s.quit()


class donemail(object):
    # TODO: add subject and message args
    def __init__(self, to):
        self._to = to

    def __call__(self, function):
        @wraps(function)
        def donemail_function(*args, **kwargs):
            result = function(*args, **kwargs)
            # TODO: send function arguments and result
            # TODO: catch, send, and reraise exceptions
            send_email(self._to, '{} done'.format(function.__name__), '')
            return result

        return donemail_function

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: send exception info
        send_email(self._to, 'done', '')
