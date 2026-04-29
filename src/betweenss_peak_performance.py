# -*- coding: utf-8 -*-
"""
用于SRA论文的出版级图表生成脚本
功能: 
1. 运行SRA仿真，记录峰值中心性和平均路径长度的演化历史。
2. 生成图4 (峰值中心性演化), 图5 (平均路径长度演化)。
3. 生成图6, 7, 8 (优化前后的中心性分布对比)。
4. 所有图表均保存为高质量、符合IEEE出版风格的PDF矢量文件。
"""
import networkx as nx
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import os

# =============================================================================
# 1. 全局绘图风格设置 (Publication Quality)
# =============================================================================
# 设置字体和字号以匹配LaTeX论文的通用风格 (Times New Roman)
plt.rcParams['font.sans-serif']=['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# =============================================================================
# 2. 核心仿真与计算函数
# =============================================================================

def get_avg_path_length_from_policy(graph, node_costs):
    """
    根据给定的节点成本（路由策略），计算网络在此策略下的平均路径长度（物理跳数）。
    注意：这是一个计算密集型操作。
    """
    total_length = 0
    path_count = 0
    
    # 我们为每个节点计算一次最短路径树
    # weight函数将节点成本转换为边成本
    path_lengths = dict(nx.all_pairs_dijkstra_path_length(
        graph, 
        weight=lambda u, v, d: (node_costs.get(u, 1.0) + node_costs.get(v, 1.0)) / 2
    ))

    # 计算这些最短路径的物理跳数
    nodes = list(graph.nodes())
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            source, target = nodes[i], nodes[j]
            try:
                # 找到基于成本的最短路径
                path = nx.dijkstra_path(
                    graph, 
                    source, 
                    target, 
                    weight=lambda u, v, d: (node_costs.get(u, 1.0) + node_costs.get(v, 1.0)) / 2
                )
                total_length += len(path) - 1  # 路径的跳数是节点数-1
                path_count += 1
            except (nx.NetworkXNoPath, KeyError):
                continue
    
    return total_length / path_count if path_count > 0 else 0


def run_sra_evolution(graph, alpha, beta_i, max_iterations):
    """
    运行SRA算法，返回演化历史（包括峰值中心性和平均路径长度）。
    """
    num_nodes = graph.number_of_nodes()
    S = np.zeros(num_nodes)
    node_list = list(graph.nodes())
    node_map = {node: i for i, node in enumerate(node_list)}
    
    history = {'iteration': [], 'peak_centrality': [], 'average_path_length': []}

    # --- 初始状态 (k=0) ---
    C_k = {node: 1.0 for node in node_list}
    # 使用networkx的精确BC计算初始状态
    initial_bc_dict = nx.betweenness_centrality(graph, normalized=False)
    initial_bc_vec = np.array([initial_bc_dict.get(node, 0) for node in node_list])
    initial_apl = nx.average_shortest_path_length(graph)

    history['iteration'].append(0)
    history['peak_centrality'].append(initial_bc_vec.max())
    history['average_path_length'].append(initial_apl)

    print(f"  演化开始 (k=0): Peak BC={initial_bc_vec.max():.2f}, Avg Path Length={initial_apl:.4f}")

    # --- 演化过程 ---
    for k in tqdm(range(1, max_iterations), desc="  SRA Iterating", unit="iter"):
        # 1. 计算当前成本C_k下的中心性kappa_k
        # 在真实应用中，这步非常耗时。这里我们使用networkx的加权BC作为估计。
        g_temp = graph.copy()
        for u, v in g_temp.edges():
            cost_u = C_k.get(u, 1.0)
            cost_v = C_k.get(v, 1.0)
            g_temp.edges[u,v]['sra_cost'] = (cost_u + cost_v) / 2
        
        bc_dict_k = nx.betweenness_centrality(g_temp, weight='sra_cost', normalized=False)
        kappa_k = np.array([bc_dict_k.get(node, 0) for node in node_list])
        
        # 2. 更新累积压力S
        max_kappa = kappa_k.max()
        if max_kappa > 0:
            kappa_norm = kappa_k / max_kappa
            S = (1 - alpha) * S + alpha * kappa_norm
        
        # 3. 计算下一轮的成本C_{k+1}
        C_k_plus_1 = {node_list[i]: (1 + beta_i * S[i]) for i in range(num_nodes)}
        
        # 4. 记录当前状态的指标
        current_apl = get_avg_path_length_from_policy(graph, C_k)
        
        history['iteration'].append(k)
        history['peak_centrality'].append(max_kappa)
        history['average_path_length'].append(current_apl)
        
        # 5. 更新成本以备下一轮使用
        C_k = C_k_plus_1
            
    final_node_costs = C_k
    return pd.DataFrame(history), final_node_costs

# =============================================================================
# 3. 主程序
# =============================================================================
if __name__ == "__main__":
    print("--- 开始为论文IV-D节生成结构性分析图表 ---")
    
    # --- 仿真参数 ---
    ALPHA = 0.1
    BETA_I = 10.0  # 与论文默认值一致
    MAX_ITERATIONS = 200
    OUTPUT_DIR = "publication_figures"

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # --- 网络设置 ---
    network_setups = {
        'ER': nx.erdos_renyi_graph(100, p=0.1, seed=42),
        'BA': nx.barabasi_albert_graph(100, m=4, seed=42),
        'WS': nx.watts_strogatz_graph(100, k=8, p=0.1, seed=42)
    }
    
    # --- 运行仿真 ---
    all_histories = {}
    initial_bcs = {}
    final_bcs = {}

    for name, G_orig in network_setups.items():
        print(f"\n[1/3] 正在处理网络: {name}")
        # 确保使用最大连通分量
        G = G_orig.subgraph(max(nx.connected_components(G_orig), key=len)).copy()
        
        # 计算初始中心性
        initial_bcs[name] = nx.betweenness_centrality(G, normalized=False)
        
        # 运行SRA演化
        history_df, final_costs = run_sra_evolution(G, alpha=ALPHA, beta_i=BETA_I, max_iterations=MAX_ITERATIONS)
        all_histories[name] = history_df
        
        # 计算最终中心性
        g_final = G.copy()
        for u, v in g_final.edges():
            g_final.edges[u,v]['final_cost'] = (final_costs.get(u,1) + final_costs.get(v,1)) / 2
        final_bcs[name] = nx.betweenness_centrality(g_final, weight='final_cost', normalized=False)

    # =========================================================================
    # 4. 生成图表
    # =========================================================================
    print("\n[2/3] 正在生成所有图表...")

    # --- 生成 图4: 峰值中心性演化 ---
    plt.figure(figsize=(6, 4)) # 标准单栏图尺寸
    styles = {'ER': ('blue', '-'), 'BA': ('red', '-'), 'WS': ('green', '-.')}
    for name, df in all_histories.items():
        plt.plot(df['iteration'], df['peak_centrality'], color=styles[name][0], label=name)
    plt.title('峰值介数中心性演化')
    plt.xlabel('迭代次数$k$')
    plt.ylabel('峰值中心性($\kappa_{max}$)')
    plt.legend(title='网络类型', loc='best', fontsize=12)
    plt.grid(True, linestyle=':', linewidth=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "figure_4_peak_centrality_evolution.pdf"))
    plt.close()
    print("  - 图4 已保存为 PDF。")

    # --- 生成 图5: 平均路径长度演化 ---
    plt.figure(figsize=(6, 4))
    for name, df in all_histories.items():
        plt.plot(df['iteration'], df['average_path_length'], color=styles[name][0], label=name)
    plt.title('平均路径长度动态演化')
    plt.xlabel('迭代次数$k$')
    plt.ylabel('平均路径长度(跳数)')
    plt.legend(title='网络类型', loc='best', fontsize=12)
    plt.grid(True, linestyle=':', linewidth=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "figure_5_avg_path_length_evolution.pdf"))
    plt.close()
    print("  - 图5 已保存为 PDF。")

    # --- 生成 图6, 7, 8: 中心性分布对比 ---
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), sharey=True) # 1x3子图布局
    network_order = ['ER', 'BA', 'WS']
    fig_labels = ['(a)', '(b)', '(c)']
    
    for i, name in enumerate(network_order):
        ax = axes[i]
        x0 = np.array(list(initial_bcs[name].values()), dtype=float)
        x1 = np.array(list(final_bcs[name].values()), dtype=float)

        sns.kdeplot(x=x0, ax=ax, color='red',   linestyle='--', label='初始状态(Dijkstra)')
        sns.kdeplot(x=x1, ax=ax, color='green', linestyle='-',  label='结束状态(SRA)')
        ax.set_title(f'{fig_labels[i]} {name}模型中心性分布')
        ax.set_xlabel('介数中心性')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, linestyle=':', linewidth=0.5)
    
    # axes[0].set_ylabel('密度')
    plt.tight_layout()
    plt.ylabel('密度', fontsize=14)
    plt.savefig(os.path.join(OUTPUT_DIR, "figure_6_7_8_distributions.pdf"))
    plt.close()
    print("  - 图6, 7, 8 已合并保存为一个 PDF。")

    print(f"\n[3/3] 所有图表已成功生成并保存在 '{OUTPUT_DIR}' 文件夹中。")