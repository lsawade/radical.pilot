# pylint: disable=protected-access, unused-argument, no-value-for-parameter

__copyright__ = "Copyright 2020, http://radical.rutgers.edu"
__license__   = "MIT"

from unittest import TestCase
from unittest import mock

from radical.pilot.agent import Agent_0


# ------------------------------------------------------------------------------
#
class TestComponent(TestCase):

    # --------------------------------------------------------------------------
    #
    @mock.patch.object(Agent_0, '__init__', return_value=None)
    def test_check_control(self, mocked_init):

        global_control = []

        def _publish_side_effect(publish_type, cmd):
            nonlocal global_control
            global_control.append((publish_type, cmd))

        def _prepare_env_side_effect(env_id, spec):
            return (env_id, spec)

        agent_cmp = Agent_0(None, None)
        agent_cmp.publish = mock.MagicMock(side_effect=_publish_side_effect)
        agent_cmp._prepare_env = mock.MagicMock(
                                           side_effect=_prepare_env_side_effect)

        msg = {'cmd': 'test',
               'arg': {'uid': 'rpc.0000',
                       'rpc': 'bye'}
              }

        self.assertTrue(agent_cmp._check_control(None, msg))
        self.assertEqual(global_control, [])

        msg = {'cmd': 'rpc_req',
               'arg': {'uid': 'rpc.0000',
                       'rpc': 'bye'}
              }
        self.assertTrue(agent_cmp._check_control(None, msg))
        self.assertEqual(global_control, [])

        msg = {'cmd': 'rpc_req',
               'arg': {'uid': 'rpc.0000',
                       'rpc': 'hello'}
              }
        self.assertTrue(agent_cmp._check_control(None, msg))
        self.assertIn(global_control[0], [('control_pubsub',
                                           {'cmd': 'rpc_res',
                                            'arg': {'uid': 'rpc.0000',
                                                    'err': "KeyError('arg')",
                                                    'ret': None}
                                           }),
                                           ('control_pubsub',
                                           {'cmd': 'rpc_res',
                                            'arg': {'uid': 'rpc.0000',
                                                    'err': "KeyError('arg',)",
                                                    'ret': None}
                                           })])

        msg = {'cmd': 'rpc_req',
               'arg': {'uid': 'rpc.0000',
                       'rpc': 'hello',
                       'arg': ['World']}
              }
        self.assertTrue(agent_cmp._check_control(None, msg))
        self.assertEqual(global_control[1], ('control_pubsub',
                                             {'cmd': 'rpc_res',
                                              'arg': {'uid': 'rpc.0000',
                                                      'err': None,
                                                      'ret': 'hello World'}
                                             }))

        msg = {'cmd': 'rpc_req',
               'arg': {'uid': 'rpc.0000',
                       'rpc': 'prep_env',
                       'arg': {'env_id'  : 'radical',
                               'env_spec': 'spec'}
                      }
              }
        self.assertTrue(agent_cmp._check_control(None, msg))
        self.assertEqual(global_control[2], ('control_pubsub',
                                             {'cmd': 'rpc_res',
                                              'arg': {'uid': 'rpc.0000',
                                                      'err': None,
                                                      'ret': ('radical', 'spec')}
                                             }))

# ------------------------------------------------------------------------------


if __name__ == '__main__':

    tc = TestComponent()
    tc.test_check_control()
