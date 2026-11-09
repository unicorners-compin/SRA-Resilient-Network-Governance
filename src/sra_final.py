# 文件名: sra_final.py

print("Attempting to import from base_simulator for SRA...")
from base_simulator import BaseTrafficSimulator, BaseNetworkNode
import networkx as nx
import simpy # Import simpy here
import numpy as np
from collections import deque # Make sure deque is available


class SRANode(BaseNetworkNode):
    """SRA专用的节点，其行为与Dijkstra节点类似，被动接收路由更新"""
    def run(self):
        # print(f"Node {self.id} SRA run process started.")
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
                    # SRA node looks up next hop in the simulator's dynamic routing table
                    # Need to ensure routing_tables is accessible and updated
                    next_hop = self.simulator.routing_tables.get(self.id, {}).get(packet.destination)

                    if next_hop is not None and next_hop in self.simulator.nodes:
                        self.simulator.log_link_usage(self.id, next_hop)
                        if self.simulator.is_in_measure_phase(): self.packets_out += 1
                        if not self.simulator.nodes[next_hop].put(packet):
                            self.simulator.log_drop()
                            if self.simulator.is_in_measure_phase(): self.packets_dropped += 1
                    else: # No route found (should be rare after warmup)
                        self.simulator.log_drop()
                        if self.simulator.is_in_measure_phase(): self.packets_dropped += 1
            except simpy.Interrupt:
                 pass


class TrafficSimulator(BaseTrafficSimulator):
    """SRA仿真器，其独特之处在于有一个后台进程在预热期不断更新路由"""
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = SRANode
        self.init_nodes() # Initialize nodes after setting NodeClass

        # SRA 核心状态变量
        self.accumulated_stress = {node: 0.0 for node in self.graph.nodes()}
        self.node_costs = {node: 1.0 for node in self.graph.nodes()}
        self.routing_tables = {node: {} for node in self.graph.nodes()} # Dynamic routing tables

        # Start the SRA background update process
        # This process should run during the warmup phase
        self.sra_updater_process = env.process(self.sra_updater())

    def sra_updater(self):
        """SRA 的核心迭代进程，在预热期运行"""
        update_interval = self.protocol_params.get('update_interval', 50)
        alpha = self.protocol_params.get('alpha', 0.1)
        beta_i = self.protocol_params.get('beta_I', 10.0)

        print("  - SRA updater process started...")

        # Continue updating as long as we are in the warmup phase
        while self.phase == 'warmup':
            # 1. 根据节点成本设置边权重 (Weight is cost of destination node)
            for u, v in self.graph.edges():
                self.graph[u][v]['weight'] = self.node_costs[v] # Weight is cost of destination node

            # 2. 计算加权中心性和最短路径 (using the new weights)
            # Ensure centrality calculation can handle disconnected components if necessary,
            # though we are using the largest connected component.
            try:
                current_bc = nx.betweenness_centrality(self.graph, weight='weight', normalized=True)
            except Exception as e:
                 print(f"Warning: Error calculating betweenness centrality: {e}")
                 current_bc = {node: 0.0 for node in self.graph.nodes()} # Default to zero if calculation fails


            # 3. 更新所有节点的路由表 based on the new weights
            # Calculate shortest paths using the current edge weights (node costs)
            # Then update the routing table for each node.
            current_shortest_paths = {}
            try:
                 # Calculate all-pairs shortest paths using current weights
                 current_shortest_paths = dict(nx.all_pairs_dijkstra_path(self.graph, weight='weight'))
            except nx.NetworkXNoPath:
                 print("Warning: Network became disconnected during SRA update step.")
                 # Keep existing routing tables if paths disappear

            # Update routing tables for all nodes
            for source_node in self.graph.nodes():
                # For each destination, the next hop is the second node in the shortest path
                self.routing_tables[source_node] = {
                    dest: path[1] for dest, path in current_shortest_paths.get(source_node, {}).items()
                    if len(path) > 1
                }


            # 4. 更新累积应力和节点成本
            max_bc = max(current_bc.values()) if current_bc else 1.0
            if max_bc == 0: max_bc = 1.0 # Avoid division by zero

            for node_id in self.graph.nodes():
                norm_bc = current_bc.get(node_id, 0.0) / max_bc
                # S(t+1) = (1-alpha)S(t) + alpha * normalized_BC(t)
                self.accumulated_stress[node_id] = (1 - alpha) * self.accumulated_stress[node_id] + alpha * norm_bc
                # C(t+1) = 1 + beta_I * S(t+1)
                self.node_costs[node_id] = 1 + beta_i * self.accumulated_stress[node_id]

            # Yield timeout to wait for the next update interval
            yield self.env.timeout(update_interval)

        print("  - SRA updater process finished (warmup period ended).")
        # Optional: Calculate final routing tables one last time
        # based on the final node costs after warmup.
        # This is already handled by the last iteration of the loop.

    # SRA simulator uses the routing_tables updated by the sra_updater process.
    # It does not need a separate get_next_hop method for packet forwarding,
    # as the SRANode looks up the route in self.simulator.routing_tables.

    # The BaseTrafficSimulator's run method will start the simulation clock
    # and trigger the packet generation and node processes, including the sra_updater.