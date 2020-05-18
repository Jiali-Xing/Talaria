import string
from random import randint, choices
from blocksim.models.transaction import Transaction
from blocksim.models.ethereum.transaction import Transaction as ETHTransaction
import json

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
            today = randint(0, 180 - 1)
            node_tx = json.load(f)[today]

        for i in range(len(node_tx)-1):
            transactions = []
            for _i in range(node_tx[str(i+1)]):
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
