# IV-C节 理论验证仿真脚本 - 出版级绘图优化版
# 仿真逻辑与PDF描述完全一致。
# 主要优化：提升图像清晰度、使用矢量PDF格式、遵循IEEE出版风格。

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import os
import warnings

# --- 修改1: 全局美化设置，使用更适合论文的风格和字体 ---
plt.rcParams['font.sans-serif']=['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 忽略 networkx 中关于 all_shortest_paths 的未来警告
warnings.filterwarnings("ignore", category=FutureWarning, module='networkx')

class SRA_Simulator:
    """ SRA 算法模拟器，用于理论验证 (与您版本逻辑一致) """
    def __init__(self, G, alpha, beta_I, T_d=1):
        self.G = G.copy()
        self.nodes = list(G.nodes())
        self.node_map = {node: i for i, node in enumerate(self.nodes)}
        self.num_nodes = len(self.nodes)
        self.alpha = alpha
        self.beta_I = beta_I
        self.T_d = T_d
        self.S = np.zeros(self.num_nodes)
        self.history = {'S': [], 'c': [], 'V': [], 'switched': []}
        self.dwell_counter = 0
        self.last_paths_hash = None
        self.frozen_c = None

    def _get_all_shortest_paths_hash(self):
        node_costs = {node: 1 + self.beta_I * self.S[self.node_map[node]] for node in self.nodes}
        for u, v in self.G.edges():
            self.G.edges[u, v]['cost'] = node_costs[u] + node_costs[v]
        paths_tuples = []
        sorted_nodes = sorted(self.nodes)
        for i in range(len(sorted_nodes)):
            for j in range(i + 1, len(sorted_nodes)):
                s, t = sorted_nodes[i], sorted_nodes[j]
                try:
                    sp = tuple(sorted([tuple(p) for p in nx.all_shortest_paths(self.G, source=s, target=t, weight='cost')]))
                    paths_tuples.append(((s,t), sp))
                except nx.NetworkXNoPath:
                    continue
        return hash(tuple(paths_tuples))

    def _calculate_betweenness_centrality(self):
        bc = nx.betweenness_centrality(self.G, weight='cost', normalized=False)
        return np.array([bc.get(node, 0.0) for node in self.nodes])

    def _calculate_lyapunov_V(self, S_k, c_k):
        return np.sum((S_k - c_k)**2)

    def run(self, max_iter=200):
        for k in tqdm(range(max_iter), desc=f"Running SRA (Td={self.T_d})"):
            switched_this_step = False
            if self.dwell_counter > 0:
                c_k = self.frozen_c
                self.dwell_counter -= 1
            else:
                current_paths_hash = self._get_all_shortest_paths_hash()
                if self.last_paths_hash is not None and current_paths_hash != self.last_paths_hash:
                    switched_this_step = True
                    self.dwell_counter = self.T_d - 1
                self.last_paths_hash = current_paths_hash
                kappa_k = self._calculate_betweenness_centrality()
                max_kappa = np.max(kappa_k)
                c_k = kappa_k / max_kappa if max_kappa > 0 else np.zeros_like(kappa_k)
                if switched_this_step:
                    self.frozen_c = c_k
            
            self.history['S'].append(self.S.copy())
            self.history['c'].append(c_k)
            self.history['V'].append(self._calculate_lyapunov_V(self.S, c_k))
            self.history['switched'].append(switched_this_step)
            self.S = (1 - self.alpha) * self.S + self.alpha * c_k
        return self.history

def estimate_delta_bar(history):
    switch_indices = np.where(history['switched'])[0]
    if len(switch_indices) < 2: return 0.1
    c_history = np.array(history['c'])
    max_delta_sq = 0.0
    for idx in switch_indices:
        if idx > 0:
            delta_sq = np.sum((c_history[idx] - c_history[idx-1])**2)
            if delta_sq > max_delta_sq:
                max_delta_sq = delta_sq
    return np.sqrt(max_delta_sq) if max_delta_sq > 0 else 0.1

def plot_lyapunov_dynamics(history, delta_bar, alpha, output_dir, zoom_range=(20, 50)):
    """ 绘制图2：Lyapunov 动态过程（中文论文版） """
    V_history = np.array(history['V'])
    switch_points = np.where(history['switched'])[0]
    iterations = np.arange(len(V_history))
    final_radius = (delta_bar**2) / (alpha**2)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7))
    fig.suptitle('Lyapunov函数$V(S)$的动态演化过程', fontsize=14, fontweight='bold')

    # --- 子图 (a): 全局收敛 ---
    ax1.plot(iterations, V_history,
                 label='Lyapunov函数值$V(S)$',
                 color='dodgerblue', zorder=2, linewidth=1.5)
    ax1.set_yscale('log')
    ax1.scatter(switch_points, V_history[switch_points],
                color='red', marker='^',
                label='路径切换时刻',
                zorder=3, s=40, edgecolor='k', linewidth=0.5)

    ax1.axhline(y=final_radius,
                color='black', linestyle='--',
                label=f'理论上界$V_{{lim}}$={final_radius:.2f}')

    ax1.set_ylabel('$V(S)$(对数坐标)')
    ax1.set_title('（a）全局收敛性与理论上界验证')
    ax1.legend(fontsize=12)

    # --- 子图 (b): 局部降-跳 ---
    start, end = zoom_range
    ax2.plot(iterations[start:end],
             V_history[start:end], '-o',
             label='$V(S)$',
             color='dodgerblue', markersize=5, zorder=2)

    zoom_switches = switch_points[(switch_points >= start) & (switch_points < end)]
    ax2.scatter(zoom_switches,
                V_history[zoom_switches],
                color='red', marker='^',
                s=80, label='路径切换时刻',
                edgecolor='k', linewidth=0.5, zorder=3)

    ax2.set_xlabel('迭代次数$k$', fontweight='bold')
    ax2.set_ylabel('$V(S)$(线性坐标)')
    ax2.set_title(f'（b）局部“下降—跳跃”动态特性(第{start}-{end}次迭代）')
    ax2.legend(fontsize=12)
    ax2.set_ylim(bottom=0)

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    output_filename = os.path.join(output_dir, '图2_Lyapunov动态.pdf')
    plt.savefig(output_filename, format='pdf', dpi=300, bbox_inches='tight')
    plt.show()

