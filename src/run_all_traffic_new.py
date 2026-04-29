# -*- coding: utf-8 -*-
# ==============================================================================
# SRA & Comparative Protocols - Automated Two-Phase Suite (v4 - Matplotlib Styles)
#
# 描述:
# - 自动化两阶段工作流脚本：
#   1) 首次运行：执行仿真并保存CSV
#   2) 后续运行：跳过仿真，直接从CSV读取并绘图
#
# 本版修改:
# - 绘图阶段不再使用 seaborn.lineplot 的自动配色/线型
# - 改为 matplotlib 的 ax.plot，严格按用户指定的线条样式绘制
# ==============================================================================

import simpy
import networkx as nx
import numpy as np
import pandas as pd
import random
import os
import matplotlib.pyplot as plt
from tqdm import tqdm


# ==============================================================================
# 1. 全局绘图风格设置 (Publication Quality)
# ==============================================================================
# 1) 英文/数字：Times New Roman 作为默认字体
import matplotlib as mpl
mpl.rcParams.update({
    # 关键：按顺序回退。英文/数字优先 Times；遇到中文就用 SimHei
    "font.family": ["Times New Roman", "SimHei"],

    # 可选：数学公式更像 Times（不影响中文）
    "mathtext.fontset": "stix",

    # 关键：导出 PDF/PS 时使用 TrueType，避免中文丢字/不嵌入
    "pdf.fonttype": 42,
    "ps.fonttype": 42,

    # 负号正常显示
    "axes.unicode_minus": False,
})

# ==============================================================================
# 2. 基础仿真框架 (与之前版本一致)
# ==============================================================================
class Packet:
    def __init__(self, packet_id, source, destination, creation_time):
        self.id, self.source, self.destination, self.creation_time = packet_id, source, destination, creation_time
        self.path, self.last_hop = [source], None

class BaseNetworkNode:
    def __init__(self, env, node_id, simulator):
        self.env, self.id, self.simulator = env, node_id, simulator
        self.processing_rate = simulator.params['node_params']['processing_rate']
        self.queue_capacity = simulator.params['node_params']['queue_capacity']
        self.queue = simpy.Store(env, capacity=self.queue_capacity)
        self.action = env.process(self.run())

    def run(self):
        raise NotImplementedError

    def put(self, packet):
        if len(self.queue.items) < self.queue_capacity:
            return self.queue.put(packet)
        else:
            self.simulator.log_drop()
            return None

class BaseTrafficSimulator:
    def __init__(self, env, graph, protocol, **params):
        self.env, self.graph, self.protocol, self.params = env, graph.copy(), protocol, params
        self.NodeClass = BaseNetworkNode
        self.nodes, self.packet_counter = {}, 0
        self.warmup_end = params.get('warmup_duration', 0)
        self.measure_end = self.warmup_end + params.get('measure_duration', 1000)
        self.drain_end = self.measure_end + params.get('drain_duration', 0)
        self.protocol_params = params.get('protocol_params', {})
        self.stats = {
            'packets_generated': 0,
            'packets_delivered': 0,
            'packets_dropped': 0,
            'total_latency': 0.0
        }

    def init_nodes(self):
        self.nodes = {node_id: self.NodeClass(self.env, node_id, self) for node_id in self.graph.nodes()}

    def packet_generator(self, rate_per_node):
        while True:
            total_rate = rate_per_node * self.graph.number_of_nodes()
            if total_rate == 0:
                yield self.env.timeout(1.0)
                continue
            yield self.env.timeout(random.expovariate(total_rate))

            if self.env.now < self.measure_end:
                source, dest = random.sample(list(self.graph.nodes()), 2)
                if self.is_in_measure_phase():
                    self.stats['packets_generated'] += 1
                self.packet_counter += 1
                self.nodes[source].put(Packet(self.packet_counter, source, dest, self.env.now))

    def is_in_measure_phase(self):
        return self.warmup_end <= self.env.now < self.measure_end

    def log_delivery(self, packet):
        if self.is_in_measure_phase():
            self.stats['packets_delivered'] += 1
            self.stats['total_latency'] += (self.env.now - packet.creation_time)

    def log_drop(self):
        if self.is_in_measure_phase():
            self.stats['packets_dropped'] += 1

    def run(self, packet_gen_rate_per_node):
        self.env.process(self.packet_generator(packet_gen_rate_per_node))
        self.env.run(until=self.drain_end)
        return self.collect_results()

    def collect_results(self):
        throughput = self.stats['packets_delivered'] / self.params['measure_duration']
        total_gen = self.stats['packets_generated']
        drop_rate = self.stats['packets_dropped'] / total_gen if total_gen > 0 else 0
        avg_latency = (self.stats['total_latency'] / self.stats['packets_delivered']
                       if self.stats['packets_delivered'] > 0 else 0)
        return {'throughput': throughput, 'drop_rate': drop_rate, 'avg_latency': avg_latency}

