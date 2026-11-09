# ==============================================================================
# SRA & Comparative Routing Protocols Simulation Suite (Multi-Topology Version)
#
# 描述:
# 这是一个支持多种网络拓扑（BA, WS, ER）的完整仿真脚本。
#
# 如何运行:
# 1. 确保已安装所需库: pip install simpy pandas networkx numpy seaborn matplotlib
# 2. 将此代码保存为单个 .py 文件 (例如, run_all_topologies.py)
# 3. 在终端中运行: python run_all_topologies.py
#    (注意：完整运行所有仿真需要较长时间)
#
# 核心修改:
# 1. [新增] 重构了主函数，使其可以循环遍历不同的网络拓扑。
# 2. [新增] 仿真和绘图函数被参数化，以接受不同的网络图和名称。
# 3. [新增] 为每种网络拓扑生成独立的性能对比图。
# ==============================================================================

import simpy
import networkx as nx
import numpy as np
import pandas as pd
from collections import deque, defaultdict
import random
import os
import seaborn as sns
import matplotlib.pyplot as plt

# ==============================================================================
# 1. 基础仿真框架 (无修改)
# ... (从原始文件中复制第1部分代码, 此处省略以保持简洁)
# ==============================================================================
class Packet:
    """定义数据包对象"""
    def __init__(self, packet_id, source, destination, creation_time):
        self.id = packet_id
        self.source = source
        self.destination = destination
        self.creation_time = creation_time
        self.path = [source]
        self.last_hop = None

class BaseNetworkNode:
    """定义网络节点对象的基类"""
    def __init__(self, env, node_id, simulator):
        self.env = env
        self.id = node_id
        self.simulator = simulator
        self.processing_rate = simulator.params['node_params']['processing_rate']
        self.queue_capacity = simulator.params['node_params']['queue_capacity']
        self.queue = simpy.Store(env, capacity=self.queue_capacity)
        self.action = env.process(self.run())
        self.packets_processed = 0
        self.packets_dropped = 0
        self.packets_out = 0
        self.queue_lengths = []

    def run(self):
        raise NotImplementedError("每个协议的Node子类必须实现run方法。")

    def put(self, packet):
        if len(self.queue.items) < self.queue_capacity:
            return self.queue.put(packet)
        else:
            self.simulator.log_drop()
            if self.simulator.is_in_measure_phase():
                self.packets_dropped += 1
            return None

    def update_queue_stats(self):
        if self.simulator.is_in_measure_phase():
            self.queue_lengths.append(len(self.queue.items))