def plot_dwell_time_effect(history_td1, history_td5, output_dir, convergence_range=(100, 200)):
    """ 绘制图3：最小驻留时间对稳定性的影响（中文论文版） """
    V_td1 = np.array(history_td1['V'])
    V_td5 = np.array(history_td5['V'])

    start, end = convergence_range
    iterations = np.arange(start, end)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    fig.suptitle('最小驻留时间 $T_d$ 对系统稳定性的影响', fontsize=14, fontweight='bold')

    # Td=5
    ax1.plot(iterations, V_td5[start:end],
             label='($T_d=5$)',
             color='green', linewidth=1.5)
    ax1.set_ylabel('$V(S)$')
    ax1.set_title('(a)按块收敛特性')
    ax1.legend(loc='upper right',fontsize=12)
    ax1.grid(True, ls=":", alpha=0.6)

    # Td=1
    ax2.plot(iterations, V_td1[start:end],
             label='($T_d=1$)',
             color='mediumblue', linewidth=1.5)
    ax2.set_xlabel('迭代次数$k$', fontweight='bold')
    ax2.set_ylabel('$V(S)$')
    ax2.set_title('(b)高频振荡现象(局部放大)')
    plt.ylim(0.002,0.033)
    ax2.legend(loc='upper right',fontsize=12)
    ax2.grid(True, ls=":", alpha=0.6)

    plt.tight_layout(rect=[0, 0, 1, 0.94])

    output_filename = os.path.join(output_dir, '图3_驻留时间影响.pdf')
    plt.savefig(output_filename, format='pdf', dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == '__main__':
    OUTPUT_DIR = "sra_simulation_plots"
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    print(f"Figures will be saved in the '{OUTPUT_DIR}' directory.")

    # --- 仿真参数 (与Table II一致) ---
    N = 100
    M = 4 # BA网络的m参数
    ALPHA = 0.1
    BETA_I = 10.0
    MAX_ITER = 200
    
    G_BA = nx.barabasi_albert_graph(N, M, seed=42)

    print("\n--- Running experiment: Td=1 (Base SRA) ---")
    sim_td1 = SRA_Simulator(G_BA, alpha=ALPHA, beta_I=BETA_I, T_d=1)
    history_td1 = sim_td1.run(max_iter=MAX_ITER)

    print("\n--- Running experiment: Td=5 (Stabilized SRA) ---")
    sim_td5 = SRA_Simulator(G_BA, alpha=ALPHA, beta_I=BETA_I, T_d=5)
    history_td5 = sim_td5.run(max_iter=MAX_ITER)

    delta_bar_estimated = estimate_delta_bar(history_td1)
    print(f"\n--- Estimated Delta_bar from simulation ≈ {delta_bar_estimated:.4f} ---")

    print("\n--- Generating Figure 2: Lyapunov Dynamics ---")
    plot_lyapunov_dynamics(history_td1, delta_bar_estimated, ALPHA, OUTPUT_DIR, zoom_range=(20, 50))

    print("\n--- Generating Figure 3: Dwell Time Effect ---")
    plot_dwell_time_effect(history_td1, history_td5, OUTPUT_DIR, convergence_range=(100, MAX_ITER))