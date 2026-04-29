# IV-B节 理论验证仿真脚本 - 出版级绘图优化版
# 仿真逻辑与Table II参数完全保持不变。
# 主要优化：提升图像清晰度、使用矢量PDF格式、遵循IEEE出版风格。

import networkx as nx
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import linregress
from tqdm import tqdm
import random
from collections import defaultdict

# --- SRA 算法核心实现 (与之前版本完全相同) ---
def run_sra(graph, alpha=0.1, beta_i=10.0, max_iter=200, tol=1e-5):
    num_nodes = graph.number_of_nodes()
    nodes = list(graph.nodes())
    node_map = {node: i for i, node in enumerate(nodes)}
    S = np.zeros(num_nodes)
    C = np.ones(num_nodes)
    for k in range(max_iter):
        for u, v in graph.edges():
            cost_u = C[node_map[u]]
            cost_v = C[node_map[v]]
            graph.edges[u, v]['weight'] = (cost_u + cost_v) / 2.0
        bc_dict = nx.betweenness_centrality(graph, k=None, normalized=False, weight='weight', endpoints=False)
        kappa = np.array([bc_dict.get(node, 0) for node in nodes])
        kappa_max = np.max(kappa)
        if kappa_max > 0:
            norm_kappa = kappa / kappa_max
        else:
            norm_kappa = np.zeros(num_nodes)
        S_prev = S.copy()
        S = (1 - alpha) * S + alpha * norm_kappa
        C = 1 + beta_i * S
        if np.linalg.norm(S - S_prev, np.inf) < tol:
            break
    return C

# --- 独立性能测量代码 (与之前版本完全相同) ---
def get_all_shortest_paths_info(G, weight):
    paths_info = defaultdict(list)
    nodes = list(G.nodes())
    for s in nodes:
        for t in nodes:
            if s == t: continue
            try:
                all_paths = list(nx.all_shortest_paths(G, s, t, weight=weight))
                paths_info[(s, t)] = all_paths
            except nx.NetworkXNoPath:
                continue
    return paths_info

def simulate_rho_crit(G, weight_key='weight', mu=1.0, T=2000, warmup=300, tol=0.02, seed=None):
    nodes = list(G.nodes())
    mu_map = {v: float(mu) for v in nodes}
    if weight_key is None or not G.edges or weight_key not in G.edges[list(G.edges)[0]]:
        paths_info = get_all_shortest_paths_info(G, weight=None)
    else:
        paths_info = get_all_shortest_paths_info(G, weight=weight_key)
    
    pairs = list(paths_info.keys())
    P = len(pairs)
    if P == 0: return 0.0
    rng = np.random.default_rng(seed)

    def stable_at(rho, local_rng):
            # 定义内部函数，检查给定吞吐量rho下网络是否稳定。
            Q = {v: 0.0 for v in nodes}
            # 初始化每个节点的队列长度（排队等待的数据包数量）为0。
            totalQ_hist = []
            # 创建一个列表，用于存储每个时间步的网络总队列长度。
            lam_pair = rho / P
            # 将总吞吐量rho平均分配给所有节点对，计算每个节点对的平均数据包到达速率。
            for t in range(T):
                # 模拟T个时间步。
                arrivals = local_rng.poisson(lam_pair, size=P)
                # 模拟一个时间步内，每个节点对的数据包到达数量（服从泊松分布）。
                for i, (s, tgt) in enumerate(pairs):
                    if arrivals[i] > 0:
                        # 如果有数据包到达。
                        shortest_paths = paths_info.get((s, tgt), [])
                        num_paths = len(shortest_paths)
                        # 获取该节点对之间的最短路径数量。
                        if num_paths == 0: continue
                        # 如果没有最短路径，跳过。
                        share = arrivals[i] / num_paths
                        # 数据包被平均分配到所有最短路径上。
                        for path in shortest_paths:
                            for v in path[1:-1]:
                                # 对于路径上的每个中间节点（不包括源和目标节点）。
                                Q[v] += share
                                # 将数据包数量累加到该节点的队列中。
                for v in nodes:
                    departures = local_rng.poisson(mu_map[v])
                    # 模拟一个时间步内，每个节点的服务（出队）数量。
                    Q[v] = max(0, Q[v] - departures)
                    # 更新节点的队列长度，确保其不为负数。
                if t >= warmup:
                    # 在预热期结束后，开始记录数据。
                    totalQ_hist.append(sum(Q.values()))
                    # 将所有节点的队列长度之和（网络总队列长度）记录下来。
            y = np.array(totalQ_hist)
            # 将总队列长度历史记录转换为NumPy数组。
            x = np.arange(len(y))
            # 创建时间步索引数组。
            if len(y) < 50: return True
            # 如果数据点太少，直接返回稳定。
            coef = np.polyfit(x, y, 1)[0]
            # 对总队列长度历史数据进行线性回归，获取斜率。斜率代表队列的增长趋势。
            return coef <= tol
            # 如果斜率小于等于容忍度，认为网络是稳定的。
        
    lo, hi = 0.0, 10.0 * mu
    for _ in range(20):
        mid = 0.5 * (lo + hi)
        if mid < 1e-9: break
        if stable_at(mid, rng):
            lo = mid
        else:
            hi = mid
    return lo

