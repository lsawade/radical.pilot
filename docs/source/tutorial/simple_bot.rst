.. _chapter_tutorial_simple_bot:

*******************
Simple Bag-of-Tasks
*******************

.. You might be wondering how to create your own RADICAL-Pilot script or how
.. RADICAL-Pilot can be useful for your needs. Before delving into the remote job
.. and data submission capabilities of RADICAL-Pilot, it is important to
.. understand the basics.

The simplest usage of a pilot system is to collectively submit and execute
multiple identical tasks (a 'Bag of Tasks' or 'BoT') either locally or on a
remote high-performance computing (HPC) machine. In this way, a pilot system
allows to code and execute parameter sweep or ensemble simulation
applications.

We create an example which submits `N` tasks using RADICAL-Pilot. All tasks
are identical, except that each task outputs its unique ID. RADICAL-Pilot (1)
submits one container job called `pilot` to the queuing system of the HPC
machine and, when this pilot becomes active, (2) it schedules and execute the
N tasks on the resources of that pilot. In this way, each task is not
individually submitted as a job to the queuing system of the HPC machine.

.. This type of run is very useful if you are running many jobs using the same
.. executable (but perhaps with different input files).

------------
Preparation
------------

Download the file ``simple_bot.py`` with the following command:

.. code-block:: bash

    curl -O https://raw.githubusercontent.com/radical-cybertools/radical.pilot/master/examples/docs/simple_bot.py


Open the file ``simple_bot.py`` with your favorite editor. The example should
work right out of the box on your local machine. However, if you want to run
it on a remote HPC machine, look for the sections marked:

.. code-block:: python

        # ----- CHANGE THIS -- CHANGE THIS -- CHANGE THIS -- CHANGE THIS ------

and change the code below that line, according to the instructions in the comments.

.. Let's discuss the above example. We define our executable as "/bin/echo," the
.. simple UNIX command that writes arguments to standard output. Next, we need to
.. provide the arguments. In this case, "I am Task number $CU_NO," would correspond
.. to typing ``/bin/echo 'I am task number $CU_NO'`` on command line.  ``$CU_NO``
.. is an environment variable, so we will need to provide a value for it, as is
.. done on the next line: ``{'CU_NO': i}``. Note that this block of code is in
.. a python for loop, therefore, ``i`` corresponds to what iteration we are on.
.. This is not a parallel code, echo uses just one core, so we specify ``cores=1``.

---------
Execution
---------

**This assumes you have installed RADICAL-Pilot in a Python virtualenv. You
also need access to a MongoDB server.**

Set the `RADICAL_PILOT_DBURL` environment variable in your shell to the
MongoDB server you want to use, for example:

.. code-block:: bash

        export RADICAL_PILOT_DBURL=mongodb://<user>:<pass>@<host>:<port>/<database>

If RADICAL-Pilot is installed and the MongoDB URL is set, you should be good
to run your program (the database is created on the fly):

.. code-block:: bash

    python simple_bot.py

The output should look something like this:

.. code-block:: none

    Initializing Pilot Manager ...
    Submitting Pilot to Pilot Manager ...
    Initializing Task Manager ...
    Registering Pilot with Task Manager ...
    Submit Tasks to Task Manager ...
    Waiting for CUs to complete ...
    ...
    Waiting for CUs to complete ...
    All CUs completed!
    Closed session, exiting now ...


----------------------
Logging and Debugging
----------------------

Since working with distributed systems is inherently complex and much of the
complexity is hidden within RADICAL-Pilot, it is necessary to do internal
logging. By default, logging output is disabled, but if something goes wrong
or if you're just curious, you can enable the logging output by setting the
environment variable ``RADICAL_PILOT_LOG_LVL`` to a value between CRITICAL
(print only critical messages) and DEBUG (print all messages).  For more
details on logging, see under 'Debugging' in chapter
:ref:`chapter_developers`.

Give it a try with the above example:

.. code-block:: bash

  RADICAL_PILOT_LOG_LVL=DEBUG python simple_bot.py
