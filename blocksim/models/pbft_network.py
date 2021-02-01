import simpy
from datetime import datetime
from simpy import Store
from blocksim.utils import get_random_values, time, get_latency_delay
from random import random
from enum import Enum
from blocksim.models.permissioned_network import PermissionedNetwork


# Ryan: Use this enum to be able to extensively configure different types of 'maliciousness'
class MaliciousModel(Enum):
    NOT_MALICIOUS = 0
    ACTIVE = 1
    PASSIVE = 2


class PBFTNetwork(PermissionedNetwork):
    def __init__(self, env, name):
        super().__init__(env, name)

        self.view = 0  # Ryan: replace authority_index with view, for terminology, and because we are no longer
        # directly iterating through the list of authorities, only when the current leader goes down
        self.f = 0  # Just so you can see that max faulty nodes is a parameter of the network, it's initialized below
        self.checkpoint_size = 1 #How many blocks before you take a checkpoint, assuming seqno is per block
        self.checkpoint_delay = 10
        self.validation_delay = 0.1

    def start_pbft_heartbeat(self):
        self._init_lists()
        empty_block = 0

        # (Ryan) Initialize max # of faulty nodes after lists have been initialized
        # Casting the divison result to an int is equivalent to applying floor function
        self.f = int(len(self._list_authority_nodes)/3)
        
        while True:
            time_between_blocks = round(get_random_values(
                self.env.delays['time_between_blocks_seconds'])[0], 2)
            yield self.env.timeout(time_between_blocks)

            # Ryan: Implement new block selection process here (updated for PBFT 7/3!)
            # Bugfix: IndexError: list index out of range, bugfix done
            selected_node = self._list_authority_nodes[self.view % len(self._list_authority_nodes)]
            if self.verbose:
                print(f'If the signer is in-turn, wait for the exact time to arrive, sign and broadcast immediately, at {time(self.env)}.')

            tx_left = self._build_new_block(selected_node)

            # If we have seven consecutive empty block, stop.
            if not tx_left:
                empty_block += 1
                # if empty_block >= 8:
                #     break
            else:
                empty_block = 0

            self.env.data['end_simulation_time'] = datetime.utcfromtimestamp(self.env.now).strftime('%m-%d %H:%M:%S')

    def start_poa_heartbeat(self):
        self._init_lists()
        empty_block = 0

        while True:
            time_between_blocks = round(get_random_values(
                self.env.delays['time_between_blocks_seconds'])[0], 2)
            yield self.env.timeout(time_between_blocks)

            # Ryan: Implement new block selection process here
            selected_node = self._list_authority_nodes[self.view % len(self._list_authority_nodes)]
            if self.verbose:
                print('If the signer is in-turn, wait for the exact time to arrive, ' +
                  'sign and broadcast immediately, at %d' % self.env.now)
            tx_left = self._build_new_block(selected_node)
            self.view = self.view + 1

            # If we have three consecutive empty block, stop.
            if not tx_left:
                empty_block += 1
                if empty_block >= 3:
                    break
            else:
                empty_block = 0

            self.env.data['end_simulation_time'] = datetime.utcfromtimestamp(self.env.now).strftime('%m-%d %H:%M:%S')

    def start_heartbeat(self):
        if self.blockchain == "poa":
            return self.start_poa_heartbeat()
        elif self.blockchain == "pbft":
            return self.start_pbft_heartbeat()
        else:
            raise Exception("Model not available.")