class BaseTrafficSimulator:
    """网络流量仿真器的核心基类"""
    def __init__(self, env, graph, protocol, **params):
        self.env = env
        self.graph = graph.copy()
        self.protocol = protocol
        self.params = params
        self.NodeClass = BaseNetworkNode
        self.nodes = {}
        self.packet_counter = 0
        self.warmup_end = params.get('warmup_duration', 0)
        self.measure_end = self.warmup_end + params.get('measure_duration', 1000)
        self.drain_end = self.measure_end + params.get('drain_duration', 0)
        self.protocol_params = params.get('protocol_params', {})
        self.stats = {'packets_generated': 0, 'packets_delivered': 0, 'packets_dropped': 0, 'total_latency': 0.0, 'hop_counts': []}
        self.link_usage = defaultdict(int)
        self.timeseries_data = []

    def init_nodes(self):
        self.nodes = {node_id: self.NodeClass(self.env, node_id, self) for node_id in self.graph.nodes()}

    def packet_generator(self, rate_per_node):
        while True:
            total_rate = rate_per_node * self.graph.number_of_nodes()
            if total_rate == 0:
                yield self.env.timeout(1.0)
                continue
            inter_arrival_time = random.expovariate(total_rate)
            yield self.env.timeout(inter_arrival_time)
            if self.env.now < self.measure_end:
                source, destination = random.sample(list(self.graph.nodes()), 2)
                if self.is_in_measure_phase():
                    self.stats['packets_generated'] += 1
                self.packet_counter += 1
                packet = Packet(self.packet_counter, source, destination, self.env.now)
                self.nodes[source].put(packet)

    def monitor(self, interval=10):
        while True:
            if self.is_in_measure_phase():
                q_lengths = [len(node.queue.items) for node in self.nodes.values()]
                self.timeseries_data.append({
                    'timestamp': self.env.now, 'avg_queue_length': np.mean(q_lengths),
                    'max_queue_length': np.max(q_lengths), 'packets_delivered': self.stats['packets_delivered'],
                    'packets_dropped': self.stats['packets_dropped']
                })
            yield self.env.timeout(interval)

    def is_in_measure_phase(self):
        return self.warmup_end <= self.env.now < self.measure_end

    def log_delivery(self, packet):
        if self.is_in_measure_phase():
            self.stats['packets_delivered'] += 1
            self.stats['total_latency'] += (self.env.now - packet.creation_time)
            self.stats['hop_counts'].append(len(packet.path) - 1)

    def log_drop(self):
        if self.is_in_measure_phase():
            self.stats['packets_dropped'] += 1

    def log_link_usage(self, u, v):
        if self.is_in_measure_phase():
            self.link_usage[tuple(sorted((u, v)))] += 1

    def run(self, packet_gen_rate_per_node):
        self.env.process(self.packet_generator(packet_gen_rate_per_node))
        self.env.process(self.monitor())
        self.env.run(until=self.drain_end)
        return self.collect_results()

    def collect_results(self):
        throughput = self.stats['packets_delivered'] / self.params['measure_duration']
        total_generated = self.stats['packets_generated']
        drop_rate = self.stats['packets_dropped'] / total_generated if total_generated > 0 else 0
        avg_latency = self.stats['total_latency'] / self.stats['packets_delivered'] if self.stats['packets_delivered'] > 0 else 0
        avg_hops = np.mean(self.stats['hop_counts']) if self.stats['hop_counts'] else 0
        macro_results = {'throughput': throughput, 'drop_rate': drop_rate, 'avg_latency': avg_latency, 'avg_hops': avg_hops}
        timeseries_df = pd.DataFrame(self.timeseries_data)
        node_data = [{'node_id': nid, 'avg_queue_length': np.mean(n.queue_lengths) if n.queue_lengths else 0,
                      'packets_dropped': n.packets_dropped} for nid, n in self.nodes.items()]
        nodes_df = pd.DataFrame(node_data)
        link_data = [{'link': link, 'usage_count': count} for link, count in self.link_usage.items()]
        links_df = pd.DataFrame(link_data)
        return {'macro': macro_results, 'timeseries': timeseries_df, 'nodes': nodes_df, 'links': links_df}

# ==============================================================================
# 2. Dijkstra 协议实现 (无修改)
# ... (从原始文件中复制第2部分代码, 此处省略以保持简洁)
# ==============================================================================
class DijkstraNode(BaseNetworkNode):
    def run(self):
        while True:
            packet = yield self.queue.get()
            self.update_queue_stats()
            yield self.env.timeout(1.0 / self.processing_rate)
            if self.simulator.is_in_measure_phase(): self.packets_processed += 1
            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.routing_tables[self.id].get(packet.destination)
                if next_hop:
                    self.simulator.log_link_usage(self.id, next_hop)
                    if self.simulator.is_in_measure_phase(): self.packets_out += 1
                    self.simulator.nodes[next_hop].put(packet)
                else:
                    self.simulator.log_drop()
                    if self.simulator.is_in_measure_phase(): self.packets_dropped += 1

class DijkstraSimulator(BaseTrafficSimulator):
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = DijkstraNode
        self.init_nodes()
        print("  - 正在预计算静态Dijkstra路由表...")
        self.routing_tables = {}
        for source_node in self.graph.nodes():
            try:
                _, paths = nx.single_source_dijkstra(self.graph, source_node)
                self.routing_tables[source_node] = {dest: path[1] for dest, path in paths.items() if len(path) > 1}
            except nx.NetworkXNoPath:
                self.routing_tables[source_node] = {}

# ==============================================================================
# 3. LIRP-D 协议实现 (无修改)
# ... (从原始文件中复制第3部分代码, 此处省略以保持简洁)
# ==============================================================================
class LIRPNode(BaseNetworkNode):
    def run(self):
        while True:
            packet = yield self.queue.get()
            self.update_queue_stats()
            yield self.env.timeout(1.0 / self.processing_rate)
            if self.simulator.is_in_measure_phase(): self.packets_processed += 1
            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.get_next_hop(self.id, packet)
                if next_hop:
                    self.simulator.log_link_usage(self.id, next_hop)
                    if self.simulator.is_in_measure_phase(): self.packets_out += 1
                    self.simulator.nodes[next_hop].put(packet)
                else:
                    self.simulator.log_drop()
                    if self.simulator.is_in_measure_phase(): self.packets_dropped += 1

