# 文件名: qroute_final.py

from base_simulator import BaseTrafficSimulator, BaseNetworkNode
import networkx as nx
import random
import numpy as np

class QRouteNode(BaseNetworkNode):
    """Q-Routing专用的节点，转发时会触发Q值更新"""
    def run(self):
        while True:
            packet = yield self.queue.get()
            self.update_queue_stats()

            yield self.env.timeout(1.0 / self.processing_rate)

            # 在数据包到达本节点后，触发对上一跳节点的Q值更新
            if packet.last_hop is not None:
                self.simulator.update_q_table(packet.last_hop, self.id, packet.destination)

            if self.simulator.is_in_measure_phase():
                self.packets_processed += 1

            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.get_next_hop(self.id, packet)
                if next_hop:
                    packet.last_hop = self.id # 记录上一跳
                    self.simulator.log_link_usage(self.id, next_hop)
                    if self.simulator.is_in_measure_phase(): self.packets_out += 1
                    self.simulator.nodes[next_hop].put(packet)
                else: # 探索或利用时找不到有效路径
                    self.simulator.log_drop()
                    if self.simulator.is_in_measure_phase(): self.packets_dropped += 1

class TrafficSimulator(BaseTrafficSimulator):
    """Q-Routing仿真器，继承自基类"""
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = QRouteNode
        self.init_nodes()

        print("  - Initializing Q-Tables with hop distance heuristic...")
        hop_distances = dict(nx.all_pairs_shortest_path_length(self.graph))
        self.q_tables = {
            node: {
                neighbor: {
                    dest: float(hop_distances[neighbor].get(dest, len(self.graph.nodes())))
                    for dest in self.graph.nodes()
                } for neighbor in self.graph.neighbors(node)
            } for node in self.graph.nodes()
        }
        self.epsilon = self.protocol_params.get('epsilon', 0.3)
        self.q_value_changes = [] # 用于Monitor记录Q值变化

    def get_next_hop(self, current_node_id, packet):
        dest = packet.destination
        neighbors = list(self.graph.neighbors(current_node_id))
        if not neighbors: return None

        epsilon_decay = self.protocol_params.get('epsilon_decay', 0.99995)
        current_epsilon = self.epsilon * (epsilon_decay ** self.env.now)

        if random.random() < current_epsilon:
            return random.choice(neighbors)
        else:
            valid_neighbors = [n for n in neighbors if n != packet.last_hop]
            if not valid_neighbors: valid_neighbors = neighbors
            q_values = {n: self.q_tables[current_node_id][n][dest] for n in valid_neighbors}
            return min(q_values, key=q_values.get)

    def update_q_table(self, from_node, to_node, dest):
        alpha = self.protocol_params.get('alpha', 0.1)
        gamma = self.protocol_params.get('gamma', 0.9)

        # 即时成本 = 下一跳节点的处理时间 + 排队时间
        immediate_cost = (1.0 / self.nodes[to_node].processing_rate) + \
                         (len(self.nodes[to_node].queue.items) / self.nodes[to_node].processing_rate)

        min_future_q = 0
        if to_node != dest:
            neighbors_of_to = list(self.graph.neighbors(to_node))
            if neighbors_of_to:
                min_future_q = min((self.q_tables[to_node][n][dest] for n in neighbors_of_to), default=float('inf'))

        current_q = self.q_tables[from_node][to_node][dest]
        new_q = current_q + alpha * (immediate_cost + gamma * min_future_q - current_q)
        self.q_tables[from_node][to_node][dest] = new_q
        self.q_value_changes.append(abs(new_q - current_q))

    def get_and_reset_delta_q(self):
        """供Monitor调用的方法，计算并重置Q值变化"""
        if not self.q_value_changes: return 0
        avg_delta = np.mean(self.q_value_changes)
        self.q_value_changes = []
        return avg_delta