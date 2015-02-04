## What is it?
Donemail sends you an email when some function/code/script completes.

## Install
```shell
git clone https://github.com/alexandershov/donemail
cd donemail && python setup.py install
```

## Usage
You need a SMTP server running on port 25.

As a decorator
```python
from donemail import donemail

@donemail('bob@example.com')
def long_running_function():
    sleep(10)
```
    
As a context manager:
```python
from donemail import donemail

with donemail('bob@example.com'):
    sleep(10)
```

In command line:
```shell
donemail bob@example.com sleep 10
```

or:
```shell
# send email when pid 123 finishes
donemail --pid 123 bob@example.com
```