class LIRPDSimulator(BaseTrafficSimulator):
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = LIRPNode
        self.init_nodes()
        print("  - 正在为LIRP-D预计算跳数距离...")
        self.hop_distances = dict(nx.all_pairs_shortest_path_length(self.graph))

    def get_next_hop(self, current_node_id, packet):
        dest = packet.destination
        neighbors = list(self.graph.neighbors(current_node_id))
        if not neighbors: return None
        current_dist = self.hop_distances[current_node_id].get(dest, float('inf'))
        closer_neighbors = [n for n in neighbors if self.hop_distances[n].get(dest, float('inf')) < current_dist]
        if not closer_neighbors: return None
        return min(closer_neighbors, key=lambda n: len(self.nodes[n].queue.items))

# ==============================================================================
# 4. Q-Routing 协议实现 (无修改)
# ... (从原始文件中复制第4部分代码, 此处省略以保持简洁)
# ==============================================================================
class QRouteNode(BaseNetworkNode):
    def run(self):
        while True:
            packet = yield self.queue.get()
            self.update_queue_stats()
            yield self.env.timeout(1.0 / self.processing_rate)
            if packet.last_hop is not None:
                self.simulator.update_q_table(packet.last_hop, self.id, packet.destination)
            if self.simulator.is_in_measure_phase(): self.packets_processed += 1
            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.get_next_hop(self.id, packet)
                if next_hop:
                    packet.last_hop = self.id
                    self.simulator.log_link_usage(self.id, next_hop)
                    if self.simulator.is_in_measure_phase(): self.packets_out += 1
                    self.simulator.nodes[next_hop].put(packet)
                else:
                    self.simulator.log_drop()
                    if self.simulator.is_in_measure_phase(): self.packets_dropped += 1

class QRoutingSimulator(BaseTrafficSimulator):
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = QRouteNode
        self.init_nodes()
        print("  - 正在使用跳数启发式初始化Q-Tables...")
        hop_distances = dict(nx.all_pairs_shortest_path_length(self.graph))
        self.q_tables = {n: {neighbor: {dest: float(hop_distances[neighbor].get(dest, len(self.graph.nodes())))
                                         for dest in self.graph.nodes()} for neighbor in self.graph.neighbors(n)}
                         for n in self.graph.nodes()}
        self.epsilon = self.protocol_params.get('epsilon', 0.3)

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

# ==============================================================================
# 5. SRA 协议实现 (无修改)
# ... (从原始文件中复制第5部分代码, 此处省略以保持简洁)
# ==============================================================================
class SRANode(BaseNetworkNode):
    def run(self):
        while True:
            packet = yield self.queue.get()
            self.update_queue_stats()
            yield self.env.timeout(1.0 / self.processing_rate)
            if self.simulator.is_in_measure_phase(): self.packets_processed += 1
            if packet.destination == self.id:
                self.simulator.log_delivery(packet)
            else:
                next_hop = self.simulator.routing_tables[self.id].get(packet.destination)
                if next_hop:
                    self.simulator.log_link_usage(self.id, next_hop)
                    if self.simulator.is_in_measure_phase(): self.packets_out += 1
                    self.simulator.nodes[next_hop].put(packet)
                else:
                    self.simulator.log_drop()
                    if self.simulator.is_in_measure_phase(): self.packets_dropped += 1