# --- 主仿真逻辑 (与之前版本完全相同) ---
def main():
    num_samples = 100
    results = []
    print("开始执行大规模仿真 (出版级绘图优化版)...")
    for i in tqdm(range(num_samples)):
        topo_type = random.choice(['ba', 'ws'])
        N = random.randint(40, 60)
        if topo_type == 'ba':
            G = nx.barabasi_albert_graph(N, 2, seed=i)
        else: # ws
            G = nx.watts_strogatz_graph(N, 4, 0.1, seed=i)
        if not nx.is_connected(G):
            largest_cc = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_cc).copy()
        if G.number_of_nodes() < 10: continue
        
        G_initial = G.copy()
        bc_initial_dict = nx.betweenness_centrality(G_initial, normalized=False, endpoints=False)
        kappa_max_initial = np.max(list(bc_initial_dict.values())) if bc_initial_dict else 0
        if kappa_max_initial == 0: continue
        
        G_sra = G.copy()
        final_costs = run_sra(G_sra)
        node_map = {node: i for i, node in enumerate(G_sra.nodes())}
        for u, v in G_sra.edges():
            G_sra.edges[u, v]['weight'] = (final_costs[node_map[u]] + final_costs[node_map[v]]) / 2.0
        bc_final_dict = nx.betweenness_centrality(G_sra, weight='weight', normalized=False, endpoints=False)
        kappa_max_final = np.max(list(bc_final_dict.values())) if bc_final_dict else 0
        if kappa_max_final == 0: continue
        
        kappa_ratio = kappa_max_initial / kappa_max_final
        rho_crit_initial = simulate_rho_crit(G_initial, weight_key=None, seed=i)
        if rho_crit_initial < 1e-6: continue
        rho_crit_final = simulate_rho_crit(G_sra, weight_key='weight', seed=i)
        if rho_crit_final < 1e-6: continue
        rho_ratio = rho_crit_final / rho_crit_initial
        
        results.append({'kappa_ratio': kappa_ratio, 'rho_ratio': rho_ratio})

    if not results:
        print("仿真完成，但未能生成有效数据。")
        return
        
    df = pd.DataFrame(results)
    
    # ==============================================================================
    # --- 绘图部分 (核心修改区域) ---
    # ==============================================================================
    
    print("\n开始生成出版级质量图片...")
    
    # --- 修改1: 设置全局绘图风格以符合IEEE标准 ---
    plt.rcParams['font.sans-serif']=['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    # --- 创建图像 ---
    plt.figure(figsize=(6, 6)) # 调整图像尺寸
    
    # --- 修改2: 优化散点图元素，使其更清晰 ---
    sns.scatterplot(
        x='kappa_ratio', 
        y='rho_ratio', 
        data=df, 
        alpha=0.6, 
        label='独立实验测量结果',
        s=30, # 调整点的大小
        edgecolor='k', # 为点添加黑色描边
        linewidth=0.5
    )
    
    min_val = min(df['kappa_ratio'].min(), df['rho_ratio'].min()) * 0.9
    max_val = max(df['kappa_ratio'].max(), df['rho_ratio'].max()) * 1.1
    
    # --- 修改3: 优化线条，使其对比更鲜明 ---
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='理论预测线($y=x$)')
    
    slope, intercept, r_value, p_value, std_err = linregress(df['kappa_ratio'], df['rho_ratio'])
    sns.regplot(
        x='kappa_ratio', 
        y='rho_ratio', 
        data=df, 
        scatter=False, 
        line_kws={'linewidth': 1.5, 'linestyle': '--'}, 
        color='black', # 使用黑色拟合线更清晰
        label=f'线性回归拟合结果($R^2={r_value**2:.3f}$)'
    )

    # --- 修改4: 优化文字和标签 ---
    # plt.title('Validation: Measured Capacity vs. Structural Improvement', fontsize=14, fontweight='bold')
    plt.xlabel(r"峰值中心性比例($\kappa_{\max} / \kappa'_{\max}$)", fontsize=12, fontweight='bold')
    plt.ylabel(r"网络容量比例($\rho'_{crit} / \rho_{crit}$)", fontsize=12, fontweight='bold')
    plt.legend(loc='upper left',fontsize=12) # 调整图例位置
    plt.grid(True, linestyle=':', alpha=0.5) # 使用更淡的点状网格
    plt.axis('equal')
    plt.xlim(left=min_val)
    plt.ylim(bottom=min_val)
    plt.tight_layout()

    # --- 修改5: 输出为PDF矢量图格式，并遵循IEEE命名逻辑 ---
    # IEEE通常建议文件名格式为: <第一作者姓>_fig<图编号>.pdf
    # 这里我们使用一个清晰的文件名
    output_filename = 'ren_fig1_validation.pdf'
    plt.savefig(output_filename, format='pdf', dpi=300, bbox_inches='tight')
    
    print(f"图片已成功保存为高清晰度PDF文件: {output_filename}")
    plt.show()


if __name__ == '__main__':
    main()