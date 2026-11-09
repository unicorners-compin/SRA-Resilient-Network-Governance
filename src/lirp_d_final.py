# 文件名: lirp_d_final.py

print("Attempting to import from base_simulator for LIRP-D...")
from base_simulator import BaseTrafficSimulator, BaseNetworkNode
import networkx as nx
import simpy # Import simpy here
from collections import deque # Make sure deque is available


class LIRPNode(BaseNetworkNode):
    """LIRP-D专用的节点，其转发逻辑是动态决策"""
    def run(self):
        # print(f"Node {self.id} LIRP-D run process started.")
        while True:
            try:
                if not self.queue:
                    yield self.env.timeout(1)
                    continue

                packet = self.queue.popleft()
                self.update_queue_stats()

                yield self.env.timeout(1.0 / self.processing_rate)

                if self.simulator.is_in_measure_phase():
                    self.packets_processed += 1

                if packet.destination == self.id:
                    self.simulator.log_delivery(packet)
                else:
                    # LIRP-D logic: get next hop from simulator's method
                    next_hop = self.simulator.get_next_hop(self.id, packet)
                    if next_hop is not None and next_hop in self.simulator.nodes:
                        self.simulator.log_link_usage(self.id, next_hop)
                        if self.simulator.is_in_measure_phase(): self.packets_out += 1
                        if not self.simulator.nodes[next_hop].put(packet):
                             self.simulator.log_drop()
                             if self.simulator.is_in_measure_phase(): self.packets_dropped += 1
                    else: # No closer neighbor or local optimum
                        self.simulator.log_drop()
                        if self.simulator.is_in_measure_phase(): self.packets_dropped += 1
            except simpy.Interrupt:
                 pass


class TrafficSimulator(BaseTrafficSimulator):
    """LIRP-D仿真器，继承自基类"""
    def __init__(self, env, graph, protocol, **params):
        # 1. 调用基类的初始化方法
        super().__init__(env, graph, protocol, **params)

        # 2. 指定使用LIRP-D专用的Node类
        self.NodeClass = LIRPNode
        self.init_nodes() # Initialize nodes after setting NodeClass

        # 3. 执行LIRP-D独特的初始化：计算跳数距离 (静态)
        print("  - Pre-calculating hop distances for LIRP-D...")
        # Calculate all-pairs shortest path lengths (unweighted)
        self.hop_distances = dict(nx.all_pairs_shortest_path_length(self.graph))
        print("  - Hop distances calculated.")


    def get_next_hop(self, current_node_id, packet):
        """LIRP-D的核心路由逻辑: 贪婪地选择距离目的地跳数更近且队列最短的邻居。"""
        dest = packet.destination
        neighbors = list(self.graph.neighbors(current_node_id))
        if not neighbors: return None

        # Get hop distance from current node to destination
        current_dist = self.hop_distances.get(current_node_id, {}).get(dest, float('inf'))

        # Find neighbors that are strictly closer to the destination
        closer_neighbors = [
            n for n in neighbors
            if self.hop_distances.get(n, {}).get(dest, float('inf')) < current_dist
        ]

        if not closer_neighbors:
            # If no neighbor is strictly closer, we are in a local optimum or at the destination's neighbor
            # If at destination's neighbor, the packet would have been delivered.
            # So, if closer_neighbors is empty and we are not the destination, it's a local optimum trap.
            return None

        # Among closer neighbors, select the one with the shortest queue
        # Access the actual queue length from the node instances
        return min(closer_neighbors, key=lambda n: len(self.nodes[n].queue.items))