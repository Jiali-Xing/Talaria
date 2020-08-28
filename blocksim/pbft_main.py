import json
import os
import time
from pathlib import Path
from datetime import datetime

from blocksim.models.pbft_network import Network
from blocksim.pbft_node_factory import NodeFactory
from blocksim.pbft_transaction_factory import TransactionFactory
from blocksim.world import SimulationWorld


def write_report(world):
    path = Path.cwd() / 'blocksim' / 'output' / 'report.json'
    
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


def run_model(json_file='tx_count_100.json', day=1):
    if day > 1:
        run_model(json_file, day-1)

    now = int(time.time())  # Current time
    duration = 3600  # seconds

    world = SimulationWorld(
        duration,
        now,
        Path.cwd() / 'dlasc-input-parameters' / 'config.json',
        Path.cwd() / 'dlasc-input-parameters' / 'latency.json',
        Path.cwd() / 'dlasc-input-parameters' / 'throughput-received.json',
        Path.cwd() / 'dlasc-input-parameters' / 'throughput-sent.json',
        Path.cwd() / 'dlasc-input-parameters' / 'delays.json',
        day
        )

    # Create the network
    network = Network(world.env, 'NetworkXPTO')

    #blocksim requires this specification for creating nodes, but can just
    #leave them blank
    miners = {}
    non_miners = {}

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
        if day > 1:
            node.restore_chains(day-1)

    transaction_factory = TransactionFactory(world)
    transaction_factory.broadcast(json_file, 9, nodes_list)

    world.start_simulation()
    report_node_chain(world, nodes_list)
    write_report(world)

    for node in nodes_list:
        node.save_chains(day)

    date_format = '%m-%d %H:%M:%S'
    t_delta = datetime.strptime(world.env.data['end_simulation_time'], date_format) - \
        datetime.strptime(world.env.data['start_simulation_time'], date_format)
    return t_delta.seconds


if __name__ == '__main__':
    main_folder = Path.cwd() / 'blocksim'
    if not main_folder.exists():
        print(Path.cwd())
        os.chdir(Path.parent)
        raise Exception('Wrong working dir. Should be blocksim-dlasc')

    # for i in range(1, 11):
    for i in [10]:
        #json_file = 'tx_count_' + str(i) + '000.json'
        json_file = 'tx_count_1.json'
        
        trials = 1
        time_record = []
        sim_time_record = []

        for i in range(trials):
            day = 1
            start_time = time.time()
            simulated_time = run_model(json_file, day=day)
            sim_time_record.append(simulated_time)
            running_time = time.time() - start_time
            time_record.append(running_time)

        # path = Path.cwd() / 'blocksim' / 'output' / ('PBFT_simulated_time_' + json_file)
        # with open(path, 'w') as f:
        #     json.dump(sim_time_record, f, indent=2)
        # path = Path.cwd() / 'blocksim' / 'output' / ('PBFT_running_time_' + json_file)
        # with open(path, 'w') as f:
        #     json.dump(time_record, f, indent=2)

    # ave_time = np.average(np.array(time_record))
    # sim_ave_time = np.average(np.array(sim_time_record))

    # print(sim_time_record)
    # print(ave_time)
