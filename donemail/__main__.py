import os
import subprocess
import sys
import time

from donemail import send_email


# TODO: allow to watch pid to completion
def main():
    # TODO: check sys.argv and parse args with argparse
    to = sys.argv[1]
    if sys.argv[2].isdigit():
        pid = int(sys.argv[2])
        if not pid_exists(pid):
            sys.exit('pid {:d} doesn\'t exist'.format(pid))
        sys.stderr.write('waiting for pid {:d} to finish\n'.format(pid))
        wait_pid(pid)
        subject = 'pid {:d} exited'.format(pid)
    else:
        # TODO: send stdin and stderr if status_code != 0
        status_code = subprocess.call(sys.argv[2:])
        subject = '{} exited with status_code = {:d}'.format(
            ' '.join(sys.argv[2:]), status_code)
    send_email(to, subject, '')


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


main()

