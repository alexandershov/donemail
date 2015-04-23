.. image:: https://travis-ci.org/alexandershov/donemail.svg?branch=master
   :target: https://travis-ci.org/alexandershov/donemail

What is it?
===========
Donemail sends you an email when some function/code/script completes.

Install
=======
.. code-block:: shell

    pip install donemail

Usage
=====
You need a SMTP server running on port 25.

As a decorator:

.. code-block:: python

   from donemail import donemail

   @donemail('bob@example.com')
   def long_running_function():
       sleep(10)


As a context manager:

.. code-block:: python

   from donemail import donemail

   with donemail('bob@example.com'):
       sleep(10)


In the command line:

.. code-block:: shell

   donemail run bob@example.com sleep 10

or:

.. code-block:: shell

   # send email when pid 123 finishes
   donemail wait bob@example.com 123