# ---------------- Dijkstra ----------------
class DijkstraNode(BaseNetworkNode):
    def run(self):
        while True:
            packet = yield self.queue.get()
            yield self.env.timeout(1.0 / self.processing_rate)
            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.routing_tables[self.id].get(packet.destination)
                if next_hop:
                    self.simulator.nodes[next_hop].put(packet)
                else:
                    self.simulator.log_drop()

class DijkstraSimulator(BaseTrafficSimulator):
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = DijkstraNode
        self.init_nodes()
        self.routing_tables = {}
        for s_node in self.graph.nodes():
            try:
                _, paths = nx.single_source_dijkstra(self.graph, s_node)
                self.routing_tables[s_node] = {d: p[1] for d, p in paths.items() if len(p) > 1}
            except nx.NetworkXNoPath:
                self.routing_tables[s_node] = {}

# ---------------- LIRP-D ----------------
class LIRPNode(BaseNetworkNode):
    def run(self):
        while True:
            packet = yield self.queue.get()
            yield self.env.timeout(1.0 / self.processing_rate)
            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.get_next_hop(self.id, packet)
                if next_hop:
                    self.simulator.nodes[next_hop].put(packet)
                else:
                    self.simulator.log_drop()

class LIRPDSimulator(BaseTrafficSimulator):
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = LIRPNode
        self.init_nodes()
        self.hop_distances = dict(nx.all_pairs_shortest_path_length(self.graph))

    def get_next_hop(self, current_node_id, packet):
        dest = packet.destination
        neighbors = list(self.graph.neighbors(current_node_id))
        if not neighbors:
            return None
        current_dist = self.hop_distances[current_node_id].get(dest, float('inf'))
        closer_neighbors = [n for n in neighbors if self.hop_distances[n].get(dest, float('inf')) < current_dist]
        if not closer_neighbors:
            return None
        return min(closer_neighbors, key=lambda n: len(self.nodes[n].queue.items))

# ---------------- Q-Routing ----------------
class QRouteNode(BaseNetworkNode):
    def run(self):
        while True:
            packet = yield self.queue.get()
            yield self.env.timeout(1.0 / self.processing_rate)
            if packet.last_hop is not None:
                self.simulator.update_q_table(packet.last_hop, self.id, packet.destination)

            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.get_next_hop(self.id, packet)
                if next_hop:
                    packet.last_hop = self.id
                    self.simulator.nodes[next_hop].put(packet)
                else:
                    self.simulator.log_drop()

class QRoutingSimulator(BaseTrafficSimulator):
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = QRouteNode
        self.init_nodes()
        hops = dict(nx.all_pairs_shortest_path_length(self.graph))
        self.q_tables = {
            n: {
                neighbor: {d: float(hops[neighbor].get(d, len(self.graph.nodes()))) for d in self.graph.nodes()}
                for neighbor in self.graph.neighbors(n)
            }
            for n in self.graph.nodes()
        }
        self.epsilon = self.protocol_params.get('epsilon', 0.3)

    def get_next_hop(self, current_node_id, packet):
        dest = packet.destination
        neighbors = list(self.graph.neighbors(current_node_id))
        if not neighbors:
            return None
        if random.random() < self.epsilon:
            return random.choice(neighbors)
        valid_neighbors = [n for n in neighbors if n != packet.last_hop]
        if not valid_neighbors:
            valid_neighbors = neighbors
        q_values = {n: self.q_tables[current_node_id][n][dest] for n in valid_neighbors}
        return min(q_values, key=q_values.get)

    def update_q_table(self, from_node, to_node, dest):
        alpha = self.protocol_params.get('alpha', 0.1)
        gamma = self.protocol_params.get('gamma', 0.9)
        cost = (1.0 / self.nodes[to_node].processing_rate) + (len(self.nodes[to_node].queue.items) / self.nodes[to_node].processing_rate)

        min_q = 0.0
        if to_node != dest and list(self.graph.neighbors(to_node)):
            min_q = min(self.q_tables[to_node][n][dest] for n in self.graph.neighbors(to_node))

        current_q = self.q_tables[from_node][to_node][dest]
        self.q_tables[from_node][to_node][dest] = current_q + alpha * (cost + gamma * min_q - current_q)

