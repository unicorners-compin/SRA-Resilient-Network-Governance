import networkx as nx
from collections import deque
import numpy as np

class Packet:
    def __init__(self, source, destination, creation_time):
        self.source = source
        self.destination = destination
        self.creation_time = creation_time
        self.path = [source]

class Node:
    # --- 唯一的改动在这里 ---
    def __init__(self, node_id, processing_capacity=20, queue_capacity=50):
        # 将处理能力从10提升到20
        self.id = node_id
        self.processing_capacity = processing_capacity
        self.queue_capacity = queue_capacity
        self.queue = deque()

    def receive_packet(self, packet, current_time):
        if len(self.queue) < self.queue_capacity:
            self.queue.append(packet)
            return True
        return False

class Network:
    def __init__(self, graph):
        self.graph = graph
        self.nodes = {i: Node(i) for i in graph.nodes()}

class RoutingAlgorithm:
    def get_next_hop(self, current_node, destination_node, network):
        raise NotImplementedError

class Simulator:
    def __init__(self, network, algorithm, packet_rate, sim_duration, rng_seed=42):
        self.network = network
        self.algorithm = algorithm
        self.packet_rate = packet_rate
        self.sim_duration = sim_duration
        self.rng = np.random.default_rng(rng_seed)
        self.stats = {
            'packets_generated': 0,
            'packets_delivered': 0,
            'total_latency': 0
        }

    def run(self):
        for t in range(self.sim_duration):
            # Packet Generation (Probabilistic)
            for i in self.network.nodes:
                if self.rng.random() < self.packet_rate:
                    self.stats['packets_generated'] += 1
                    dest = self.rng.choice([n for n in self.network.nodes if n != i])
                    packet = Packet(source=i, destination=dest, creation_time=t)
                    if not self.network.nodes[i].receive_packet(packet, t):
                        pass

            # Packet Processing and Forwarding
            for i in self.network.nodes:
                node = self.network.nodes[i]
                packets_to_process = min(len(node.queue), node.processing_capacity)

                for _ in range(packets_to_process):
                    if not node.queue: break
                    packet = node.queue.popleft()

                    if packet.destination == i:
                        self.stats['packets_delivered'] += 1
                        self.stats['total_latency'] += (t - packet.creation_time)
                    else:
                        next_hop = self.algorithm.get_next_hop(i, packet.destination, self.network)
                        if next_hop is not None and next_hop in self.network.nodes:
                            packet.path.append(next_hop)
                            if not self.network.nodes[next_hop].receive_packet(packet, t):
                                pass
                        else:
                            pass

        # Final Stats Calculation
        throughput = self.stats['packets_delivered'] / self.sim_duration
        packet_loss_rate = (self.stats['packets_generated'] - self.stats['packets_delivered']) / self.stats['packets_generated'] if self.stats['packets_generated'] > 0 else 0
        avg_latency = self.stats['total_latency'] / self.stats['packets_delivered'] if self.stats['packets_delivered'] > 0 else 0

        return {
            'throughput': throughput,
            'packet_loss_rate': packet_loss_rate,
            'avg_latency': avg_latency
        }