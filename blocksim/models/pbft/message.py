from blocksim.utils import kB_to_MB


class Message:
    # Jiali: Copied from Ethereum
    # Defines a model for the network messages of the PoA blockchain.

    def __init__(self, origin_node):
        self.origin_node = origin_node
        _env = origin_node.env
        self._message_size = _env.config['poa']['message_size_kB']
        self.seqno = 0

    def increment_seqno(self):
        self.seqno = self.seqno + 1
        return self.seqno

    def status(self):
        """ Inform a peer of its current PoA state.
        This message should be sent `after` the initial handshake and `prior` to any PoA related messages.
        """
        return {
            'id': 'status',
            'protocol_version': 'ONE',
            'network': self.origin_node.network.name,
            'td': self.origin_node.chain.head.header.difficulty,
            'best_hash': self.origin_node.chain.head.header.hash,
            'genesis_hash': self.origin_node.chain.genesis.header.hash,
            'size': kB_to_MB(self._message_size['status'])
        }

    def transactions(self, transactions: list):
        """ Specify (a) transaction(s) that the peer should make sure is included on its
        transaction queue. Nodes must not resend the same transaction to a peer in the same session.
        This packet must contain at least one (new) transaction.
        """
        num_txs = len(transactions)
        transactions_size = num_txs * self._message_size['tx']
        return {
            'id': 'transactions',
            'transactions': transactions,
            'size': kB_to_MB(transactions_size)
        }
    
    # Ryan: Reformat messages to hold info
    def pre_prepare(self, new_blocks: dict):
        # Jiali: pre-prepare should be similar to newblock, so I migrate newblock to here.
        """Advertises one or more new blocks which have appeared on the network"""
        self.increment_seqno()
        num_new_block_hashes = len(new_blocks)
        new_blocks_size = num_new_block_hashes * \
                          self._message_size['hash_size']
        return {
            'id': 'pre-prepare',
            'view': self.origin_node.network.view,
            'seqno': self.seqno,
            'digest': 0,
            'new_blocks': new_blocks,
            'size': kB_to_MB(new_blocks_size)
        }
    
    def prepare(self):
        return {
            'id': 'prepare',
            'view': self.origin_node.network.view,
            'seqno': self.seqno,
            'digest': 0,
            'replica_id': self.origin_node.replica_id,
            'size': kB_to_MB(self._message_size['get_headers'])
        }
    
    # Originally copied from "block_bodies()" below
    def commit(self):
        return {
            'id': 'commit',
            'view': self.origin_node.network.view,
            'seqno': self.seqno,
            'digest': 0,
            'replica_id': self.origin_node.replica_id,
            'size': kB_to_MB(self._message_size['block_header_size'])
        }

    # def block_headers(self, block_headers: list):
    #     """ Reply to `get_headers` the items in the list are block headers.
    #     This may contain no block headers if no block headers were able to be returned
    #     for the `get_headers` message.
    #     """
    #     num_headers = len(block_headers)
    #     block_headers_size = num_headers * self._message_size['header']
    #     return {
    #         'id': 'block_headers',
    #         'block_headers': block_headers,
    #         'size': kB_to_MB(block_headers_size)
    #     }


    # def block_bodies(self, block_bodies: dict):
    #     """ Reply to `get_block_bodies`. The items in the list are some of the blocks, minus the header.
    #     This may contain no items if no blocks were able to be returned for the `get_block_bodies` message.
    #     """
    #     txsCount = 0
    #     for block_hash, block_txs in block_bodies.items():
    #         txsCount += len(block_txs)
    #     message_size = (
    #         txsCount * self._message_size['tx']) + self._message_size['block_bodies']
    #     print(
    #         f'block bodies with {txsCount} txs have a message size: {message_size} kB')
    #     return {
    #         'id': 'block_bodies',
    #         'block_bodies': block_bodies,
    #         'size': kB_to_MB(message_size)
    #     }