# ---------------- SRA ----------------
class SRANode(BaseNetworkNode):
    def run(self):
        while True:
            packet = yield self.queue.get()
            yield self.env.timeout(1.0 / self.processing_rate)
            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.routing_tables[self.id].get(packet.destination)
                if next_hop:
                    self.simulator.nodes[next_hop].put(packet)
                else:
                    self.simulator.log_drop()

class SRASimulator(BaseTrafficSimulator):
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = SRANode
        self.init_nodes()
        self.accumulated_stress = {n: 0.0 for n in self.graph.nodes()}
        self.node_costs = {n: 1.0 for n in self.graph.nodes()}
        self.routing_tables = {n: {} for n in self.graph.nodes()}
        self.env.process(self.sra_updater())

    def sra_updater(self):
        update_interval = self.protocol_params.get('update_interval', 50)
        self.relax_network_step()
        while self.env.now < self.params['warmup_duration']:
            yield self.env.timeout(update_interval)
            self.relax_network_step()

    def relax_network_step(self):
        alpha = self.protocol_params.get('alpha', 0.1)
        beta_i = self.protocol_params.get('beta_I', 10.0)

        for u, v in self.graph.edges():
            self.graph.edges[u, v]['weight'] = self.node_costs[u] + self.node_costs[v]

        current_bc = nx.betweenness_centrality(self.graph, weight='weight', normalized=True)

        for s_node in self.graph.nodes():
            try:
                _, paths = nx.single_source_dijkstra(self.graph, s_node, weight='weight')
                self.routing_tables[s_node] = {d: p[1] for d, p in paths.items() if len(p) > 1}
            except nx.NetworkXNoPath:
                self.routing_tables[s_node] = {}

        max_bc = max(current_bc.values()) if current_bc else 1.0
        if max_bc == 0:
            max_bc = 1.0

        for n_id in self.graph.nodes():
            norm_bc = current_bc.get(n_id, 0.0) / max_bc
            self.accumulated_stress[n_id] = (1 - alpha) * self.accumulated_stress[n_id] + alpha * norm_bc
            self.node_costs[n_id] = 1 + beta_i * self.accumulated_stress[n_id]

# ==============================================================================
# 3. 工作流函数
# ==============================================================================
def run_simulation_phase(network_generators, protocols, params, output_csv_path):
    """运行所有仿真并将结果保存到单个CSV文件。"""
    master_results = []

    for network_name, G_generator in network_generators.items():
        print(f"\n{'='*70}\n>>> 开始处理网络拓扑: {network_name}\n{'='*70}")
        G = G_generator()
        G_CONN = G.subgraph(max(nx.connected_components(G), key=len)).copy()

        for proto_name, (SimClass, proto_params) in protocols.items():
            for load in tqdm(params['load_levels'], desc=f'  Simulating {proto_name}', unit='load'):
                sim_params = {'node_params': params['node_params'], **proto_params, **params['sim_phases']}
                env = simpy.Environment()
                simulator = SimClass(env, G_CONN, proto_name, **sim_params)
                macro_data = simulator.run(packet_gen_rate_per_node=load)
                macro_data.update({'protocol': proto_name, 'load': load, 'network_type': network_name})
                master_results.append(macro_data)

    master_df = pd.DataFrame(master_results)
    master_df.to_csv(output_csv_path, index=False)
    print(f"\n>>> 所有仿真结果已成功保存至: {output_csv_path}")

