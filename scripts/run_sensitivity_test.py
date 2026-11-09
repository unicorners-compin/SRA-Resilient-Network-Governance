# 文件名: run_sensitivity_test.py

import os
import pandas as pd
import numpy as np
import networkx as nx
import simpy
from tqdm import tqdm

# 我们只对SRA算法进行测试，因此只导入SRA的最终版仿真器
try:
    from sra_final import TrafficSimulator as SRASimulator
    print("成功导入SRA仿真器模块 (sra_final.py)。")
except ImportError as e:
    print("错误：无法导入SRA仿真器。请确保 'base_simulator.py' 和 'sra_final.py' 文件存在于当前目录。")
    print(f"详细错误: {e}")
    exit()

def main():
    print("--- 开始执行SRA算法参数敏感性分析 ---")

    # --- 仿真参数 ---
    # 定义要扫描的参数网格
    # Alpha (α): 学习率/阻尼因子
    ALPHA_LEVELS = np.linspace(0.05, 0.5, 10) # 扫描10个α值
    # Beta_I (β_I): 积分项增益
    BETA_I_LEVELS = np.linspace(5, 50, 10) # 扫描10个β值

    # 固定其他仿真参数
    LOAD_LEVEL = 0.8 # 在一个具有挑战性的固定负载下测试
    SIMULATION_PHASES = {'warmup_duration': 500, 'measure_duration': 1500, 'drain_duration': 500}
    NODE_PARAMS = {'processing_rate': 10, 'queue_capacity': 50}

    # 创建网络拓扑
    G_base = nx.barabasi_albert_graph(100, m=4, seed=42)
    G_base = G_base.subgraph(sorted(nx.connected_components(G_base), key=len, reverse=True)[0]).copy()

    # 创建输出目录
    output_dir = "results_sensitivity"
    os.makedirs(output_dir, exist_ok=True)

    # 用于存储所有仿真结果的列表
    all_results = []

    # 创建一个总的迭代次数用于tqdm进度条
    total_runs = len(ALPHA_LEVELS) * len(BETA_I_LEVELS)
    print(f"\n将要进行 {total_runs} 次独立的仿真运行，这可能需要较长时间...")

    with tqdm(total=total_runs) as pbar:
        # --- 主循环：遍历所有参数组合 ---
        for alpha in ALPHA_LEVELS:
            for beta_i in BETA_I_LEVELS:
                pbar.set_description(f"Testing α={alpha:.2f}, β_I={beta_i:.1f}")

                # 设置当前要测试的SRA参数
                sra_params = {
                    'alpha': alpha,
                    'beta_I': beta_i,
                    'update_interval': 50
                }

                simulation_params = {
                    'node_params': NODE_PARAMS,
                    'protocol_params': sra_params,
                    **SIMULATION_PHASES
                }

                env = simpy.Environment()
                simulator = SRASimulator(env, G_base, 'SRA', **simulation_params)

                # 运行仿真，我们只需要宏观结果
                result = simulator.run(packet_gen_rate_per_node=LOAD_LEVEL)

                # 记录本次运行的参数和结果
                macro_result = result['macro']
                macro_result['alpha'] = alpha
                macro_result['beta_I'] = beta_i
                all_results.append(macro_result)

                pbar.update(1)

    # --- 数据整理与保存 ---
    print("\n\n--- 所有仿真已完成，正在整理并保存结果... ---")

    # 将结果列表转换为DataFrame
    results_df = pd.DataFrame(all_results)

    # 保存到CSV文件
    output_csv_path = os.path.join(output_dir, "sensitivity_analysis_results.csv")
    results_df.to_csv(output_csv_path, index=False)

    print(f"\n--- 参数敏感性分析数据已成功保存至: {output_csv_path} ---")
    print("您可以将此CSV文件发送给我，以便进行热力图可视化和最终分析。")

if __name__ == '__main__':
    main()