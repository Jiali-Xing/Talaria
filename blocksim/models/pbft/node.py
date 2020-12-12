from collections import namedtuple  # to support envelope finality for viewchanges
from blocksim.models.permissioned_node import Node
from blocksim.models.pbft_network import Network, MaliciousModel
from blocksim.models.chain import Chain
from blocksim.models.consensus import Consensus
from blocksim.models.db import BaseDB
from blocksim.models.permissoned_transaction_queue import TransactionQueue
from blocksim.utils import time, get_random_values
from blocksim.models.block import Block, BlockHeader
from blocksim.models.pbft.message import Message
from collections import defaultdict
from pathlib import Path
from scipy import random
import pickle

Envelope = namedtuple('Envelope', 'msg, timestamp, destination, origin')

class PBFTNode(Node):

    def __init__(self,
                 env,
                 network: Network,
                 location: str,
                 address: str,
                 replica_id, 
                 is_authority=False,
                 is_malicious=MaliciousModel.NOT_MALICIOUS
                 ):
        # Jiali: This function is borrowed from ethereum/node.py, without any change actually.
        # Create the PBFT genesis block and init the chain
        genesis = Block(BlockHeader())
        consensus = Consensus(env)
        chain = Chain(env, self, consensus, genesis, BaseDB())

        self.is_authority = is_authority
        super().__init__(env,
                         network,
                         location,
                         address,
                         chain,
                         consensus,
                         is_authority)
        self.temp_headers = {}
        self.is_malicious = is_malicious
        self.network_message = Message(self)
        if is_authority:
            self.current_view = self.network.view
            self.current_sequence = 0
            # Transaction Queue to store the transactions
            self.transaction_queue = TransactionQueue(
                env, self, self.consensus)
            self.env.process(self._check_timeout())  # When node is initialized, begin periodically checking for timeout
            self.env.process(self._checkpointing())  # When node is initialized, periodically check if a checkpoint should be taken
            
        if self.is_malicious == MaliciousModel.PASSIVE:
            self.drop_probability = 0.4
        
        self._handshaking = env.event()
        self.replica_id = replica_id
        # Jiali: a dict for logging msg/prepare/commit
        self.log = {
            'block': defaultdict(bool),
            'prepare': defaultdict(set),
            'prepared': defaultdict(bool),
            'commit': defaultdict(set),
            'committed': defaultdict(bool),
            'reply': defaultdict(set),
            'viewchange' : defaultdict(list),  # TODO, correct for multiple occurrences
            'checkpoint': defaultdict(set),
            'newview' : defaultdict(set)
        }
        #A dict to store the actual prepare messages.They should be identical
        #per seqno. update when a valid prepare message is received.
        self.preparemsg = {}

        # Ryan: We want to model node failures and view changes...
        self.timedout = False  # Indicate if a node has timed out
        self.timeoutVal = 3  # Some numerical time value for a timeout here
        self.failure = False  # Indicate if a node is down or will somehow act Byzantine
        # self.prevLog = {}  # Keep track of previous log state so node can detect changes to it
        self.currSeqno = 0
        self.lastCheckpoint = 0

    def build_new_block(self):
        """Builds a new candidate block and propagate it to the network

        Jiali: This function is borrowed from bitcoin/node.py, without too much change."""
        if self.is_authority is False:
            raise RuntimeError(f'Node {self.location} is not a authority')

        # Jiali: Assume passive malicious nodes doesn't broadcast blocks either.
        if self.is_malicious == MaliciousModel.PASSIVE:
            drop_message = random.choice([True, False], p=[self.drop_probability, 1 - self.drop_probability])
            if drop_message:
                return True

        block_size = self.env.config['pbft']['block_size_limit_mb']
        transactions_per_block_dist = self.env.config[
            'pbft']['number_transactions_per_block']
        transactions_per_block = int(
            get_random_values(transactions_per_block_dist)[0])
        pending_txs = []
        tx_left = True
        for i in range(transactions_per_block * block_size):
            if self.transaction_queue.is_empty():
                print(
                    f'{self.address} at {time(self.env)}: No more transactions queued.')
                # Jiali: stop simulation when tx are done, in order to know whether/when it happens
                # raise Exception('TX all processed')
                tx_left = False if i == 0 else True
                break
            pending_tx = self.transaction_queue.get()
            pending_txs.append(pending_tx)
        candidate_block = self._build_candidate_block(pending_txs)
        print(
            f'{self.address} at {time(self.env)}: New candidate block #{candidate_block.header.number} created {candidate_block.header.hash[:8]} with difficulty {candidate_block.header.difficulty}')
        # Add the candidate block to the chain of the authority node
        self.chain.add_block(candidate_block)
        # We need to broadcast the new candidate block across the network
        self.broadcast_pre_prepare([candidate_block])
        return tx_left

    def _build_candidate_block(self, pending_txs):
        # Jiali: This function is borrowed from bitcoin/node.py, without any change actually.
        # Get the current head block
        prev_block = self.chain.head
        coinbase = self.address
        timestamp = self.env.now
        difficulty = self.consensus.calc_difficulty(prev_block, timestamp)
        block_number = prev_block.header.number + 1
        candidate_block_header = BlockHeader(
            prev_block.header.hash,
            block_number,
            timestamp,
            coinbase,
            difficulty)
        return Block(candidate_block_header, pending_txs)

    def _read_envelope(self, envelope):
        # Jiali: This function is borrowed from ethereum/node.py, with minor changes.
        super()._read_envelope(envelope)
        
        if self.is_malicious == MaliciousModel.PASSIVE:
            drop_message = random.choice([True, False], p=[self.drop_probability, 1 - self.drop_probability])
            if drop_message:
                return
                # to relax the assumption of malicious nodes handling newview
                # if envelope.msg['id'] not in ('checkpoint', 'viewchange', 'newview'):
                #     return
        
        if envelope.msg['id'] == 'status':
            self._receive_status(envelope)
        if envelope.msg['id'] == 'transactions':
            self._receive_full_transactions(envelope)
        if envelope.msg['id'] == 'reply':
            self._receive_reply(envelope)
        # Only do these if you are authority
        if self.is_authority:
            if envelope.msg['id'] == 'pre-prepare':
                self._receive_pre_prepare(envelope)
            if envelope.msg['id'] == 'prepare':
                self._receive_prepare(envelope)
            if envelope.msg['id'] == 'commit':
                self._receive_commit(envelope)
            if envelope.msg['id'] == 'checkpoint':
                self._receive_checkpoint_message(envelope)
            # Only the prospective next view primary should care about a viewchange
            # This is checked within "receive_viewchange"
            if envelope.msg['id'] == 'viewchange':
                self._receive_viewchange(envelope)
            if envelope.msg['id'] == 'newview':
                self._receive_newview(envelope)

    ##              ##
    ## Handshake    ##
    ##              ##

    def connect(self, nodes: list):
        super().connect(nodes)
        for node in nodes:
            self._handshake(node.address)

    def _handshake(self, destination_address: str):
        """Handshake inform a node of its current ethereum state, negotiating network, difficulties,
        head and genesis blocks
        This message should be sent after the initial handshake and prior to any ethereum related messages."""
        status_msg = self.network_message.status()
        print(
            f'{self.address} at {time(self.env)}: Status message sent to {destination_address}')
        self.env.process(self.send(destination_address, status_msg))

    def _receive_status(self, envelope):
        print(
            f'{self.address} at {time(self.env)}: Receive status from {envelope.origin.address}')
        node = self.active_sessions.get(envelope.origin.address)
        node['status'] = envelope.msg
        self.active_sessions[envelope.origin.address] = node
        self._handshaking.succeed()
        self._handshaking = self.env.event()

    ##              ##
    ## Transactions ##
    ##              ##

    def broadcast_transactions(self, transactions: list):
        """Broadcast transactions to all nodes with an active session and mark the hashes
        as known by each node"""
        yield self.connecting  # Wait for all connections
        # yield self._handshaking  # Wait for handshaking to be completed
        for node_address, node in self.active_sessions.items():
            for tx in transactions:
                # Checks if the transaction was previous sent
                if any({tx.hash} & node.get('knownTxs')):
                    print(
                        f'{self.address} at {time(self.env)}: Transaction {tx.hash[:8]} was already sent to {node_address}')
                    transactions.remove(tx)
                else:
                    self._mark_transaction(tx.hash, node_address)
        # Only send if it has transactions
        if transactions:
            print(
                f'{self.address} at {time(self.env)}: {len(transactions)} transactions ready to be sent')
            transactions_msg = self.network_message.transactions(transactions)
            self.env.process(self.broadcast(transactions_msg))

    def _receive_full_transactions(self, envelope):
        """Handle full tx received. If node is authority store transactions in a pool (ordered by the gas price)"""
        transactions = envelope.msg.get('transactions')
        valid_transactions = []
        for tx in transactions:
            if self.is_authority:
                self.transaction_queue.put(tx)
            else:
                valid_transactions.append(tx)
        # self.env.process(self.broadcast_transactions(valid_transactions))

    ##              ##
    ## Blocks       ##
    ##              ##

    def broadcast_pre_prepare(self, new_blocks: list):
        # Jiali: Here I renamed broadcast_new_blocks to broadcast_pre_prepare......
        """Specify one or more new blocks which have appeared on the network.
        To be maximally helpful, nodes should inform peers of all blocks that
        they may not be aware of."""
        new_blocks_hashes = {}
        block_bodies = {}
        # TODO: make our seqno adaptive to the fact that blocksim can handle a list of block in a single broadcast,
        #  even though this feature seems to be not used.
        for block in new_blocks:
            # Jiali: I changed the header number to header itself, for the sake of flexibility.
            new_blocks_hashes[block.header.hash] = block.header
            block_bodies[block.header.hash] = block.transactions
            # Jiali: Add block to its own log first.
            seqno = block.header.number
            self.log['block'][seqno] = block
            self.currSeqno = seqno

        new_blocks_msg = self.network_message.pre_prepare(seqno, new_blocks_hashes, block_bodies, False)
        self.env.process(self.broadcast(new_blocks_msg))

    def _receive_pre_prepare(self, envelope):
        # yield self.env.timeout(self.network.validation_delay)
        seqno = envelope.msg.get('seqno')

        if not self.validate_message_digest(envelope.msg):
            return
        
        if (envelope.msg['new_blocks'] == None) and (envelope.msg['block_bodies'] == None):
            self.log['block'][seqno] = None
            return  # Do nothing because it was a no-op preprepare from a view change
        new_blocks = envelope.msg['new_blocks']
        block_bodies = envelope.msg['block_bodies']

        print(f'{self.address} at {time(self.env)}: In pre-prepare phase, new blocks received {new_blocks}')
        # If the block is already known by a node, it does not need to prepare again.
        # block_numbers = []
        for block_hash, block_header in new_blocks.items():
            self._send_prepare(envelope)
            # Jiali: store the block in the log for future commit
            block = Block(block_header, block_bodies[block_hash])
            self.log['block'][seqno] = block
            print( 'TIME IS ' + time(self.env))

            if self.log['committed'][seqno] and self.chain.get_block(block_hash) is None:
                new_block = self.log['block'][seqno]
                self.chain.add_block(new_block)
                print(
                    f'{self.address} at {time(self.env)}: Block assembled and added to the top of the chain  {new_block.header}')

    def _send_prepare(self, envelop):
        # Send prepare
        # TODO: add attributes to prepare msg, a PREPARE should have <v, n, d, i>,
        #  where the seqno should be attached to block not per node! (so can not be self.seqno?)
        seqno = envelop.msg['seqno']
        print(
            f'{self.address} at {time(self.env)}: Prepare prepared to multicast.')
        prepare_msg = self.network_message.prepare(seqno)
        self.log['prepare'][seqno].add(self.address)
        self.env.process(self.broadcast_to_authorities(prepare_msg))

    def _receive_prepare(self, envelope):
        # yield self.env.timeout(self.network.validation_delay)
        """Handle prepare received"""
        if not self.validate_message_digest(envelope.msg):
            return
        seqno = envelope.msg.get('seqno')
        self.log['prepare'][seqno].add(envelope.origin.address)
        self.preparemsg[seqno] = envelope.msg
        # Replica multicasts a COMMIT to the other replicas when prepared becomes true.
        if len(self.log['prepare'][seqno]) >= 2*self.network.f:
            self.log['prepared'][seqno] = True
            self._send_commit(seqno)

    def _send_commit(self, seqno):
        """Request a node (identified by the `destination_address`) to return block bodies.
        Specify a list of `hashes` that we're interested in.
        """
        commit_msg = self.network_message.commit(seqno)
        self.log['commit'][seqno].add(self.address)
        self.env.process(self.broadcast_to_authorities(commit_msg))

    def _receive_commit(self, envelope):
        # yield self.env.timeout(self.network.validation_delay)
        """Handle block bodies receive   d
        Assemble the block header in a temporary list with the block body received and
        insert it in the blockchain"""
        if not self.validate_message_digest(envelope.msg):
            return
        seqno = envelope.msg.get('seqno')
        self.log['commit'][seqno].add(envelope.origin.address)
        # committed-local is true if and only if prepared is true and has accepted 2f+1 commits
        # (possibly including its own)
        if self.log['prepared'][seqno] and len(self.log['commit'][seqno]) >= 2*self.network.f+1:
            self.log['committed'][seqno] = True
        if self.log['committed'][seqno]:
            # TODO: sometimes, committed block is not in the log, i.e., not received from pre-prepare yet...
            #  It feels weird that commit comes earlier than pre-prepare...
            # Note from Ryan - Is this just at the end of the sim? If so, this could make sense...
            if self.log['block'][seqno]:
                new_block = self.log['block'][seqno]
                # if self._is_primary():
                client_reply = self.network_message.client_reply(new_block)
                self.env.process(self.broadcast_to_non_authorities(client_reply))
                self.chain.add_block(new_block)
                print(f'{self.address} at {time(self.env)}: Block assembled and added to the tip of the chain  {new_block.header}')

    # How non-authority nodes handle the receipt of a reply message from an authority
    def _receive_reply(self, envelope):
        # Handle a non-authority block receiving information about adding a block
        # yield self.env.timeout(self.network.validation_delay)
        if self.is_authority:
            raise RuntimeError(f'Node {self.location} is an authority - they should not receive replies')
            
        new_block = envelope.msg.get('result')
        timestamp = envelope.msg.get('timestamp')    
        
        self.log['reply'][timestamp].add(envelope.origin.address)
        if len(self.log['reply'][timestamp]) >= (2*self.network.f + 1):
            self.chain.add_block(new_block)

    ##                                               ##
    ##         View Changes and Checkpoints          ##
    ##                                               ##

    def _check_timeout(self):
        self.prevView = 0
        self.timeoutCount = 0
        self.prevLogBlockLength = 0

        while True:
            yield self.env.timeout(self.timeoutVal)
            # TOT: Bugfix. prevLog always same as log
            # assert self.prevLogBlockLength == len(self.log['block'])
            # TODO: Bugfix. Stop timeout and viewchange sending after leader change! Jiali
            if self.prevView == self.network.view and (self.prevLogBlockLength == len(self.log['block'])):  # No new blocks have been sent to a node + prevLog nonempty
                self.timedout = True
                self._send_viewchange()
                self.timeoutCount += 1
            else:
                self.timeoutCount = 0

            self.prevView = self.network.view
            self.prevLogBlockLength = len(self.log['block'])  # track log every timeout check

    def _checkpointing(self):
        while True:
            if (self.currSeqno % self.network.checkpoint_size) == 0:  # and (self.currSeqno - self.lastCheckpoint == self.network.checkpoint_size):  # Periodically see if we have reached a checkpoint handler
                self._send_checkpoint_message(self.currSeqno)
            yield self.env.timeout(self.network.checkpoint_delay)

    def _send_checkpoint_message(self, seqno):
        checkpoint_msg = self.network_message.checkpoint(seqno, self.replica_id)
        self.env.process(self.broadcast_to_authorities(checkpoint_msg))
        self.log['checkpoint'][seqno].add(self.address)

    def _receive_checkpoint_message(self, envelope):
        # yield self.env.timeout(self.network.validation_delay)
        if not self.validate_message_digest(envelope.msg):
            return
        seqno = envelope.msg.get('seqno')
        self.log['checkpoint'][seqno].add(envelope.origin.address)

        if self.log['checkpoint'][seqno] and len(self.log['checkpoint'][seqno]) >= 2*self.network.f:
            # Clear out log entries covered by a checkpoint state
            if self.log['committed'][self.lastCheckpoint]:
                for oldSeqno in range(self.lastCheckpoint, seqno):
                    # TODO: Iron out what to do with reply messages since they use timestamp instead of seqno
                    del self.log['reply'][self.log['block'][oldSeqno].header.timestamp]
                    del self.log['block'][oldSeqno]
                    del self.log['prepare'][oldSeqno]
                    del self.log['prepared'][oldSeqno]
                    del self.log['commit'][oldSeqno]
                    del self.log['committed'][oldSeqno]
                self.lastCheckpoint = seqno

    # IMPORTANT NOTE: View changes cannot be correctly implemented until checkpoints are first!
    def _send_viewchange(self):
        checkpoint_msg = self.log['checkpoint'][self.lastCheckpoint]
        prepare_msg = self._collect_viewchange_prepareset()
        viewchange_msg = self.network_message.view_change(self.lastCheckpoint, checkpoint_msg, prepare_msg)
        self.log['viewchange'][self.network.view].append((self.address, viewchange_msg))
        self.env.process(self.broadcast_to_authorities(viewchange_msg))
        
    def _collect_viewchange_prepareset(self):
        prepareset = []
        for seqno in range(self.lastCheckpoint, self.currSeqno):
            if self.log['prepared'][seqno]:
                prepareset.append(self.log['block'][seqno])
                # for node in range(1, (2*self.network.f) + 1):
                #    prepareset.append(self.log['prepare'][seqno][node])
                # TODO: May want to consider converting the log to use lists instead of sets and just deal with checking for duplicates.
                # Unless there is a no-duplicate list?
                prepareset.append(self.log['block'][seqno] )  # Could be more than 2f+1, but for now...
        return prepareset
        
    def _receive_viewchange(self, envelope):
        # yield self.env.timeout(self.network.validation_delay)
        newView = envelope.msg.get('nextview')
        if newView <= self.network.view:
            return
        for (address, msg) in self.log['viewchange'][newView]:  # Deal with list duplicates for viewchanges (need actual contents of viewchange messages, so can't use set)
            if address == envelope.origin.address:
                self.log['viewchange'][newView].remove((address,msg))
                self.log['viewchange'][newView].append((envelope.origin.address, envelope.msg))
                break
        else:
            self.log['viewchange'][newView].append((envelope.origin.address, envelope.msg))
            
        if self._is_next_primary():
            if len(self.log['viewchange'][newView]) >= (2*self.network.f + 1):
                self._send_newview(newView)
    
    def _send_newview(self, newView):
        viewchange_msg = self.log['viewchange'][self.network.view + 1]
        preprepare_msg = self._collect_newview_preprepareset(viewchange_msg)
        newview_msg = self.network_message.new_view(viewchange_msg, preprepare_msg)
        self.log['newview'][newView].add(self.address)
        self.env.process(self.broadcast_to_authorities(newview_msg))
        self.network.view += self.timeoutCount
    
    def _collect_newview_preprepareset(self, viewchange_msg):
        preprepareset = []
        max_checkpt = 0
        existing_seqnos = []
        max_s = 0  # See PBFT paper for description of 'max_s'
        for (origin_address, msg) in viewchange_msg:
            ckpt = msg.get('checkpoint_seqno')
            if ckpt > max_checkpt:
                max_checkpt = ckpt
            prepareset = msg.get('prepare_messages')
            for prepare_msg in prepareset:
                # Bug fixed. AttributeError: 'Block' object has no attribute 'get'
                # Bug fixed. AttributeError: 'NoneType' object has no attribute 'header'
                if prepare_msg is not None:
                    prepare_seqno = prepare_msg.header.number
                    existing_seqnos.append(prepare_seqno)
                    if prepare_seqno > max_s:
                        max_s = prepare_seqno
            
        min_s = max_checkpt  # See PBFT paper for description of 'min_s'
        
        # Check min_s relative to latest node checkpoint
        # If they don't match, forge a stability proof!
        if min_s > self.lastCheckpoint:
            for i in range(2 * self.network.f + 1):
                new_checkpoint = self.network_message.checkpoint(min_s, i)
                envelope = Envelope(new_checkpoint, time(self.env), None, None)
                self._receive_checkpoint_message(envelope)
        
        # New preprepare messages created for uncommitted messages from old view
        new_prepreparemsg = None
        for seqno in range(min_s, max_s + 1):
            if seqno in existing_seqnos:
                new_blocks = self.preparemsg[seqno].get('new_blocks')
                block_bodies = self.preparemsg[seqno].get('block_bodies')
                new_prepreparemsg = self.network_message.pre_prepare(seqno, new_blocks, block_bodies, True)
                
            else:
                new_prepreparemsg = self.network_message.pre_prepare(seqno, None, None, True)
                
            preprepareset.append(new_prepreparemsg)
            envelope = Envelope(new_prepreparemsg, time(self.env), None, None)
            self._receive_pre_prepare(envelope)  # Leverage already existing message to log 'O' for primary
        return preprepareset
    
    def _receive_newview(self, envelope):
        # yield self.env.timeout(self.network.validation_delay)
        if self._is_primary():
            return
        
        newview = envelope.msg.get('newview')
        if len(self.log['viewchange'][newview]) >= (2 * self.network.f + 1):
            for o_msg in envelope.msg.get('preprepare_messages'):
                pass
            self.current_view += 1
            
            
    def _is_primary(self):
        return self.replica_id == (self.network.view % len(self.network._list_authority_nodes))

    def _is_next_primary(self):
        return self.replica_id == ((self.network.view + self.timeoutCount) % len(self.network._list_authority_nodes))
    
    ##                                         ##
    ##     Malicious Nodes-related methods     ##
    ##                                         ##
    
    def validate_message_digest(self, message):
        # Note that digest is 1 meaning valid message!
        try:
            return message["digest"]
        except KeyError:
            return "This message has no digest"

    ##              ##
    ## Chains       ##
    ##              ##

    def save_chains(self, day):
        date = str(day)
        file = Path.cwd() / 'blocksim' / 'chains' / (date + self.address)
        with open(file, 'wb') as f:
            pickle.dump((self.chain.head, self.chain.db), f)

    def restore_chains(self, day):
        date = str(day)
        file = Path.cwd() / 'blocksim' / 'chains' / (date + self.address)
        with open(file, 'rb') as f:
            # yesterday_chains = pickle.load(f)
            # genesis = yesterday_chains.genesis
            # db = yesterday_chains.db
            genesis, db = pickle.load(f)
            consensus = Consensus(self.env)
            self.chain = Chain(self.env, self, consensus, genesis, db)
        # Jiali: remove dumped file after restore to collect garbage
        file.unlink()
