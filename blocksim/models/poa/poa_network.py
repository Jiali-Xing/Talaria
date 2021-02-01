from datetime import datetime
from blocksim.utils import get_random_values, time, get_latency_delay
from blocksim.models.permissioned_network import PermissionedNetwork


class PoANetwork(PermissionedNetwork):
    def __init__(self, env, name):
        super().__init__(env, name)

    def start_heartbeat(self):
        self._init_lists()
        empty_block = 0
        while True:
            time_between_blocks = round(get_random_values(
                self.env.delays['time_between_blocks_seconds'])[0], 2)
            yield self.env.timeout(time_between_blocks)
            # Ryan: Implement new block selection process here
            selected_node = self._list_authority_nodes[self.authority_index % len(self._list_authority_nodes)]
            if self.verbose:
                print('If the signer is in-turn, wait for the exact time to arrive, ' +
                  'sign and broadcast immediately, at %d' % self.env.now)
            tx_left = self._build_new_block(selected_node)
            self.authority_index = self.authority_index + 1

            # If we have seven consecutive empty block, stop.
            if not tx_left:
                empty_block += 1
                if empty_block >= 4:
                    break
            else:
                empty_block = 0

        self.env.data['end_simulation_time'] = datetime.utcfromtimestamp(self.env.now).strftime('%m-%d %H:%M:%S')
