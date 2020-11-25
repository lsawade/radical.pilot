"""RADICAL-Executor builds on the RADICAL-Pilot/ParSL
"""
import os
import re
import shlex
import parsl
import queue
import pickle
import logging
import typeguard
import threading
import inspect

import radical.pilot as rp
import radical.utils as ru

from concurrent.futures import Future

from multiprocessing import Process, Queue
from typing import Any, Dict, List, Optional, Tuple, Union

from ipyparallel.serialize import unpack_apply_message  # pack_apply_message
from ipyparallel.serialize import pack_apply_message   # unpack_apply_message
from ipyparallel.serialize import deserialize_object  # deserialize_object

from parsl.app.errors import RemoteExceptionWrapper
from parsl.executors.errors import *
from parsl.executors.base import ParslExecutor

from parsl.utils import RepresentationMixin
from parsl.providers import LocalProvider



class RADICALExecutor(ParslExecutor, RepresentationMixin):
    """Executor designed for cluster-scale

    The RADICALExecutor system has the following components:

      1. "start" resposnible for creating the RADICAL-executor session and pilot.
      2. "submit" resposnible for translating and submiting ParSL tasks the RADICAL-executor.
      3. "shut_down"  resposnible for shutting down the RADICAL-executor components.

    Here is a diagram

    .. code:: python
                                                                                                                     RADICAL Executor
        ----------------------------------------------------------------------------------------------------------------------------------------------------
                        ParSL API                          |         ParSL DFK/dflow               |      Task Translator      |     RP-Client/Unit-Manager
        ---------------------------------------------------|---------------------------------------|---------------------------|----------------------------                                                     
                                                           |                                       |                           |
         parsl_tasks_description ------>  ParSL_tasks{}----+-> Dep. check ------> ParSL_tasks{} <--+--> ParSL Task/Tasks desc. | umgr.submit_units(RP_units)
                                           +api.submit     | Data management          +dfk.submit  |             |             |
                                                           |                                       |             v             |
                                                           |                                       |     RP Unit/Units desc. --+->   
        ----------------------------------------------------------------------------------------------------------------------------------------------------
    """        
  
    @typeguard.typechecked
    def __init__(self,
                 label: str = 'RADICALExecutor',
                 resource: str = None,
                 login_method: str = None,                  # Specify the connection protocol SSH/GISSH/local
                 walltime: int = None,
                 tasks_pre_exec: Optional[str] = None,      # Specify any requirements that this task needs to run
                 managed: bool = True,
                 max_tasks: Union[int, float] = float('inf'),
                 worker_logdir_root: Optional[str] = ".",
                 partition : Optional[str] = " ",
                 project: Optional[str] = " ",):

        self.logger = ru.Logger(name='radical.pilot.parsl.executor', level='DEBUG')
        self.report = ru.Reporter(name='radical.pilot')  

        self.report.title('RP version %s :' % rp.version)
        self.report.header("Initializing RADICALExecutor with ParSL version %s :" % parsl.__version__)
        self.label = label
        self.project = project
        self.resource = resource
        self.login_method = login_method
        self.partition = partition
        self.walltime = walltime
        self.tasks = list()
        self.future_tasks = {}
        self.tasks_pre_exec = tasks_pre_exec
        self.managed = managed
        self.max_tasks = max_tasks
        self._task_counter = 0
        self.run_dir = '.'
        self.worker_logdir_root = worker_logdir_root
        self.session = rp.Session(uid=ru.generate_id('parsl.radical_executor.session',
                       mode=ru.ID_PRIVATE))
        self.pmgr    = rp.PilotManager(session=self.session)
        self.umgr    = rp.UnitManager(session=self.session)
      
        #self._executor_bad_state = threading.Event()
        #self._executor_exception = None

    def unit_state_cb(self, unit, state):

        """
        Update the state of Parsl Future tasks
        Based on RP unit state
        """
        task = self.future_tasks[unit.name]
        if state == rp.DONE:
            task.set_result(unit.stdout)
        elif state == rp.FAILED:
            task.set_result(unit.stderr)


    def start(self):
        """Create the Pilot process and pass it.
        """
        if self.resource is None : self.logger.error("specify remoute or local resource")


        else : pd_init = {'resource'      : self.resource,
                          'runtime'       : self.walltime,
                          'exit_on_error' : True,
                          'project'       : self.project,
                          'queue'         : self.partition,
                          'access_schema' : self.login_method,
                          'cores'         : 1*self.max_tasks,
                          'gpus'          : 0,}

        pdesc = rp.ComputePilotDescription(pd_init)
        pilot = self.pmgr.submit_pilots(pdesc)
        self.umgr.add_pilots(pilot)

        return True


    def task_translate(self, func, args, kwargs):

        task_type = inspect.getsource(func).split('\n')[0]
        
        if task_type.startswith('@bash_app'):
            source_code = inspect.getsource(func).split('\n')[2].split('return')[1]
            temp        = ' '.join(shlex.quote(arg) for arg in (shlex.split(source_code,
                                                                comments=True,posix=True)))
            task_exe    = re.findall(r"'(.*?).format",temp,re.DOTALL)[0]
            cu = {"source_code": task_exe,
                  "name"  : func.__name__,
                  "args"  : None,
                  "kwargs": kwargs}
            #self.report.header(inspect.getsource(func))
            #self.report.header('Bash task name %s ' %(cu['name'])) 
            #self.report.header('Bash task exe %s ' %(task_exe))           
            #self.report.header('Bash task args  %s ' %(cu['args']))
            #self.report.header('Bash task kwargs  %s ' %(cu['kwargs']))

        elif task_type.startswith('@python_app'):

            task_pre_exec = inspect.getsource(func).split('\n')[2]
            task_exe      = inspect.getsource(func).split('\n')[3]
            cu = {"source_code": task_exe,
                  "name"  : func.__name__,
                  "args"  : None,
                  "pre_exec": task_pre_exec,
                  "kwargs": kwargs}
            #report.header('python task %s ' %(inspect.getsource(func)))
            #report.header('python task pre_exec %s ' %(cu['pre_exec']))
            #report.header('python task name %s ' %(cu['name']))
            #report.header('Python task exe %s ' %(task_exe))
            #report.header('python task kwargs  %s ' %(cu['args']))

        else:
            pass
    
        return cu

        
    def submit(self, func, *args, **kwargs):
        """Submits task/tasks to RADICAL unit_manager.

        Args:
            - func (callable) : Callable function
            - *args (list) : List of arbitrary positional arguments.

        Kwargs:
            - **kwargs (dict) : A dictionary of arbitrary keyword args for func.
        """
        self.logger.debug("Got a task from the parsl.dataflow.dflow")

        self._task_counter += 1
        task_id = str(self._task_counter)
        self.future_tasks[task_id] = Future()
        tu = self.task_translate(func, args, kwargs)

        try:
            self.umgr.register_callback(self.unit_state_cb) 
            self.report.progress_tgt(self._task_counter, label='create')

            task                  = rp.ComputeUnitDescription()
            task.name             = task_id
            task.executable       = tu['source_code'] if 'exe' not in tu['kwargs'] else "{0} {1}".format(tu['kwargs']['exe'],
                                                                                                         tu['source_code'])
                                                       
            task.arguments        = tu['args']
            task.pre_exec         = self.tasks_pre_exec
            task.cpu_processes    = tu['kwargs']['nproc']
            task.cpu_process_type = None if 'ptype' not in tu['kwargs'] else tu['kwargs']['ptype']
            task.cpu_threads      = 1    if 'nthrd' not in tu['kwargs'] else tu['kwargs']['nthrd']
            self.report.progress()
            self.umgr.submit_units(task)
            
        
        except Exception as e:
            # Something unexpected happened in the pilot code above
            self.report.error('caught Exception: %s\n' % e)
            ru.print_exception_trace()
            raise

        except (KeyboardInterrupt, SystemExit):
            ru.print_exception_trace()
            self.report.warn('exit requested\n')

        return self.future_tasks[task_id]
    

    def shutdown(self, hub=True, targets='all', block=False):
        """Shutdown the executor, including all RADICAL-Pilot components."""
        self.report.progress_done()
        self.session.close(download=True)
        self.report.header("Attempting RADICALExecutor shutdown")

        return True

    @property
    def scaling_enabled(self) -> bool:
        return False

    def scale_in(self, blocks: int):
        raise NotImplementedError

    def scale_out(self, blocks: int):
        raise NotImplementedError
