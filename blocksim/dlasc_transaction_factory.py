import string
from random import randint, choices
from blocksim.models.transaction import Transaction
from blocksim.models.ethereum.transaction import Transaction as ETHTransaction
import json
import numpy as np

# Read a dictionary for node_tx
# node_tx = {}
# for nodes in range(1, 112):
#     use integer as key please
#     node_tx[nodes] = randint(0, 5)


class TransactionFactory:
    """ Responsible to create batches of random transactions. Depending on the blockchain
    being simulated, transaction factory will create transactions according to the
    transaction model. Moreover, the created transactions will be broadcasted when simulation
    is running by a random node on a list. Additionally, the user needs to specify the
    number of batches, number of transactions per batch and the interval in seconds between each batch.
    """

    def __init__(self, world):
        self._world = world

    def broadcast(self, number_of_batches, transactions_per_batch, interval, nodes_list):
        with open('../DLASC/src/tx_count.json') as f:
            # today = randint(0, 180 - 1)
            today = ' DAY 5 '
            # only one day's tx is too little...
            # Thus I decide to use all tx from 180 days
            all_days_tx = json.load(f)
            j = 0
            # This part sums all tx of 180 days, to make tx larger...
            for key, value in all_days_tx.items():
                node_tx = np.empty([len(all_days_tx), len(all_days_tx[today][1:])], dtype=np.int64)
                node_tx[j] = all_days_tx[key][1:]
                j += 1
            sum_tx = np.sum(node_tx, axis=0)

        for i in range(len(sum_tx)):
            transactions = []
            for _i in range(sum_tx[i]):
                # Generate a random string to a transaction be distinct from others
                rand_sign = ''.join(
                    choices(string.ascii_letters + string.digits, k=20))
                if self._world.blockchain == 'bitcoin':
                    tx = Transaction('address', 'address', 140, rand_sign, 50)
                elif self._world.blockchain == 'ethereum':
                    gas_limit = self._world.env.config['ethereum']['tx_gas_limit']
                    tx = ETHTransaction('address', 'address',
                                        140, rand_sign, i, 2, gas_limit)
                transactions.append(tx)
            self._world.env.data['created_transactions'] += len(transactions)
            # Choose the given node to broadcast the transaction
            self._world.env.process(
                nodes_list[i].broadcast_transactions(transactions))
            # self._world.env.process(
            #     nodes_list[randint(0, len(nodes_list)-1)].broadcast_transactions(transactions))
            self._world.env.process(self._set_interval(interval))

    def _set_interval(self, interval):
        yield self._world.env.timeout(interval)
