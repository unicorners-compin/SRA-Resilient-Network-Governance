# -*- coding: utf-8 -*-
# ==============================================================================
# SRA Robustness Analysis - Statistically Robust Version
#
# 需求实现:
# 1) 中文: SimHei；英文/数字: Times New Roman（并保证 PDF 不丢中文）
# 2) 线条样式: 从 {o, ^, *, d} 里选（这里用 ^ / o / d），marker 为空心
# 3) 自动两阶段：无CSV则跑仿真并保存；有CSV则直接绘图
# ==============================================================================

import os
import pandas as pd
import numpy as np
import networkx as nx
from tqdm import tqdm
import random
import matplotlib.pyplot as plt
import matplotlib as mpl

# ==============================================================================
# 1. 全局参数 & 字体/绘图风格设置
# ==============================================================================
NUM_SIMULATION_RUNS = 50  # 运行次数

# --- 字体混排 & PDF 防丢字 ---
# 关键点：
# - font.family 写成列表：优先 Times New Roman（英文/数字），遇中文回退 SimHei
# - pdf.fonttype=42：TrueType嵌入，避免中文在PDF里丢失/变方块/空白
mpl.rcParams.update({
    "font.family": ["Times New Roman", "SimHei"],
    "font.size": 10,

    "axes.labelsize": 10,
    "axes.titlesize": 12,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,

    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.format": "pdf",

    "pdf.fonttype": 42,
    "ps.fonttype": 42,

    "axes.unicode_minus": False,
    "mathtext.fontset": "stix",  # 公式更接近Times风格（可选）
})

# ==============================================================================
# 2. 仿真核心逻辑
# ==============================================================================
def get_sra_policy(graph, alpha=0.1, beta_i=10.0, max_iter=200):
    num_nodes = graph.number_of_nodes()
    S = np.zeros(num_nodes)
    node_list = list(graph.nodes())

    for _ in range(max_iter):
        node_costs = {node_list[i]: 1 + beta_i * S[i] for i in range(num_nodes)}
        for u, v in graph.edges():
            graph.edges[u, v]['weight'] = node_costs[u] + node_costs[v]

        bc = nx.betweenness_centrality(graph, weight='weight', normalized=True)
        kappa = np.array([bc.get(node, 0.0) for node in node_list])
        max_kappa = kappa.max()
        if max_kappa > 0:
            S = (1 - alpha) * S + alpha * (kappa / max_kappa)

    final_costs = {node_list[i]: 1 + beta_i * S[i] for i in range(num_nodes)}
    routing_tables = {}
    for u, v in graph.edges():
        graph.edges[u, v]['weight'] = final_costs[u] + final_costs[v]

    for source_node in graph.nodes():
        try:
            _, paths = nx.single_source_dijkstra(graph, source_node, weight='weight')
            routing_tables[source_node] = {dest: path[1] for dest, path in paths.items() if len(path) > 1}
        except nx.NetworkXNoPath:
            routing_tables[source_node] = {}
    return routing_tables


def get_dijkstra_policy(graph):
    routing_tables = {}
    for source_node in graph.nodes():
        try:
            _, paths = nx.single_source_dijkstra(graph, source_node)
            routing_tables[source_node] = {dest: path[1] for dest, path in paths.items() if len(path) > 1}
        except nx.NetworkXNoPath:
            routing_tables[source_node] = {}
    return routing_tables


def calculate_pdr(graph, routing_policy, num_packets=2000):
    if graph.number_of_nodes() < 2:
        return 0.0

    delivered = 0
    nodes = list(graph.nodes())

    for _ in range(num_packets):
        source, dest = random.sample(nodes, 2)
        current_node = source

        # 最多走 N 跳，防止死循环
        for _ in range(graph.number_of_nodes()):
            if current_node == dest:
                delivered += 1
                break
            next_hop = routing_policy.get(current_node, {}).get(dest)
            if next_hop is None or next_hop not in graph.nodes():
                break
            current_node = next_hop

    return delivered / num_packets if num_packets > 0 else 0.0


def run_attack_campaign(graph, protocol_name, policy):
    results = []
    num_nodes_initial = graph.number_of_nodes()

    # 用初始 BC 做“定向攻击序列”
    initial_bc = nx.betweenness_centrality(graph, normalized=True)
    nodes_to_remove = sorted(initial_bc, key=initial_bc.get, reverse=True)

    g_attacked = graph.copy()
    remove_steps = int(num_nodes_initial * 0.4)

    for i in range(remove_steps):
        nodes_removed_percent = (i / num_nodes_initial) * 100.0

        pdr = calculate_pdr(g_attacked, policy)
        results.append({
            'protocol': protocol_name,
            'nodes_removed_percent': nodes_removed_percent,
            'pdr': pdr
        })

        if i < len(nodes_to_remove) and nodes_to_remove[i] in g_attacked:
            g_attacked.remove_node(nodes_to_remove[i])

    return pd.DataFrame(results)

