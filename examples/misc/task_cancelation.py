#!/usr/bin/env python3

import os
import time

import radical.pilot as rp


# ------------------------------------------------------------------------------
#
if __name__ == '__main__':

    # demonstrate task cancelation during execution: we start some tasks, then
    # wait for some to finish, and cancel some more, both tasks currently
    # executing and tasks still pending for execution

    session = rp.Session()

    try:
        pmgr    = rp.PilotManager(session=session)
        pd_init = {'resource'      : 'local.localhost',
                   'runtime'       : 60,
                   'cores'         :  8
                  }
        pdesc = rp.ComputePilotDescription(pd_init)
        pilot = pmgr.submit_pilots(pdesc)
        umgr  = rp.UnitManager(session=session)
        umgr.add_pilots(pilot)

        # wait until pilot is active to have somewhat sensible timings below
        pilot.wait(rp.PMGR_ACTIVE)
        print('pilot state: %s' % pilot.state)

        # submit 32 tasks, each running for 120 seconds.  We have 8 cores, so the
        # tasks will run in 8 batches at a time, in a total of 4 batches (aka
        # generations).
        t_start = time.time()
        cuds    = list()
        for _ in range(32):

            cud = rp.ComputeUnitDescription()
            cud.executable = '%s/examples/hello_rp.sh' % os.getcwd()
            cud.arguments  = [120]
            cuds.append(cud)

        tasks = umgr.submit_units(cuds)

        # wait until 8 tasks are done (16 cores: should take about 120 seconds
        while True:
            time.sleep(1)
            states = [t.state for t in tasks]
            count  =  states.count(rp.DONE)
            print('%d total  %d DONE' % (len(states), count))
            if count >= 8:
                break

        t_gen_1 = time.time()

        # cancel 12 tasks which are not in the set of DONE tasks above.  That
        # should request cancellation for a mix of currently running and still
        # pending tasks (8 are DONE, 8 are running right now, 16 are pending.
        done_uids   = [t.uid for t in tasks if t.state == rp.DONE]
        cancel_uids = [t.uid for t in tasks if t.uid not in done_uids]
        cancel_uids = cancel_uids[:12]
        n_canceled  = len(cancel_uids)

        umgr.cancel_units(uids=cancel_uids)

      # # this would also work:
      # n_canceled = 0
      # for t in tasks:
      #     if t.uid in done_uids: continue
      #     if n_canceled == 12  : break
      #     t.cancel()
      #     n_canceled += 1

        t_cancel = time.time()

        # 4 tasks should be left which fit on the available core, and we should
        # wait for another 120 seconds or so
        umgr.wait_units()
        t_done = time.time()

        # print some statistocs
        states = [t.state for t in tasks]
        print('states:')
        for s in [rp.DONE, rp.FAILED, rp.CANCELED]:
            print ('  %-10s: %3d' % (s, states.count(s)))
        print('  canceled: %d tasks' % n_canceled)

        print('times:')
        print('  gen 1 : %10.1f sec (exp: 120 sec)' % (t_gen_1  - t_start))
        print('  cancel: %10.1f sec (exp:   0 sec)' % (t_cancel - t_gen_1))
        print('  gen x : %10.1f sec (exp: 120 sec)' % (t_done   - t_cancel))

        session.close(download=True)

    except:
        session.close(download=False)
        raise


# ------------------------------------------------------------------------------
