from blocksim.models.network import Network, Connection


class PermissionedNetwork(Network):
    def __init__(self, env, name):
        super().__init__(env, name)
        self._list_authority_nodes = []  # Want to keep track of which nodes are authorities
        self.authority_index = 0  # Keep track of which authority we're on

    def add_node(self, node):
        self._nodes[node.address] = node

    def _init_lists(self):
        for add, node in self._nodes.items():
            self._list_nodes.append(node)
            if node.is_authority:  # Put the authority nodes in the authority node list
                self._list_authority_nodes.append(node)
