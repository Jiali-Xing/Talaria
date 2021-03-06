import json
from pathlib import Path
from random import choices, randint
from blocksim.transaction_factory import TransactionFactory
import numpy as np

from blocksim.models.ethereum.transaction import Transaction as ETHTransaction
from blocksim.models.transaction import Transaction


class PermTransactionFactory(TransactionFactory):
    """ Responsible to create batches of random transactions. Depending on the blockchain
    being simulated, transaction factory will create transactions according to the
    transaction model. Moreover, the created transactions will be broadcasted when simulation
    is running by a random node on a list. Additionally, the user needs to specify the
    number of batches, number of transactions per batch and the interval in seconds between each batch.
    """

    def __init__(self, world):
        super().__init__(world)

    def broadcast(self, json_file_name, interval, nodes_list):
        # path = Path.cwd() / 'blocksim' / 'tx_count.json'
        # path = Path.cwd() / 'DLASC' / 'simulator-master' / 'src' / 'tx_count_UTC.json'
        path = Path.cwd() / 'supply-chain-input-data' / json_file_name
        if not path.exists():
            raise Exception('Wrong working dir. Should be perm-blocksim')
        with path.open() as f:
            today = 'DAY ' + str(randint(0, 180 - 1)) + ' '
            # today = 'DAY 5 '

            # only one day's tx is too little...
            # Thus I decide to use all tx from 180 days
            all_days_tx = json.load(f)
            '''
            node_tx = []
            # This part sums all tx of 180 days, to make tx larger...
            for key, value in all_days_tx.items():
                node_tx.append(all_days_tx[key][1:])
                node_tx_array = np.array(node_tx)
            '''
            # sum_tx = np.sum(node_tx_array, axis=0)
            sum_tx = all_days_tx[today][1:]

        blockchain_switcher = {
            'poa': self._generate_poa_tx,
            'bitcoin': self._generate_bitcoin_tx,
            'ethereum': self._generate_ethereum_tx
        }

        for i in range(len(sum_tx)):
            transactions = []
            for _i in range(sum_tx[i]):
                # Generate a random string to a transaction be distinct from others
                # rand_sign = ''.join(
                #     choices(string.ascii_letters + string.digits, k=20))
                sign = '- '.join([today, nodes_list[i].address, str(_i), str(self._world.env.data['created_transactions'])])
                tx = blockchain_switcher.get(self._world.blockchain, lambda: "Invalid blockchain")(sign, i)
                transactions.append(tx)
            self._world.env.data['created_transactions'] += len(transactions)
            # Choose the given node to broadcast the transaction
            self._world.env.process(
                nodes_list[i].broadcast_transactions(transactions))
            # self._world.env.process(
            #     nodes_list[randint(0, len(nodes_list)-1)].broadcast_transactions(transactions))
            self._world.env.process(self._set_interval(interval))

    def _generate_bitcoin_tx(self, rand_sign, i):
        tx = Transaction('address', 'address', 140, rand_sign, 50)
        return tx

    def _generate_ethereum_tx(self, rand_sign, i):
        gas_limit = self._world.env.config['ethereum']['tx_gas_limit']
        tx = ETHTransaction('address', 'address',
                            140, rand_sign, i, 2, gas_limit)
        return tx

    def _generate_poa_tx(self, rand_sign, i):
        tx = Transaction('address', 'address', 140, rand_sign, 50)
        return tx

