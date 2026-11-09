# 文件名: run_experiments_final.py (已修正笔误)

import os
import pandas as pd
import numpy as np
import networkx as nx
import seaborn as sns  # <-- 这里是修正后的代码
import matplotlib.pyplot as plt
import simpy


# --------------------------------------------------------------------
# 1. 动态导入所有最终版的仿真器
# --------------------------------------------------------------------
try:
    from dijkstra_final import TrafficSimulator as DijkstraSimulator
    from lirp_d_final import TrafficSimulator as LIRPDSimulator
    from qroute_final import TrafficSimulator as QRoutingSimulator
    from sra_final import TrafficSimulator as SRASimulator
    print("成功导入所有最终版仿真器模块。")
except ImportError as e:
    print(f"错误：无法导入仿真器模块。请确保 'base_simulator.py' 和所有 '..._final.py' 文件存在于当前目录。")
    print(f"详细错误: {e}")
    exit()

# --------------------------------------------------------------------
# 2. 定义全局仿真参数
# --------------------------------------------------------------------
# 负载水平
LOAD_LEVELS = np.linspace(0.1, 1.5, 15)

# 仿真阶段时长 (秒)
SIMULATION_PHASES = {
    'warmup_duration': 500,
    'measure_duration': 1500,
    'drain_duration': 500
}

# 节点参数
NODE_PARAMS = {
    'processing_rate': 10,
    'queue_capacity': 50
}

# 协议特定参数
Q_ROUTING_PARAMS = {'alpha': 0.1, 'gamma': 0.9, 'epsilon': 0.3, 'epsilon_decay': 0.9999}
SRA_PARAMS = {'alpha': 0.1, 'beta_I': 10.0, 'update_interval': 50}

# 网络拓扑生成
print("正在生成BA无标度网络 (N=100, m=4)...")
ba_graph = nx.barabasi_albert_graph(100, m=4, seed=42)
G_CONN = ba_graph.subgraph(sorted(nx.connected_components(ba_graph), key=len, reverse=True)[0]).copy()
print(f"网络已生成，包含 {G_CONN.number_of_nodes()} 个节点和 {G_CONN.number_of_edges()} 条边。")


# --------------------------------------------------------------------
# 3. 实验执行主函数 (已更新)
# --------------------------------------------------------------------
def run_simulation_campaign():
    protocols_to_run = {
        'Dijkstra': (DijkstraSimulator, {}),
        'LIRP-D': (LIRPDSimulator, {}),
        'Q-Routing': (QRoutingSimulator, {'protocol_params': Q_ROUTING_PARAMS}),
        'SRA': (SRASimulator, {'protocol_params': SRA_PARAMS})
    }

    master_macro_results = []

    for protocol_name, (simulator_class, protocol_specific_params) in protocols_to_run.items():
        print(f"\n{'='*60}\n>>> 开始运行协议: {protocol_name}\n{'='*60}")

        # --- 创建详细的结果输出子目录 ---
        output_dir = f"results_{protocol_name}"
        timeseries_dir = os.path.join(output_dir, "timeseries")
        nodes_dir = os.path.join(output_dir, "nodes")
        links_dir = os.path.join(output_dir, "links")
        os.makedirs(timeseries_dir, exist_ok=True)
        os.makedirs(nodes_dir, exist_ok=True)
        os.makedirs(links_dir, exist_ok=True)

        protocol_aggregate_results = []

        for load in LOAD_LEVELS:
            print(f"\n  - 正在仿真负载: {load:.2f}...")

            simulation_params = {
                'node_params': NODE_PARAMS, **protocol_specific_params, **SIMULATION_PHASES
            }

            env = simpy.Environment()
            simulator = simulator_class(env, G_CONN, protocol_name, **simulation_params)

            result = simulator.run(packet_gen_rate_per_node=load)

            # --- 分别提取并保存四类数据 ---
            # A. 提取宏观数据
            macro_data = result['macro']
            macro_data.update({'protocol': protocol_name, 'load': load})
            protocol_aggregate_results.append(macro_data)
            master_macro_results.append(macro_data)

            # B. 保存时间序列数据
            result['timeseries'].to_csv(os.path.join(timeseries_dir, f"timeseries_load_{load:.2f}.csv"), index=False)

            # C. 保存节点行为数据
            result['nodes'].to_csv(os.path.join(nodes_dir, f"node_stats_load_{load:.2f}.csv"), index=False)

            # D. 保存链路行为数据
            if not result['links'].empty:
                result['links'].to_csv(os.path.join(links_dir, f"link_stats_load_{load:.2f}.csv"), index=False)

            print(f"    * 已保存负载 {load:.2f} 的 宏观、时间序列、节点及链路数据。")

        # 将当前协议的宏观结果汇总保存
        protocol_df = pd.DataFrame(protocol_aggregate_results)
        protocol_csv_path = os.path.join(output_dir, "aggregate_performance.csv")
        protocol_df.to_csv(protocol_csv_path, index=False)
        print(f"\n  >>> {protocol_name} 协议的宏观性能汇总已保存至: {protocol_csv_path}")

    print(f"\n{'='*60}\n>>> 所有仿真已完成!\n{'='*60}")

    return pd.DataFrame(master_macro_results)

# --------------------------------------------------------------------
# 4. 结果可视化函数 (无需修改)
# --------------------------------------------------------------------
def plot_comparison_results(results_df):
    """根据汇总的宏观性能数据，生成对比图。"""
    print("\n正在生成最终性能对比图...")

    sns.set(style="whitegrid", palette="deep", font_scale=1.2)
    fig, axes = plt.subplots(3, 1, figsize=(14, 20), sharex=True)
    fig.suptitle('Routing Protocol Performance Comparison on BA Network', fontsize=20, y=0.95)

    # 吞吐量
    sns.lineplot(data=results_df, x='load', y='throughput', hue='protocol', style='protocol', markers=True, dashes=False, ax=axes[0])
    axes[0].set_title('(a) Network Throughput vs. Load')
    axes[0].set_ylabel('Throughput (Packets/Timestep)')

    # 丢包率
    sns.lineplot(data=results_df, x='load', y='drop_rate', hue='protocol', style='protocol', markers=True, dashes=False, ax=axes[1])
    axes[1].set_title('(b) Packet Drop Rate vs. Load')
    axes[1].set_ylabel('Packet Drop Rate')
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter('{:.0%}'.format))

    # 平均延迟
    sns.lineplot(data=results_df, x='load', y='avg_latency', hue='protocol', style='protocol', markers=True, dashes=False, ax=axes[2])
    axes[2].set_title('(c) Average Packet Latency vs. Load')
    axes[2].set_ylabel('Average Latency (Timesteps)')
    axes[2].set_xlabel('Network Load (Packet Generation Rate per Node)')

    for ax in axes:
        ax.grid(True, which='both', linestyle='--')
        ax.legend(title='Protocol')

    plt.tight_layout(rect=[0, 0, 1, 0.93])

    output_filename = "performance_comparison_final.png"
    plt.savefig(output_filename, dpi=300)
    print(f"性能对比图已成功保存为: {output_filename}")
    plt.show()

# --------------------------------------------------------------------
# 5. 主程序入口
# --------------------------------------------------------------------
if __name__ == "__main__":
    # 执行所有仿真
    final_results_df = run_simulation_campaign()

    # 如果有结果，则进行绘图
    if not final_results_df.empty:
        plot_comparison_results(final_results_df)
    else:
        print("没有生成任何仿真结果，无法绘图。")