class SRASimulator(BaseTrafficSimulator):
    def __init__(self, env, graph, protocol, **params):
        super().__init__(env, graph, protocol, **params)
        self.NodeClass = SRANode
        self.init_nodes()
        self.accumulated_stress = {node: 0.0 for node in self.graph.nodes()}
        self.node_costs = {node: 1.0 for node in self.graph.nodes()}
        self.routing_tables = {node: {} for node in self.graph.nodes()}
        self.env.process(self.sra_updater())

    def sra_updater(self):
        update_interval = self.protocol_params.get('update_interval', 50)
        print("  - SRA后台更新进程已启动...")
        # 确保在流量开始前至少有一次路由计算
        self.relax_network_step()
        while self.env.now < self.params['warmup_duration']:
            yield self.env.timeout(update_interval)
            self.relax_network_step()
        print("  - SRA预热期收敛完成。路由表已固定。")

    def relax_network_step(self):
        alpha = self.protocol_params.get('alpha', 0.1)
        beta_i = self.protocol_params.get('beta_I', 10.0)

        # --- **核心Bug修正** ---
        # 1. 根据节点成本正确地、对称地设置边权重
        for u, v in self.graph.edges():
            self.graph.edges[u,v]['weight'] = self.node_costs[u] + self.node_costs[v]

        # 2. 计算加权中心性
        current_bc = nx.betweenness_centrality(self.graph, weight='weight', normalized=True)

        # 3. 更新所有节点的路由表
        for source_node in self.graph.nodes():
            try:
                _, paths = nx.single_source_dijkstra(self.graph, source_node, weight='weight')
                self.routing_tables[source_node] = {dest: path[1] for dest, path in paths.items() if len(path) > 1}
            except nx.NetworkXNoPath:
                self.routing_tables[source_node] = {}

        # 4. 更新累积应力和节点成本
        max_bc = max(current_bc.values()) if current_bc else 1.0
        if max_bc == 0: max_bc = 1.0
        for node_id in self.graph.nodes():
            norm_bc = current_bc.get(node_id, 0.0) / max_bc
            self.accumulated_stress[node_id] = (1 - alpha) * self.accumulated_stress[node_id] + alpha * norm_bc
            self.node_costs[node_id] = 1 + beta_i * self.accumulated_stress[node_id]


# ==============================================================================
# 6. 实验运行与可视化 (已修改)
# ==============================================================================

# --- MODIFICATION START ---
# 将仿真流程封装成一个函数，接收图和其名称作为参数
def run_simulation_campaign(graph_to_test, network_name):
    """
    为给定的网络图运行所有协议的仿真。
    :param graph_to_test: 要测试的NetworkX图对象。
    :param network_name: 图的名称（如 'BA', 'WS', 'ER'），用于日志记录。
    :return: 包含所有宏观结果的Pandas DataFrame。
    """
    protocols_to_run = {
        'Dijkstra': (DijkstraSimulator, {}), 'LIRP-D': (LIRPDSimulator, {}),
        'Q-Routing': (QRoutingSimulator, {'protocol_params': Q_ROUTING_PARAMS}),
        'SRA': (SRASimulator, {'protocol_params': SRA_PARAMS})
    }
    master_macro_results = []

    print(f"\n{'='*80}\n>>> 开始为 {network_name} 网络运行仿真活动\n{'='*80}")

    for protocol_name, (simulator_class, protocol_specific_params) in protocols_to_run.items():
        print(f"\n--- 开始运行协议: {protocol_name} on {network_name} ---")
        for load in LOAD_LEVELS:
            print(f"  - 正在仿真负载: {load:.2f}...")
            # 创建一个新的图副本以确保每次仿真环境独立
            current_graph = graph_to_test.copy()
            simulation_params = {'node_params': NODE_PARAMS, **protocol_specific_params, **SIMULATION_PHASES}
            env = simpy.Environment()
            simulator = simulator_class(env, current_graph, protocol_name, **simulation_params)
            result = simulator.run(packet_gen_rate_per_node=load)
            macro_data = result['macro']
            macro_data.update({'protocol': protocol_name, 'load': load, 'network': network_name})
            master_macro_results.append(macro_data)

    print(f"\n{'='*80}\n>>> {network_name} 网络的仿真活动已完成!\n{'='*80}")
    return pd.DataFrame(master_macro_results)

