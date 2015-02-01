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
python -m donemail test@example.com sleep 10
```