# ==============================================================================
# 3. 工作流函数
# ==============================================================================
def run_and_save_robustness_data(network_generators, num_runs, output_csv_path):
    """PHASE 1: 运行所有抗毁性仿真并保存CSV。"""
    master_results = []

    for run_id in tqdm(range(num_runs), desc="Overall Simulation Progress"):
        for network_name, G_generator in network_generators.items():
            G = G_generator(seed=run_id)

            # 确保连通：取最大连通分量
            G_CONN = G.subgraph(max(nx.connected_components(G), key=len)).copy()

            # SRA
            sra_policy = get_sra_policy(G_CONN.copy())
            sra_results = run_attack_campaign(G_CONN.copy(), 'SRA', sra_policy)
            sra_results['network_type'] = network_name
            sra_results['run_id'] = run_id

            # Dijkstra
            dijkstra_policy = get_dijkstra_policy(G_CONN.copy())
            dijkstra_results = run_attack_campaign(G_CONN.copy(), 'Dijkstra', dijkstra_policy)
            dijkstra_results['network_type'] = network_name
            dijkstra_results['run_id'] = run_id

            master_results.extend([sra_results, dijkstra_results])

    master_df = pd.concat(master_results, ignore_index=True)
    master_df.to_csv(output_csv_path, index=False)
    print(f"\n>>> 所有 {num_runs} 次抗毁性仿真结果已成功保存至: {output_csv_path}")


def plot_advantage_from_csv(input_csv_path, output_dir):
    """PHASE 2: 从CSV读取数据，画均值曲线 + 标准差阴影。"""
    print(f"\n--- 正在从 '{input_csv_path}' 读取数据并生成图表 ---")
    results_df = pd.read_csv(input_csv_path)

    # pivot：每个(run, network, removed%)对齐 SRA / Dijkstra 的 pdr
    pivot_df = results_df.pivot_table(
        index=['run_id', 'network_type', 'nodes_removed_percent'],
        columns='protocol',
        values='pdr'
    ).reset_index()

    # 防止除零：Dijkstra=0 时 advantage 置为 NaN
    pivot_df['Dijkstra'] = pivot_df['Dijkstra'].replace(0, np.nan)
    pivot_df['advantage'] = ((pivot_df['SRA'] - pivot_df['Dijkstra']) / pivot_df['Dijkstra']) * 100.0

    # 统计：均值 + 标准差
    stats_df = pivot_df.groupby(['network_type', 'nodes_removed_percent'])['advantage'].agg(['mean', 'std']).reset_index()

    # --- 线型/marker：从你给的 {o, ^, *, d} 里选 ---
    # 这里用：BA '^'，WS 'o'，ER 'd'，并且 marker 空心
    marker_map = {'BA': '^', 'WS': 'o', 'ER': 'd'}

    # 颜色（你原本的配色）
    color_map = {'BA': 'royalblue', 'WS': 'forestgreen', 'ER': 'red'}

    plt.figure(figsize=(8, 5))
    ax = plt.gca()

    for network_name in ['BA', 'WS', 'ER']:
        network_data = stats_df[stats_df['network_type'] == network_name].sort_values('nodes_removed_percent')
        if network_data.empty:
            continue

        x_axis = network_data['nodes_removed_percent'].to_numpy()
        mean_line = network_data['mean'].to_numpy()
        std_line = network_data['std'].to_numpy()

        # 均值曲线
        ax.plot(
            x_axis, mean_line,
            linewidth=1.0,
            marker=marker_map.get(network_name, 'o'),
            markerfacecolor='none',          # 空心点
            markersize=4,
            color=color_map.get(network_name, 'black'),
            label=network_name
        )

        # 标准差阴影
        ax.fill_between(
            x_axis,
            mean_line - std_line,
            mean_line + std_line,
            color=color_map.get(network_name, 'gray'),
            alpha=0.15
        )

    # 标题/坐标轴（中文会走SimHei，英文数字走Times）
    # ax.set_title('SRA PDR Advantage vs. Dijkstra under Targeted Attack (50 Runs)')
    ax.set_xlabel('节点移除比例(%)')
    ax.set_ylabel('SRA PDR优势(%)')

    ax.axhline(0, color='black', linestyle='--', linewidth=0.75, alpha=0.8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, pos: f'{v:.0f}%'))
    ax.legend(title='网络模型', fontsize=12)
    ax.grid(True, which='both', linestyle=':', linewidth=0.5)

    plt.tight_layout()
    output_pdf_path = os.path.join(output_dir, "robustness_advantage_summary_stats.pdf")
    plt.savefig(output_pdf_path)
    plt.close()

    print(f"\n>>> 带置信区间的抗毁性优势对比图已成功保存至: {output_pdf_path}")

# ==============================================================================
# 4. 主程序
# ==============================================================================
def main():
    OUTPUT_DIR = "publication_figures"
    OUTPUT_CSV = os.path.join(OUTPUT_DIR, "robustness_analysis_full_results.csv")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    NETWORK_GENERATORS = {
        'BA': lambda seed: nx.barabasi_albert_graph(100, m=4, seed=seed),
        'WS': lambda seed: nx.watts_strogatz_graph(100, k=8, p=0.1, seed=seed),
        'ER': lambda seed: nx.erdos_renyi_graph(100, p=0.1, seed=seed)
    }

    if not os.path.exists(OUTPUT_CSV):
        print(f"--- [PHASE 1] 结果文件未找到，开始执行 {NUM_SIMULATION_RUNS} 次抗毁性仿真... ---")
        run_and_save_robustness_data(NETWORK_GENERATORS, NUM_SIMULATION_RUNS, OUTPUT_CSV)
    else:
        print("--- [PHASE 1] 结果文件已存在，跳过仿真。 ---")

    print("\n--- [PHASE 2] 开始从CSV文件生成图表... ---")
    plot_advantage_from_csv(OUTPUT_CSV, OUTPUT_DIR)

if __name__ == "__main__":
    main()