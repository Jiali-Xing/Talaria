import numpy as np
from datetime import datetime
from blocksim.utils import get_random_values, time, get_latency_delay
from blocksim.models.permissioned_network import PermissionedNetwork


class PoETNetwork(PermissionedNetwork):
    def __init__(self, env, name):
        super().__init__(env, name)

    def start_heartbeat(self):
        self._init_lists()
        empty_block = 0
        while True:
            exponential_param = {
                "name": "expon",
                "parameters": "(0, 10)"
            }
            # for authority in self._list_authority_nodes:
            time_between_blocks = get_random_values(exponential_param, len(self._list_authority_nodes))
            yield self.env.timeout(np.min(time_between_blocks))
            selected_node = self._list_authority_nodes[np.argmin(time_between_blocks)]
            if self.verbose:
                print('If the signer is in-turn, wait for the exact time to arrive, ' +
                  'sign and broadcast immediately, at %d' % self.env.now)
            tx_left = self._build_new_block(selected_node)

            # If we have seven consecutive empty block, stop.
            if not tx_left:
                empty_block += 1
                if empty_block >= 4:
                    break
            else:
                empty_block = 0

        self.env.data['end_simulation_time'] = datetime.utcfromtimestamp(self.env.now).strftime('%m-%d %H:%M:%S')
