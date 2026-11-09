# 文件名: dijkstra_final.py
print("Attempting to import from base_simulator...")
from base_simulator import BaseTrafficSimulator, BaseNetworkNode
import networkx as nx
import simpy # Import simpy here

class DijkstraNode(BaseNetworkNode):
    """Dijkstra专用的节点，其转发逻辑是固定的查表"""
    def run(self):
        # --- Added print for debugging ---
        # print(f"Node {self.id} Dijkstra run process started.")
        while True:
            try:
                # yield self.queue.get() is for simpy.Store, we use simpy.Container
                # Packets arrive via self.put() from neighbors.
                # We process packets from the queue (deque).
                # We need to wait for the queue to have items before processing.
                # A simple approach is to check the queue and yield a timeout.
                # A better approach is to use simpy.Store if queueing is the bottleneck.
                # Since BaseNetworkNode uses simpy.Container for capacity,
                # let's keep the deque for the queue logic and yield timeouts for processing time.

                if not self.queue:
                    # If queue is empty, wait a short time before checking again
                    yield self.env.timeout(1)
                    continue

                packet = self.queue.popleft()
                self.update_queue_stats()

                # Simulate processing time
                yield self.env.timeout(1.0 / self.processing_rate)

                if self.simulator.is_in_measure_phase():
                    self.packets_processed += 1

                if packet.destination == self.id:
                    self.simulator.log_delivery(packet)
                else:
                    # Look up next hop in the pre-calculated static routing table
                    next_hop = self.simulator.routing_tables[self.id].get(packet.destination)
                    if next_hop is not None and next_hop in self.simulator.nodes:
                        self.simulator.log_link_usage(self.id, next_hop)
                        if self.simulator.is_in_measure_phase(): self.packets_out += 1
                        # Attempt to put packet into next hop's queue
                        # If queue is full, the packet is dropped
                        if not self.simulator.nodes[next_hop].put(packet):
                             # Packet dropped at next hop's queue
                             self.simulator.log_drop()
                             if self.simulator.is_in_measure_phase(): self.packets_dropped += 1
                    else: # No route found or invalid next hop
                        self.simulator.log_drop()
                        if self.simulator.is_in_measure_phase(): self.packets_dropped += 1

            except simpy.Interrupt:
                 # Handle interruption if needed (e.g., during drain phase)
                 pass


class TrafficSimulator(BaseTrafficSimulator):
    """Dijkstra仿真器，继承自基类"""
    def __init__(self, env, graph, protocol, **params):
        # 1. 调用基类的初始化方法
        super().__init__(env, graph, protocol, **params)

        # 2. 指定使用Dijkstra专用的Node类
        self.NodeClass = DijkstraNode
        self.init_nodes() # Initialize nodes after setting NodeClass

        # 3. 执行Dijkstra独特的初始化：计算静态路由表
        print("  - Pre-calculating static Dijkstra routing tables...")
        self.routing_tables = {}
        for source_node in self.graph.nodes():
            try:
                # single_source_dijkstra returns (distances, paths)
                # We only need the paths to find the next hop
                distances, paths = nx.single_source_dijkstra(self.graph, source_node)
                # The next hop for a destination is the second node in the shortest path
                self.routing_tables[source_node] = {dest: path[1] for dest, path in paths.items() if len(path) > 1}
            except nx.NetworkXNoPath:
                # Handle cases where a node might be disconnected - should not happen in connected component
                self.routing_tables[source_node] = {}
            except KeyError as e:
                 print(f"Warning: Could not find path from {source_node} to a destination.")
                 self.routing_tables[source_node] = {} # Ensure entry exists

        print("  - Dijkstra routing tables calculated.")

    # Dijkstra simulator uses the routing_tables calculated in __init__
    # It does not need a get_next_hop method in the simulator level, as
    # the node itself looks up the route.
    # The BaseTrafficSimulator's run method will trigger node processes.