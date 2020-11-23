import json
import time
from pathlib import Path
from datetime import datetime

from blocksim.models.permissioned_network import Network
from blocksim.permissioned_node_factory import NodeFactory
from blocksim.permissioned_transaction_factory import TransactionFactory
from blocksim.world import SimulationWorld


def write_report(world):
    path = Path.cwd() / 'blocksim' / 'output' / 'report.json'
    # if not os.path.exists(path):
    #     os.mkdir('output')

    with open(path, 'w') as f:
        json.dump(world.env.data, f, indent=2)


def report_node_chain(world, nodes_list):
    for node in nodes_list:
        head = node.chain.head
        chain_list = []
        num_blocks = 0
        for i in range(head.header.number):
            b = node.chain.get_block_by_number(i)
            chain_list.append(str(b.header))
            num_blocks += 1
        chain_list.append(str(head.header))
        key = f'{node.address}_chain'
        world.env.data[key] = {
            'head_block_hash': f'{head.header.hash[:8]} #{head.header.number}',
            'number_of_blocks': num_blocks,
            'chain_list': chain_list
        }


def run_model(json_file='tx_count_10000.json'):
    now = int(time.time())  # Current time
    duration = 3600  # seconds

    world = SimulationWorld(
        duration,
        now,
        Path.cwd() / 'dlasc-input-parameters' / 'config_poa.json',
        Path.cwd() / 'dlasc-input-parameters' / 'latency.json',
        Path.cwd() / 'dlasc-input-parameters' / 'throughput-received.json',
        Path.cwd() / 'dlasc-input-parameters' / 'throughput-sent.json',
        Path.cwd() / 'dlasc-input-parameters' / 'delays.json'
        )

    # Create the network
    network = Network(world.env, 'NetworkXPTO')

    miners = {
        '5': {
            'how_many': 1,
            'mega_hashrate_range': "(20, 40)"
        },
        '1': {
            'how_many': 1,
            'mega_hashrate_range': "(20, 40)"
        }
    }
    non_miners = {
        '1': {
            'how_many': 1
        },
        '4': {
            'how_many': 1
        }
    }

    node_factory = NodeFactory(world, network)
    # Create all nodes
    # Notice that the miner/non_miners this useless here, they're specified in
    # dlasc_node_factory
    nodes_list = node_factory.create_nodes(miners, non_miners)
    # Start the network heartbeat
    world.env.process(network.start_heartbeat())
    # Full Connect all nodes
    for node in nodes_list:
        node.connect(nodes_list)

    transaction_factory = TransactionFactory(world)
    transaction_factory.broadcast(json_file, 5, nodes_list)

    world.start_simulation()
    report_node_chain(world, nodes_list)
    write_report(world)

    date_format = '%m-%d %H:%M:%S'
    t_delta = datetime.strptime(world.env.data['end_simulation_time'], date_format) - \
        datetime.strptime(world.env.data['start_simulation_time'], date_format)
    return t_delta.seconds


if __name__ == '__main__':
    main_folder = Path.cwd() / 'blocksim'
    if not main_folder.exists():
        raise Exception('Wrong working dir. Should be blocksim-dlasc')

    for i in range(10, 11):
        json_file = 'tx_count_' + str(i) + '000.json'

        trials = 1
        time_record = []
        sim_time_record = []

        for i in range(trials):
            start_time = time.time()
            simulated_time = run_model(json_file)
            sim_time_record.append(simulated_time)
            running_time = time.time() - start_time
            time_record.append(running_time)

        path = Path.cwd() / 'blocksim' / 'output' / ('simulation_time_' + json_file)
        with open(path, 'w') as f:
            json.dump(sim_time_record, f, indent=2)
        path = Path.cwd() / 'blocksim' / 'output' / ('running_time_' + json_file)
        with open(path, 'w') as f:
            json.dump(time_record, f, indent=2)

    # ave_time = np.average(np.array(time_record))
    # sim_ave_time = np.average(np.array(sim_time_record))

    # print(sim_time_record)
    # print(ave_time)
