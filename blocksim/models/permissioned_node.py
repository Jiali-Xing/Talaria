from collections import namedtuple
from blocksim.models.permissioned_network import Connection, Network
 #Ryan: wasn't importing permissioned network before 7/5
from blocksim.models.chain import Chain
from blocksim.models.node import Node
from blocksim.models.consensus import Consensus
from blocksim.utils import get_received_delay, get_sent_delay, get_latency_delay, time

Envelope = namedtuple('Envelope', 'msg, timestamp, destination, origin')

# Maximum transactions hashes to keep in the known list (prevent DOS)
MAX_KNOWN_TXS = 30000
# Maximum block hashes to keep in the known list (prevent DOS)
MAX_KNOWN_BLOCKS = 1024


class PermNode(Node):
    def __init__(self,
                 env,
                 network: Network,
                 location: str,
                 address: str,
                 chain: Chain,
                 consensus: Consensus,
                 is_authority: bool):

        super().__init__(env, network, location, address, chain, consensus)
        # self.verbose = verbose
        # self.env = env
        # self.network = network
        # self.location = location
        # self.address = address
        # self.chain = chain
        # self.consensus = consensus
        # self.active_sessions = {}
        # self.connecting = None
        # Join the node to the network
        # self.network.add_node(self)
        # Set the monitor to count the forks during the simulation
        # key = f'forks_{address}'
        # self.env.data[key] = 0
        
        #Indicate whether the permissioned node is an authority or not
        self.is_authority = is_authority

    def listening_node(self, connection):
        while True:
            # Get the messages from connection
            envelope = yield connection.get()
            origin_loc = envelope.origin.location
            dest_loc = envelope.destination.location
            message_size = envelope.msg['size']
            received_delay = get_received_delay(
                self.env, message_size, origin_loc, dest_loc)
            yield self.env.timeout(received_delay)

            # Monitor the transaction propagation on Ethereum
            if envelope.msg['id'] == 'transactions':
                tx_propagation = self.env.data['tx_propagation'][
                    f'{envelope.origin.address}_{envelope.destination.address}']
                txs = {}
                for tx in envelope.msg['transactions']:
                    initial_time = tx_propagation.get(tx.hash[:8], None)
                    if initial_time is not None:
                        propagation_time = self.env.now - initial_time
                        txs.update({f'{tx.hash[:8]}': propagation_time})
                self.env.data['tx_propagation'][f'{envelope.origin.address}_{envelope.destination.address}'].update(
                    txs)
            # Monitor the block propagation on Ethereum and PBFT
            if envelope.msg['id'] in ('block_bodies', 'pre-prepare'):
                block_propagation = self.env.data['block_propagation'][
                    f'{envelope.origin.address}_{envelope.destination.address}']
                blocks = {}
                for block_hash, _ in envelope.msg['block_bodies'].items():
                    initial_time = block_propagation.get(block_hash[:8], None)
                    if initial_time is not None:
                        propagation_time = self.env.now - initial_time
                        blocks.update({f'{block_hash[:8]}': propagation_time})
                self.env.data['block_propagation'][f'{envelope.origin.address}_{envelope.destination.address}'].update(
                    blocks)

            self._read_envelope(envelope)

    def send(self, destination_address: str, msg):
        if self.address == destination_address:
            return
        node = self.active_sessions[destination_address]
        active_connection = node['connection']
        origin_node = active_connection.origin_node
        destination_node = active_connection.destination_node

        # Perform block validation before sending
        # For Ethereum it performs validation when receives the header:
        if msg['id'] == 'pre-prepare':
            for header in msg['new_blocks']:
                delay = self.consensus.validate_block()
                yield self.env.timeout(delay)
        # For Bitcoin it performs validation when receives the full block:
        if msg['id'] in ('prepare','commit'):
            delay = self.consensus.validate_block()
            yield self.env.timeout(delay)
        # Perform transaction validation before sending
        # For Ethereum:
        if msg['id'] == 'transactions':
            for tx in msg['transactions']:
                delay = self.consensus.validate_transaction()
                yield self.env.timeout(delay)
        # For Bitcoin:
        if msg['id'] == 'tx':
            delay = self.consensus.validate_transaction()
            yield self.env.timeout(delay)

        upload_transmission_delay = get_sent_delay(
            self.env, msg['size'], origin_node.location, destination_node.location)
        yield self.env.timeout(upload_transmission_delay)

        envelope = Envelope(msg, time(self.env), destination_node, origin_node)
        active_connection.put(envelope)

    def broadcast(self, msg):
        # Perform block validation before sending
        # For Ethereum it performs validation when receives the header:
        if msg['id'] == 'pre-prepare':
            for header in msg['new_blocks']:
                delay = self.consensus.validate_block()
                yield self.env.timeout(delay)
        # For Bitcoin it performs validation when receives the full block:
        if msg['id'] in ('prepare', 'commit'):
            delay = self.consensus.validate_block()
            yield self.env.timeout(delay)
        # Perform transaction validation before sending
        # For Ethereum:
        if msg['id'] == 'transactions':
            for tx in msg['transactions']:
                delay = self.consensus.validate_transaction()
                yield self.env.timeout(delay)
        # For Bitcoin:
        if msg['id'] == 'tx':
            delay = self.consensus.validate_transaction()
            yield self.env.timeout(delay)

        """Broadcast a message to all nodes with an active session"""
        for add, node in self.active_sessions.items():
            connection = node['connection']
            origin_node = connection.origin_node
            destination_node = connection.destination_node

            # Monitor the transaction propagation on Ethereum
            if msg['id'] == 'transactions':
                txs = {}
                for tx in msg['transactions']:
                    txs.update({f'{tx.hash[:8]}': self.env.now})
                self.env.data['tx_propagation'][f'{origin_node.address}_{destination_node.address}'].update(
                    txs)
            # Monitor the block propagation on Ethereum
            if msg['id'] in ('new_blocks', 'pre-prepare'):
                blocks = {}
                for block_hash in msg['new_blocks']:
                    blocks.update({f'{block_hash[:8]}': self.env.now})
                self.env.data['block_propagation'][f'{origin_node.address}_{destination_node.address}'].update(
                    blocks)

            upload_transmission_delay = get_sent_delay(
                self.env, msg['size'], origin_node.location, destination_node.location)
            yield self.env.timeout(upload_transmission_delay)
            envelope = Envelope(msg, time(self.env),
                                destination_node, origin_node)
            connection.put(envelope)
            
    def broadcast_to_authorities(self, msg):
        """Broadcast a message to all nodes with an active session"""
        for add, node in self.active_sessions.items():
            
            #Want to test if the node is an authority
            authority_addresses = []
            for auth_node in self.network._list_authority_nodes:
                authority_addresses.append(auth_node.address)
                
            if add in authority_addresses:
            
                connection = node['connection']
                origin_node = connection.origin_node
                destination_node = connection.destination_node

                # Monitor the transaction propagation on Ethereum
                if msg['id'] == 'transactions':
                    txs = {}
                    for tx in msg['transactions']:
                        txs.update({f'{tx.hash[:8]}': self.env.now})
                    self.env.data['tx_propagation'][f'{origin_node.address}_{destination_node.address}'].update(
                    txs)
                    
                # Monitor the block propagation on Ethereum
                if msg['id'] == 'new_blocks' or msg['id'] == 'pre-prepare':
                    blocks = {}
                    for block_hash in msg['new_blocks']:
                        blocks.update({f'{block_hash[:8]}': self.env.now})
                    self.env.data['block_propagation'][f'{origin_node.address}_{destination_node.address}'].update(
                    blocks)

                upload_transmission_delay = get_sent_delay(
                    self.env, msg['size'], origin_node.location, destination_node.location)
                yield self.env.timeout(upload_transmission_delay)
                envelope = Envelope(msg, time(self.env),
                                destination_node, origin_node)
                connection.put(envelope)
                
    def broadcast_to_non_authorities(self, msg):
        """Broadcast a message to all nodes with an active session"""
        for add, node in self.active_sessions.items():
            
            #Want to test if the node is an authority
            authority_addresses = []
            for auth_node in self.network._list_authority_nodes:
                authority_addresses.append(auth_node.address)
                
            if add not in authority_addresses:
            
                connection = node['connection']
                origin_node = connection.origin_node
                destination_node = connection.destination_node

                # Monitor the transaction propagation on PBFT network
                if msg['id'] == 'reply' and self.verbose:
                    print("Reply being sent to " + add)

                upload_transmission_delay = get_sent_delay(
                    self.env, msg['size'], origin_node.location, destination_node.location)
                yield self.env.timeout(upload_transmission_delay)
                envelope = Envelope(msg, time(self.env),
                                destination_node, origin_node)
                connection.put(envelope)
            