def plot_generation_phase(input_csv_path, output_dir):
    """从CSV文件读取数据并生成所有图表（使用 matplotlib 固定曲线样式）。"""
    print(f"\n--- 正在从 '{input_csv_path}' 读取数据并生成图表 ---")
    all_results_df = pd.read_csv(input_csv_path)

    # 按你要求的样式固定：颜色 + marker（空心）
    style_map = {
        'Dijkstra':  dict(color='r', marker='o'),
        'LIRP-D':    dict(color='g', marker='^'),
        'Q-Routing': dict(color='y', marker='*'),
        'SRA':       dict(color='b', marker='d'),
    }

    metrics = [
        ('throughput', '(a)吞吐量', '吞吐量(Packets/Timestep)'),
        ('drop_rate',  '(b)丢包率',     '丢包率(%)'),
        ('avg_latency','(c)平均时延',   '平均时延(Timesteps)'),
    ]

    for network_name in sorted(all_results_df['network_type'].unique()):
        print(f"  - 正在为 {network_name} 网络绘图...")
        results_df = all_results_df[all_results_df['network_type'] == network_name].copy()

        fig, axes = plt.subplots(1, 3, figsize=(10, 3))

        for ax, (ycol, title, ylabel) in zip(axes, metrics):
            for proto, st in style_map.items():
                dfp = results_df[results_df['protocol'] == proto].sort_values('load')
                if dfp.empty:
                    continue
                ax.plot(
                    dfp['load'], dfp[ycol],
                    linewidth=1,                # 这里用数字 1（不要用字符串 '1'）
                    marker=st['marker'],
                    markerfacecolor='none',     # 空心 marker
                    color=st['color'],
                    label=proto
                )

            ax.set_title(title)
            ax.set_xlabel('网络负载')
            ax.set_ylabel(ylabel)
            ax.grid(True, which='both', linestyle=':', linewidth=0.5)

        # 丢包率显示为百分比
        axes[1].yaxis.set_major_formatter(plt.FuncFormatter('{:.0%}'.format))

        # 图例只放在第一个子图（论文更干净）
        axes[0].legend(loc='upper left', title='路由协议', fontsize=9)

        plt.tight_layout()

        filename = f"performance_comparison_{network_name.lower()}.pdf"
        plt.savefig(os.path.join(output_dir, filename))
        plt.close()
        print(f"    - 组合图已保存: {filename}")

    print(f"\n>>> 所有图表已成功生成并保存在 '{output_dir}' 文件夹中。")

# ==============================================================================
# 4. 主程序
# ==============================================================================
def main():
    """主执行函数，自动化两阶段工作流。"""
    PARAMS = {
        'load_levels': np.linspace(0.1, 1.4, 14),
        'sim_phases': {'warmup_duration': 300, 'measure_duration': 1700, 'drain_duration': 500},
        'node_params': {'processing_rate': 10, 'queue_capacity': 50}
    }

    Q_ROUTING_PARAMS = {'alpha': 0.1, 'gamma': 0.9, 'epsilon': 0.3}
    SRA_PARAMS = {'alpha': 0.1, 'beta_I': 10.0, 'update_interval': 50}

    PROTOCOLS = {
        'Dijkstra': (DijkstraSimulator, {}),
        'LIRP-D': (LIRPDSimulator, {}),
        'Q-Routing': (QRoutingSimulator, {'protocol_params': Q_ROUTING_PARAMS}),
        'SRA': (SRASimulator, {'protocol_params': SRA_PARAMS})
    }

    NETWORK_GENERATORS = {
        'BA': lambda: nx.barabasi_albert_graph(100, m=4, seed=42),
        'WS': lambda: nx.watts_strogatz_graph(100, k=8, p=0.1, seed=42),
        'ER': lambda: nx.erdos_renyi_graph(100, p=0.1, seed=42)
    }

    OUTPUT_DIR = "publication_figures"
    OUTPUT_CSV = os.path.join(OUTPUT_DIR, "dynamic_traffic_summary_results.csv")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 自动化工作流：有CSV就跳过仿真
    if not os.path.exists(OUTPUT_CSV):
        print("--- [PHASE 1] 结果文件未找到，开始执行完整仿真... ---")
        run_simulation_phase(NETWORK_GENERATORS, PROTOCOLS, PARAMS, OUTPUT_CSV)
    else:
        print("--- [PHASE 1] 结果文件已存在，跳过仿真。 ---")

    print("\n--- [PHASE 2] 开始从CSV文件生成图表... ---")
    plot_generation_phase(OUTPUT_CSV, OUTPUT_DIR)

if __name__ == "__main__":
    main()