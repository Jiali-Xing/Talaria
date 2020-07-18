from collections import OrderedDict
# from collections import deque
# from blocksim.utils import time


class TransactionQueue():
    def __init__(self, env, node, consensus):
        self._env = env
        self._node = node
        self._consensus = consensus
        self._transaction_queue = OrderedDict()
        key = f'{node.address}_number_of_transactions_queue'
        self._env.data[key] = 0

    def put(self, tx):
        key = f'{self._node.address}_number_of_transactions_queue'
        self._env.data[key] += 1
        self._transaction_queue[tx.signature] = tx

    def get(self):
        # TODO: A delay to retrieve a transaction from the Queue
        # Jiali: FIFO popitem is achieved with the OrderedDict() here
        return self._transaction_queue.popitem(last=False)[1]

    def remove(self, tx):
        # None is the default value for pop, so no exception is raised if given key doesn't exist
        return self._transaction_queue.pop(tx.signature, None)

    def remove_txs(self, txs):
        [self._transaction_queue.pop(tx.signature) for tx in txs]

    def add_txs(self, txs):
        for tx in txs:
            self.put(tx)

    def is_empty(self):
        return len(self._transaction_queue) == 0

    def size(self):
        return len(self._transaction_queue)
