import json
from random import random
import numpy as np
from pathlib import Path

for i in range(1, 11):
    json_file = 'tx_count_' + str(i) + '000.json'

    path = Path.cwd() / 'DLASC' / 'simulator-master' / 'src' / json_file
    if not path.exists():
        raise Exception('Wrong working dir. Should be blocksim-dlasc')

    all_days = True
    with path.open() as f:
        all_days_tx = json.load(f)
        if all_days:
            today = 'All Days'
            node_tx = []
            for key, value in all_days_tx.items():
                if int(key[-2:-1]) < 1:
                    node_tx.append(all_days_tx[key][1:])
            node_tx_array = np.array(node_tx)
            sum_tx = np.sum(node_tx_array, axis=0)

            print(np.sum(sum_tx[0:30]))
