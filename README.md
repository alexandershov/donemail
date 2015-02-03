## What is it?
Donemail sends an email to the specified address when some 
function/code/script finishes execution.

## Install
```shell
git clone https://github.com/alexandershov/donemail
cd donemail && python setup.py install
```

## Usage
As a decorator
```python
from donemail import donemail

@donemail('test@example.com')
def long_running_function():
    sleep(10)
```
    
As a context manager:
```python
from donemail import donemail

with donemail('test@example.com'):
    sleep(10)
```

In command line:
```shell
donemail test@example.com sleep 10
```

or:
```shell
# send email when pid 123 finishes
donemail --pid 123 test@example.com
```