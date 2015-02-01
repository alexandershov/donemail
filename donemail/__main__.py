import subprocess
import sys

from donemail import send_email


# TODO: allow to watch pid to completion
def main():
    # TODO: check sys.argv and probably parse args with argparse
    to = sys.argv[1]
    subprocess.call(sys.argv[2:])
    send_email('test@example.com', 'donemail test', 'It works!')


main()