# 将绘图函数也参数化，以生成特定于网络拓扑的图表
def plot_comparison_results(results_df, network_type_str):
    """
    为给定的结果数据框生成并保存性能对比图。
    :param results_df: 包含仿真结果的DataFrame。
    :param network_type_str: 网络类型字符串（'BA', 'WS', 'ER'），用于图表标题和文件名。
    """
    print(f"\n正在为 {network_type_str} 网络生成最终性能对比图...")
    sns.set(style="whitegrid", palette="deep", font_scale=1.2)
    fig, axes = plt.subplots(3, 1, figsize=(14, 20), sharex=True)
    fig.suptitle(f'Routing Protocol Performance Comparison on {network_type_str} Network', fontsize=20, y=0.95)

    # 筛选出特定网络的数据进行绘图
    data_to_plot = results_df[results_df['network'] == network_type_str]

    sns.lineplot(data=data_to_plot, x='load', y='throughput', hue='protocol', style='protocol', markers=True, dashes=False, ax=axes[0])
    axes[0].set_title('(a) Network Throughput vs. Load')
    axes[0].set_ylabel('Throughput (Packets/Timestep)')

    sns.lineplot(data=data_to_plot, x='load', y='drop_rate', hue='protocol', style='protocol', markers=True, dashes=False, ax=axes[1])
    axes[1].set_title('(b) Packet Drop Rate vs. Load')
    axes[1].set_ylabel('Packet Drop Rate')
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter('{:.0%}'.format))

    sns.lineplot(data=data_to_plot, x='load', y='avg_latency', hue='protocol', style='protocol', markers=True, dashes=False, ax=axes[2])
    axes[2].set_title('(c) Average Packet Latency vs. Load')
    axes[2].set_ylabel('Average Latency (Timesteps)')
    axes[2].set_xlabel('Network Load (Packet Generation Rate per Node)')

    for ax in axes:
        ax.grid(True, which='both', linestyle='--')
        ax.legend(title='Protocol')
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    # 使用网络名称命名输出文件，避免覆盖
    output_filename = f"performance_comparison_{network_type_str}.png"
    plt.savefig(output_filename, dpi=300)
    print(f"性能对比图已成功保存为: {output_filename}")
    # plt.show() # 在批量运行时可以注释掉此行，避免弹出窗口中断流程
    plt.close(fig) # 关闭图形，释放内存

if __name__ == "__main__":
    # --- 全局参数定义 ---
    LOAD_LEVELS = np.linspace(0.1, 1.5, 15)
    SIMULATION_PHASES = {'warmup_duration': 500, 'measure_duration': 1500, 'drain_duration': 500}
    NODE_PARAMS = {'processing_rate': 10, 'queue_capacity': 50}
    Q_ROUTING_PARAMS = {'alpha': 0.1, 'gamma': 0.9, 'epsilon': 0.3, 'epsilon_decay': 0.9999}
    SRA_PARAMS = {'alpha': 0.1, 'beta_I': 10.0, 'update_interval': 50}
    N_NODES = 100
    RANDOM_SEED = 42

    # --- 生成所有需要的网络拓扑 ---
    print("正在生成网络拓扑...")
    # BA 无标度网络 (m=4)
    ba_graph_raw = nx.barabasi_albert_graph(N_NODES, m=4, seed=RANDOM_SEED)

    # WS 小世界网络 (k=8, p=0.1)
    ws_graph_raw = nx.watts_strogatz_graph(N_NODES, k=8, p=0.1, seed=RANDOM_SEED)

    # ER 随机网络 (p=0.1)
    er_graph_raw = nx.erdos_renyi_graph(N_NODES, p=0.1, seed=RANDOM_SEED)

    networks_to_test = {
        "BA": ba_graph_raw,
        "WS": ws_graph_raw,
        "ER": er_graph_raw
    }

    all_results = []

    # --- 为每种拓扑运行完整的仿真活动 ---
    for name, graph_raw in networks_to_test.items():
        # 确保网络是连通的，只在最大连通分量上进行仿真
        connected_components = list(nx.connected_components(graph_raw))
        if not connected_components:
            print(f"警告: {name} 网络为空或不连通，跳过此拓扑。")
            continue

        g_conn = graph_raw.subgraph(max(connected_components, key=len)).copy()
        print(f"\n已准备好 {name} 网络，包含 {g_conn.number_of_nodes()} 个节点和 {g_conn.number_of_edges()} 条边。")

        # 运行仿真并收集结果
        results_df = run_simulation_campaign(g_conn, name)
        all_results.append(results_df)

    # --- 组合所有结果并绘图 ---
    if all_results:
        final_results_df = pd.concat(all_results, ignore_index=True)
        # 为每种网络拓扑分别绘制并保存图表
        for network_name in final_results_df['network'].unique():
            plot_comparison_results(final_results_df, network_name)
        print("\n所有仿真和绘图任务已全部完成！")
    else:
        print("没有生成任何仿真结果，无法绘图。")

# --- MODIFICATION END ---