
__copyright__ = "Copyright 2016, http://radical.rutgers.edu"
__license__   = "MIT"


import os
import radical.utils as ru

from .base import LaunchMethod


# ------------------------------------------------------------------------------
#
class Runjob(LaunchMethod):

    # --------------------------------------------------------------------------
    #
    def __init__(self, cfg, session):

        LaunchMethod.__init__(self, cfg, session)


    # --------------------------------------------------------------------------
    #
    def _configure(self):

        # runjob: job launcher for IBM BG/Q systems, e.g. Joule
        self.launch_command = ru.which('runjob')

        raise NotImplementedError('RUNJOB LaunchMethod still coupled to '
                                  'scheduler/ResourceManager')


    # --------------------------------------------------------------------------
    #
    def construct_command(self, t, launch_script_hop):

        slots        = t['slots']
        td          = t['description']
        task_exec    = td['executable']
        task_cores   = td.get('cpu_processes', 0) + td.get('gpu_processes', 0)
                                                         # FIXME: handle threads
        task_env     = td.get('environment') or dict()
        task_args    = td.get('arguments')   or list()
        task_argstr  = self._create_arg_string(task_args)

        if  'loadl_bg_block'      not in slots            or \
            'sub_block_shape_str' not in slots            or \
            'corner_node'         not in slots            or \
            'lm_info'             not in slots            or \
            'cores_per_node'      not in slots['lm_info'] or \
            'gpus_per_node'       not in slots['lm_info']    :
            raise RuntimeError('insufficient information to launch via %s: %s'
                              % (self.name, slots))

        cores_per_node      = slots['lm_info']['cores_per_node']
        gpus_per_node       = slots['lm_info']['gpus_per_node']
        loadl_bg_block      = slots['loadl_bg_block']
        sub_block_shape_str = slots['sub_block_shape_str']
        corner_node         = slots['corner_node']

        # FIXME GPU
        if task_cores % cores_per_node:
            msg = "Num cores (%d) is not a multiple of %d!" % (task_cores, cores_per_node)
            self._log.exception(msg)
            raise ValueError(msg)

        # Runjob it is!
        runjob_command = self.launch_command

        # Set the number of tasks/ranks per node
        # TODO: Currently hardcoded, this should be configurable,
        #       but I don't see how, this would be a leaky abstraction.
        # FIXME GPU
        runjob_command += ' --ranks-per-node %d' % min(cores_per_node, task_cores)

        # Run this subjob in the block communicated by LoadLeveler
        runjob_command += ' --block %s'  % loadl_bg_block
        runjob_command += ' --corner %s' % corner_node

        # convert the shape
        runjob_command += ' --shape %s' % sub_block_shape_str

        # runjob needs the full path to the executable
        if os.path.basename(task_exec) == task_exec:
            # Use `which` with back-ticks as the executable,
            # will be expanded in the shell script.
            task_exec = '`which %s`' % task_exec
            # Note: We can't use the expansion from here,
            #       as the pre-execs of the Task aren't run yet!!

        # And finally add the executable and the arguments
        # usage: runjob <runjob flags> : /bin/hostname -f
        runjob_command += ' : %s' % task_exec
        if task_argstr:
            runjob_command += ' %s' % task_argstr

        return runjob_command, None


# ------------------------------------------------------------------------------

