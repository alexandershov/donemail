.. image:: https://travis-ci.org/alexandershov/donemail.svg?branch=master
   :target: https://travis-ci.org/alexandershov/donemail

What is it?
===========
Donemail sends you an email when some process/command/function/code completes.

Install
=======
.. code-block:: shell

    pip install donemail

Usage
=====
You need a SMTP server running on port 25.

In the command line:

.. code-block:: shell

   # run command 'sleep 10' and send an email after it exits
   donemail run bob@example.com sleep 10

or:

.. code-block:: shell

   # send an email when process with pid 123 exits
   donemail wait bob@example.com 123

As a decorator:

.. code-block:: python

   from donemail import donemail

   # send an email after each long_running_function() call
   @donemail('bob@example.com')
   def long_running_function():
       sleep(10)

As a context manager:

.. code-block:: python

   from donemail import donemail

   # send an email after sleep(10) completes
   with donemail('bob@example.com'):
       sleep(10)
