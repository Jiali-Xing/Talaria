import csv
from pathlib import Path
from ast import literal_eval as make_tuple
from random import randint

from blocksim.models.bitcoin.node import BTCNode
from blocksim.models.ethereum.dlasc_node import ETHNode
from blocksim.models.poa.node import POANode
from blocksim.models.pbft.node import PBFTNode


class NodeFactory:
    """ Responsible to create the nodes used during the simulation.
    Depending on the blockchain being simulated, node factory will create nodes according
    to the node model. The user can specify the location, number of miners and non-miners,
    and the range of hash rate for the miner nodes. When nodes are created, is chosen a
    random hash rate from the range inputed. The location of each node needs to be recognised
    by the simulator, meaning that it needs to exist input parameters about latency and throughput.
    """

    def __init__(self, world, network):
        self._world = world
        self._network = network

    def create_nodes(self, miners, non_miners):
        self._check_location(miners, non_miners)
        # If a new blockchain is modeled it needs to be inserted here
        blockchain_switcher = {
            'bitcoin': self.create_bitcoin_nodes,
            'ethereum': self.create_ethereum_nodes,
            'poa': self.create_poa_nodes,
            'pbft': self.create_pbft_nodes
        }
        return blockchain_switcher.get(
            self._world.blockchain, lambda: "Invalid blockchain")(miners, non_miners)

    def create_poa_nodes(self, miners, non_miners):
        # Jiali: miners/non_miners are set by csv instead, so no need to provide above!
        path = Path.cwd() / 'blocksim' / 'Test_DLA1_Input.csv'
        if not path.exists():
            raise Exception('Wrong working dir. Should be blocksim-dlasc')
        with path.open('r') as infile:
            reader = csv.reader(infile)
            node_region = {rows[0]: rows[3] for rows in reader}
            print(node_region)
        # node_id = 0  # Unique ID for each node
        nodes_list = []
        for node_id, region_id in node_region.items():
            node_address = f'region_{region_id}-no_{node_id}'
            if int(region_id) <= 3:
                # Create the authority nodes if node is in US
                mega_hashrate_range = make_tuple('(20, 40)')
                # Jiali: hashrate is no longer needed, but let's keep it in case.
                # hashrate = randint(
                #     mega_hashrate_range[0], mega_hashrate_range[1]) * 10 ** 6
                new = POANode(self._world.env,
                              self._network,
                              region_id,
                              node_address,
                              # hashrate,
                              True)
                nodes_list.append(new)
            else:
                # Creat the non-authority nodes if node is oversea
                new = POANode(self._world.env,
                              self._network,
                              region_id,
                              node_address,
                              False)
                nodes_list.append(new)
        print(f'NodeFactory: Created {len(nodes_list)} PoA nodes')
        return nodes_list

    def create_pbft_nodes(self, miners, non_miners):
        # Jiali: miners/non_miners are set by csv instead, so no need to provide above!
        path = Path.cwd() / 'blocksim' / 'Test_DLA1_Input.csv'
        if not path.exists():
            raise Exception('Wrong working dir. Should be blocksim-dlasc')
        with path.open('r') as infile:
            reader = csv.reader(infile)
            node_region = {rows[0]: rows[3] for rows in reader}
            print(node_region)
        # node_id = 0  # Unique ID for each node
        nodes_list = []
        replica_id = 0
        for node_id, region_id in node_region.items():
            node_address = f'region_{region_id}-no_{node_id}'
            if int(region_id) <= 3:
                # Create the authority nodes if node is in US
                mega_hashrate_range = make_tuple('(20, 40)')
                # Jiali: hashrate is no longer needed, but let's keep it in case.
                # hashrate = randint(
                #     mega_hashrate_range[0], mega_hashrate_range[1]) * 10 ** 6
                new = PBFTNode(self._world.env,
                              self._network,
                              region_id,
                              node_address,
                              replica_id,
                              True)
                nodes_list.append(new)
            else:
                # Creat the non-authority nodes if node is oversea
                new = PBFTNode(self._world.env,
                              self._network,
                              region_id,
                              node_address,
                              replica_id,
                              False)
                nodes_list.append(new)
            replica_id = replica_id + 1
            
        print(f'NodeFactory: Created {len(nodes_list)} PoA nodes')
        return nodes_list

    def create_bitcoin_nodes(self, miners, non_miners):
        node_id = 0  # Unique ID for each node
        # Create the miners nodes
        miners_list = []
        for miner_location, _miners in miners.items():
            for i in range(_miners['how_many']):
                node_id += 1
                node_address = f'{miner_location.lower()}-{node_id}'
                mega_hashrate_range = make_tuple(
                    _miners['mega_hashrate_range'])
                # Choose a random value on MH/s range and convert to H/s
                hashrate = randint(
                    mega_hashrate_range[0], mega_hashrate_range[1])*10**6
                new = BTCNode(self._world.env,
                              self._network,
                              miner_location,
                              node_address,
                              hashrate,
                              True)
                miners_list.append(new)
        # Create the non-miners nodes
        non_miners_list = []
        for miner_location, _miners in non_miners.items():
            for i in range(_miners['how_many']):
                node_id += 1
                node_address = f'{miner_location.lower()}-{node_id}'
                new = BTCNode(self._world.env,
                              self._network,
                              miner_location,
                              node_address)
                non_miners_list.append(new)
        # Fully connect all the nodes
        nodes_list = miners_list + non_miners_list
        print(f'NodeFactory: Created {len(nodes_list)} bitcoin nodes')
        return nodes_list

    def create_ethereum_nodes(self, miners, non_miners):
        with open('Test_DLA1_Input.csv', mode='r') as infile:
            reader = csv.reader(infile)
            node_region = {rows[0]: rows[3] for rows in reader}
            print(node_region)
        # node_id = 0  # Unique ID for each node
        nodes_list = []
        for node_id, region_id in node_region.items():
            node_address = f'{region_id}-{node_id}'
            if int(region_id) <= 3:
                # Create the miners nodes if node is in US
                mega_hashrate_range = make_tuple('(20, 40)')
                # Choose a random value on MH/s range and convert to H/s
                hashrate = randint(
                    mega_hashrate_range[0], mega_hashrate_range[1]) * 10 ** 6
                new = ETHNode(self._world.env,
                              self._network,
                              region_id,
                              node_address,
                              hashrate,
                              True)
                nodes_list.append(new)
            else:
                # Creat the non-miner nodes if node is oversea
                new = ETHNode(self._world.env,
                              self._network,
                              region_id,
                              node_address,
                              False)
                nodes_list.append(new)
        print(f'NodeFactory: Created {len(nodes_list)} ethereum nodes')
        return nodes_list

        # for miner_location, _miners in miners.items():
        #     for i in range(_miners['how_many']):
        #         node_id += 1
        #         node_address = f'{miner_location.lower()}-{node_id}'
        #         mega_hashrate_range = make_tuple(
        #             _miners['mega_hashrate_range'])
        #         # Choose a random value on MH/s range and convert to H/s
        #         hashrate = randint(
        #             mega_hashrate_range[0], mega_hashrate_range[1])*10**6
        #         new = ETHNode(self._world.env,
        #                       self._network,
        #                       miner_location,
        #                       node_address,
        #                       hashrate,
        #                       True)
        #         miners_list.append(new)
        #
        # # Create the non-miners nodes
        # non_miners_list = []
        # for miner_location, _miners in non_miners.items():
        #     for i in range(_miners['how_many']):
        #         node_id += 1
        #         node_address = f'{miner_location.lower()}-{node_id}'
        #         new = ETHNode(self._world.env,
        #                       self._network,
        #                       miner_location,
        #                       node_address,
        #                       False)
        #         non_miners_list.append(new)
        # Fully connect all the nodes
        # nodes_list = miners_list + non_miners_list
        # print(f'NodeFactory: Created {len(nodes_list)} ethereum nodes')
        # return nodes_list

    def _check_location(self, miners, non_miners):
        nodes_location = list(miners.keys()) + list(non_miners)
        for location in nodes_location:
            if location not in self._world.locations:
                raise RuntimeError(
                    f'There are not measurements for the location {location}. Only available locations: {self._world.locations}')
