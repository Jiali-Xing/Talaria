import simpy
from datetime import datetime
from simpy import Store
from blocksim.utils import get_random_values, time, get_latency_delay
from random import random
from enum import Enum


# Ryan: Use this enum to be able to extensively configure different types of 'maliciousness'
class MaliciousModel(Enum):
    NOT_MALICIOUS = 0
    ACTIVE = 1
    PASSIVE = 2


class Network:
    def __init__(self, env, name, verbose=False):
        self.verbose = verbose
        self.env = env
        self.name = name
        self.blockchain = self.env.config['blockchain']
        self._nodes = {}
        self._list_nodes = []
        self._list_authority_nodes = []  # Want to keep track of which nodes are authorities
        self.out_of_turn_block = False  # Jiali: specify whether to simulate concurrent/out-of-turn block propose.
        self.view = 0  # Ryan: replace authority_index with view, for terminology, and because we are no longer
        # directly iterating through the list of authorities, only when the current leader goes down
        self.f = 0  # Just so you can see that max faulty nodes is a parameter of the network, it's initialized below
        self.checkpoint_size = 1 #How many blocks before you take a checkpoint, assuming seqno is per block
        self.checkpoint_delay = 10
        self.validation_delay = 0.1

    def get_node(self, address):
        return self._nodes.get(address)

    def add_node(self, node):
        self._nodes[node.address] = node
    
    def _init_lists(self):
        for add, node in self._nodes.items():
            self._list_nodes.append(node)
            if node.is_authority:  # Put the authority nodes in the authority node list
                self._list_authority_nodes.append(node)

    def start_pbft_heartbeat(self):
        """ The "heartbeat" frequency of any blockchain network based on PoW is time difference
        between blocks. With this function we simulate the network heartbeat frequency.

        During all the simulation, between time intervals (corresponding to the time between blocks)
        its chosen 1 or 2 nodes to broadcast a candidate block.

        We choose 2 nodes, when we want to simulate an orphan block situation.

        A fork due to orphan blocks occurs when there are two equally or nearly equally
        valid candidates for the next block of data in the blockchain.  This event can occur
        when the two blocks are found close in time, and are submitted to the network at different “ends”

        Each node has a corresponding hashrate. The greater the hashrate, the greater the
        probability of the node being chosen.
        """
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
                if empty_block >= 8:
                    break
            else:
                empty_block = 0

            self.env.data['end_simulation_time'] = datetime.utcfromtimestamp(self.env.now).strftime('%m-%d %H:%M:%S')

            if self.out_of_turn_block:
                # Jiali: Assume there are n number of authorities able to propose block
                # I try to model the out of turn leader, not successful yet
                n = 5
                out_of_turn_authority = []
                for leader in range(n):
                    out_of_turn_authority.append(
                        self._list_authority_nodes[(self.view + leader) % len(self._list_authority_nodes)]
                    )
                if self.verbose:
                    print('If the signer is out-of-turn, delay signing by rand(SIGNER_COUNT * 500ms)')
                for node in out_of_turn_authority:
                    self.env.process(self._delay_out_turn_signing(node, n))


    def start_poa_heartbeat(self):
        """ The "heartbeat" frequency of any blockchain network based on PoW is time difference
        between blocks. With this function we simulate the network heartbeat frequency.

        During all the simulation, between time intervals (corresponding to the time between blocks)
        its chosen 1 or 2 nodes to broadcast a candidate block.

        We choose 2 nodes, when we want to simulate an orphan block situation.

        A fork due to orphan blocks occurs when there are two equally or nearly equally
        valid candidates for the next block of data in the blockchain.  This event can occur
        when the two blocks are found close in time, and are submitted to the network at different “ends”

        Each node has a corresponding hashrate. The greater the hashrate, the greater the
        probability of the node being chosen.
        """
        self._init_lists()
        # tx_left = True
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

            if self.out_of_turn_block:
                # Jiali: Assume there are n number of authorities able to propose block
                # I try to model the out of turn leader, not successful yet
                n = 5
                out_of_turn_authority = []
                for leader in range(n):
                    out_of_turn_authority.append(
                        self._list_authority_nodes[(self.view + leader) % len(self._list_authority_nodes)]
                    )
                if self.verbose:
                    print('If the signer is out-of-turn, delay signing by rand(SIGNER_COUNT * 500ms)')
                for node in out_of_turn_authority:
                    self.env.process(self._delay_out_turn_signing(node, n))


    def start_heartbeat(self):
        if self.blockchain == "poa":
            return self.start_poa_heartbeat()
        elif self.blockchain == "pbft":
            return self.start_pbft_heartbeat()
        else:
            raise Exception("Model not available.")

    def _delay_out_turn_signing(self, node, n):
        delay = random() * n / 2
        out_turn_block_propose = simpy.events.Timeout(self.env, delay=delay, value=delay)
        delayed_time = yield out_turn_block_propose
        self._build_new_block(node)
        if self.verbose:
            print('now=%d, out-of-turn node %s proposes after delayed_time=%d' % (self.env.now, node, delayed_time))

    def _build_new_block(self, node):
        if self.verbose:
            print(
                f'Network at {time(self.env)}: Node {node.address} selected to broadcast his candidate block')
        # Give orders to the selected node to broadcast his candidate block
        return node.build_new_block()


class Connection:
    """This class represents the propagation through a Connection."""

    def __init__(self, env, origin_node, destination_node, verbose=False):
        self.verbose = verbose
        self.env = env
        self.store = Store(env)
        self.origin_node = origin_node
        self.destination_node = destination_node

    def latency(self, envelope):
        latency_delay = get_latency_delay(
            self.env, self.origin_node.location, self.destination_node.location)
        yield self.env.timeout(latency_delay)
        self.store.put(envelope)

    def put(self, envelope):
        if self.verbose:
            print(
                f'{envelope.origin.address} at {envelope.timestamp}: Message (ID: {envelope.msg["id"]}) sent with {envelope.msg["size"]} MB with a destination: {envelope.destination.address}')
        self.env.process(self.latency(envelope))

    def get(self):
        return self.store.get()
