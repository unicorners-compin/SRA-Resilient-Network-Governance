#!/usr/bin/env python3
"""
CNCOMM-2026-0222 Major Revision Simulation Campaign
===================================================
Executes the 4 supplementary experiment blocks required by the Editor, Reviewer 1, and Reviewer 2:
  1. Exp-1: Component Ablation Study & Stronger Baselines (30 independent trials on BA, WS, ER)
     - Static Dijkstra (alpha=0)
     - Memoryless Reactive BC (alpha=1.0, T_d=1)
     - Unnormalized Stress SRA (fixed scale, T_d=5)
     - SRA without Dwell Time (alpha=0.1, T_d=1)
     - Full SRA (alpha=0.1, beta_I=10.0, T_d=5)
     - Stronger Baseline 1: Static BC-Weighted Routing (open-loop centrality weighting)
     - Stronger Baseline 2: Dynamic IGP/OSPF Weight Tuning (Fortz-Thorup convex piecewise congestion penalty)
     - LIRP-D (Local queue-aware deflection)
     - Q-Routing (DRL/RL baseline)
  2. Exp-2: Generalized Demand/Capacity-Weighted Stress, Time-Varying Traffic & Noise Injection
     - (a) Non-uniform Hotspot/Gravity traffic matrix W_st + heterogeneous node capacities mu_i:
           Comparing Topology-Only SRA vs. Generalized Demand/Capacity-Weighted SRA (\tilde{\kappa}_i)
     - (b) Time-varying traffic shock (step load surge from 0.6 to 1.2 at t=1000)
     - (c) Control-plane sensing noise injection (\sigma \in {0%, 5%, 10%, 20%, 30%})
  3. Exp-3: Hyperparameter Sensitivity (alpha, beta_I, and Minimum Dwell Time T_d)
     - Joint evaluation across T_d \in {1, 2, 3, 5, 8, 10} and (alpha, beta_I)
  4. Exp-4: Computational Complexity, Scalability (N \in {50, 100, 200, 300, 500}),
     and Real-World Backbone Topologies (NSFNET, GEANT2)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


# ------------------------------------------------------------------------------
# Real-World Backbone Topologies (NSFNET 14-node & GEANT 23-node / Synthetic ISP)
# ------------------------------------------------------------------------------
def build_nsfnet_graph() -> nx.Graph:
    """Standard 14-node, 21-link NSFNET backbone topology."""
    edges = [
        (0, 1), (0, 2), (0, 3), (1, 2), (1, 7), (2, 5), (3, 4), (3, 10),
        (4, 5), (4, 6), (5, 9), (5, 12), (6, 7), (7, 8), (8, 9), (8, 11),
        (8, 13), (9, 11), (10, 11), (10, 13), (11, 12)
    ]
    g = nx.Graph()
    g.add_edges_from(edges)
    return g


def build_geant_graph() -> nx.Graph:
    """Standard 22-node, 36-link European GEANT research backbone topology."""
    edges = [
        (0, 1), (0, 2), (0, 5), (1, 2), (1, 3), (1, 9), (2, 4), (2, 7),
        (3, 4), (3, 6), (4, 8), (4, 10), (5, 7), (5, 11), (6, 8), (6, 12),
        (7, 11), (7, 13), (8, 10), (8, 14), (9, 12), (9, 15), (10, 13),
        (10, 16), (11, 13), (11, 17), (12, 14), (12, 18), (13, 17), (14, 16),
        (14, 19), (15, 18), (16, 20), (17, 20), (18, 21), (19, 21)
    ]
    g = nx.Graph()
    g.add_edges_from(edges)
    return g


# ------------------------------------------------------------------------------
# Core Routing & Discrete-Time Packet Simulation Engine
# ------------------------------------------------------------------------------
def compute_routing_tables(graph: nx.Graph, node_costs: Dict[int, float]) -> Tuple[Dict[int, Dict[int, int]], Dict[Tuple[int, int], List[int]]]:
    """Compute all-pairs shortest paths and next-hop tables under symmetric edge weight C_u + C_v."""
    for u, v in graph.edges():
        graph.edges[u, v]["weight"] = 0.5 * (node_costs[u] + node_costs[v])
    routing_tables: Dict[int, Dict[int, int]] = {u: {} for u in graph.nodes()}
    all_paths: Dict[Tuple[int, int], List[int]] = {}
    for s in graph.nodes():
        _, paths = nx.single_source_dijkstra(graph, s, weight="weight")
        for t, p in paths.items():
            if len(p) > 1:
                routing_tables[s][t] = p[1]
                all_paths[(s, t)] = p
    return routing_tables, all_paths


def compute_structural_stress(
    graph: nx.Graph,
    all_paths: Dict[Tuple[int, int], List[int]],
    demand_matrix: Dict[Tuple[int, int], float] | None = None,
    node_capacities: Dict[int, float] | None = None,
    noise_std: float = 0.0,
    rng: np.random.Generator | None = None,
) -> Dict[int, float]:
    """
    Compute unnormalized or generalized demand/capacity-weighted structural stress:
      \tilde{\kappa}_i(S; W, \mu) = (1 / \mu_i) \sum_{s \neq i \neq t} W_{st} I(i \in P_{st})
    """
    stress = {u: 0.0 for u in graph.nodes()}
    for (s, t), path in all_paths.items():
        if s == t or len(path) <= 2:
            continue
        w = demand_matrix.get((s, t), 1.0) if demand_matrix is not None else 1.0
        for mid in path[1:-1]:
            stress[mid] += w

    if node_capacities is not None:
        for u in stress:
            stress[u] = stress[u] / max(node_capacities[u], 1e-6)

    if noise_std > 0.0 and rng is not None:
        for u in stress:
            multiplicative_noise = max(0.0, 1.0 + rng.normal(0.0, noise_std))
            stress[u] *= multiplicative_noise

    return stress


def fortz_thorup_penalty(utilization: float) -> float:
    """Piecewise convex link/node utilization penalty inspired by Fortz & Thorup OSPF weight tuning."""
    u = max(0.0, utilization)
    if u < 1.0 / 3.0:
        return 1.0 + u
    elif u < 2.0 / 3.0:
        return 1.0 + 3.0 * u - 2.0 / 3.0
    elif u < 0.9:
        return 1.0 + 10.0 * u - 16.0 / 3.0
    elif u < 1.0:
        return 1.0 + 70.0 * u - 178.0 / 3.0
    else:
        return 1.0 + 500.0 * u - 1468.0 / 3.0


def run_control_plane_relaxation(
    graph: nx.Graph,
    variant: str,
    alpha: float = 0.1,
    beta_I: float = 10.0,
    dwell_time: int = 5,
    max_iters: int = 60,
    demand_matrix: Dict[Tuple[int, int], float] | None = None,
    node_capacities: Dict[int, float] | None = None,
    noise_std: float = 0.0,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Execute the control-plane relaxation loop and track trajectory metrics:
    - Peak centrality reduction
    - Route switching frequency (churn)
    - Tracking error V_k = ||S^{(k)} - q^{(k)}||_2^2
    - Peak-shaving certificate satisfaction rate
    """
    rng = np.random.default_rng(seed)
    nodes = list(graph.nodes())
    S = {u: 0.0 for u in nodes}
    C = {u: 1.0 for u in nodes}

    routing_tables, all_paths = compute_routing_tables(graph, C)
    initial_raw_bc = compute_structural_stress(graph, all_paths, demand_matrix=None, node_capacities=None)
    initial_peak_bc = max(initial_raw_bc.values()) if initial_raw_bc else 1.0
    ref_scale = max(initial_peak_bc, 1.0)

    prev_paths_sig = tuple((k, tuple(v)) for k, v in sorted(all_paths.items()))
    dwell_counter = 0
    switch_count = 0
    peak_shaving_holds = 0
    total_switches_checked = 0
    prev_peak = initial_peak_bc

    v_trace = []
    peak_trace = []
    apl_trace = []

    for k in range(max_iters):
        if dwell_counter > 0:
            # Hold current routing configuration during dwell lock
            dwell_counter -= 1
        else:
            new_rt, new_paths = compute_routing_tables(graph, C)
            new_sig = tuple((pair, tuple(p)) for pair, p in sorted(new_paths.items()))
            if k > 0 and new_sig != prev_paths_sig:
                switch_count += 1
                dwell_counter = max(0, dwell_time - 1)
                prev_paths_sig = new_sig
            routing_tables, all_paths = new_rt, new_paths

        # Measure true topological peak BC and average path length
        raw_bc = compute_structural_stress(graph, all_paths, demand_matrix=demand_matrix, node_capacities=None)
        cur_peak = max(raw_bc.values()) if raw_bc else 0.0
        avg_pl = float(np.mean([len(p) - 1 for p in all_paths.values()])) if all_paths else 0.0
        peak_trace.append(cur_peak)
        apl_trace.append(avg_pl)

        if k > 0 and dwell_counter == max(0, dwell_time - 1) and switch_count > 0:
            total_switches_checked += 1
            if cur_peak <= prev_peak:
                peak_shaving_holds += 1
            prev_peak = cur_peak

        # Compute sensed stress feedback according to variant
        if variant == "Dijkstra":
            q = {u: 0.0 for u in nodes}
            V_k = 0.0
            v_trace.append(V_k)
            continue
        elif variant == "Static_BC":
            if k == 0:
                max_val = max(initial_raw_bc.values()) or 1.0
                for u in nodes:
                    S[u] = initial_raw_bc[u] / max_val
                    C[u] = 1.0 + beta_I * S[u]
            v_trace.append(0.0)
            continue
        elif variant == "IGP_Weight_Tuning":
            # Fortz-Thorup style iterative convex congestion weight update
            sensed = compute_structural_stress(
                graph, all_paths, demand_matrix=demand_matrix, node_capacities=node_capacities,
                noise_std=noise_std, rng=rng
            )
            max_s = max(sensed.values()) or 1.0
            for u in nodes:
                util = sensed[u] / max_s
                C[u] = 0.7 * C[u] + 0.3 * fortz_thorup_penalty(util)
            v_trace.append(0.0)
            continue

        # SRA family variants
        use_W = demand_matrix if variant == "Weighted_SRA" else None
        use_mu = node_capacities if variant == "Weighted_SRA" else None
        sensed = compute_structural_stress(
            graph, all_paths, demand_matrix=use_W, node_capacities=use_mu,
            noise_std=noise_std, rng=rng
        )
        max_s = max(sensed.values()) or 1.0

        if variant == "Unnormalized_SRA":
            # Feed raw kappa^{(k)} / N^2 directly without dynamic max-normalization norm(.)
            n_sq = max(float(len(nodes) ** 2), 1.0)
            q = {u: sensed[u] / n_sq for u in nodes}
        else:
            q = {u: sensed[u] / max_s for u in nodes}

        V_k = sum((S[u] - q[u]) ** 2 for u in nodes)
        v_trace.append(V_k)

        eff_alpha = 1.0 if variant == "Reactive_BC_alpha1" else alpha
        for u in nodes:
            S[u] = (1.0 - eff_alpha) * S[u] + eff_alpha * q[u]
            C[u] = 1.0 + beta_I * S[u]

    # Final routing evaluation
    routing_tables, all_paths = compute_routing_tables(graph, C)
    final_raw_bc = compute_structural_stress(graph, all_paths, demand_matrix=demand_matrix, node_capacities=None)
    final_peak_bc = max(final_raw_bc.values()) if final_raw_bc else 0.0
    final_apl = float(np.mean([len(p) - 1 for p in all_paths.values()])) if all_paths else 0.0

    return {
        "routing_tables": routing_tables,
        "all_paths": all_paths,
        "node_costs": C,
        "initial_peak_bc": initial_peak_bc,
        "final_peak_bc": final_peak_bc,
        "peak_reduction_pct": (initial_peak_bc - final_peak_bc) / max(initial_peak_bc, 1e-9) * 100.0,
        "final_apl": final_apl,
        "switch_count": switch_count,
        "switch_rate": switch_count / max(max_iters, 1),
        "final_tracking_error": v_trace[-1] if v_trace else 0.0,
        "mean_tail_tracking_error": float(np.mean(v_trace[-15:])) if len(v_trace) >= 15 else 0.0,
        "v_trace": v_trace,
        "peak_trace": peak_trace,
        "apl_trace": apl_trace,
    }


def run_packet_simulation(
    graph: nx.Graph,
    routing_tables: Dict[int, Dict[int, int]],
    load_per_node: float = 0.85,
    total_steps: int = 800,
    warmup_steps: int = 200,
    base_proc_capacity: float = 10.0,
    queue_capacity: int = 50,
    node_capacities: Dict[int, float] | None = None,
    demand_weights: Dict[Tuple[int, int], float] | None = None,
    protocol_mode: str = "table",
    sra_online_params: Dict[str, Any] | None = None,
    load_schedule: Dict[int, float] | None = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Fast, exact discrete-timestep packet queuing simulator matching Table II parameters:
      - Processing capacity: 10 packets/timestep (or heterogeneous mu_i)
      - Queue capacity: 50 packets
      - Supports static/pre-converged routing tables, LIRP-D queue deflection, or online time-varying adaptation.
    """
    rng = np.random.default_rng(seed)
    nodes = list(graph.nodes())
    n_nodes = len(nodes)
    queues: Dict[int, List[Tuple[int, int, int, int]]] = {u: [] for u in nodes}
    proc_cap = {u: int(round(node_capacities[u])) if node_capacities else int(base_proc_capacity) for u in nodes}

    # Precompute hop distances for LIRP-D if needed
    hop_dist = dict(nx.all_pairs_shortest_path_length(graph)) if protocol_mode == "LIRP-D" else {}

    # Prepare OD sampling distribution
    od_pairs = [(s, t) for s in nodes for t in nodes if s != t]
    if demand_weights is not None:
        probs = np.array([demand_weights.get(pair, 1.0) for pair in od_pairs], dtype=float)
        probs /= probs.sum()
    else:
        probs = None

    # Online state for time-varying adaptation
    S_online = {u: 0.0 for u in nodes}
    C_online = {u: 1.0 for u in nodes}
    node_pass_counts = {u: 0.0 for u in nodes}
    current_rt = {u: dict(routing_tables.get(u, {})) for u in nodes}

    generated = 0
    delivered = 0
    dropped = 0
    latencies: List[int] = []
    hops_list: List[int] = []
    timeseries_pdr: List[Tuple[int, float, float]] = []

    win_gen = 0
    win_del = 0
    win_lat = 0

    for t in range(total_steps):
        cur_load = load_per_node
        if load_schedule is not None:
            for step_t, val in sorted(load_schedule.items()):
                if t >= step_t:
                    cur_load = val

        # 1. Packet arrivals (Poisson with mean N * cur_load)
        n_arrivals = rng.poisson(n_nodes * cur_load)
        if probs is not None:
            chosen_indices = rng.choice(len(od_pairs), size=n_arrivals, p=probs)
            arrivals = [od_pairs[idx] for idx in chosen_indices]
        else:
            src_arr = rng.integers(0, n_nodes, size=n_arrivals)
            dst_offsets = rng.integers(1, n_nodes, size=n_arrivals)
            arrivals = [(nodes[s_i], nodes[(s_i + off) % n_nodes]) for s_i, off in zip(src_arr, dst_offsets)]

        for s, d in arrivals:
            if t >= warmup_steps:
                generated += 1
            win_gen += 1
            if len(queues[s]) < queue_capacity:
                queues[s].append((s, d, t, 0))
            else:
                if t >= warmup_steps:
                    dropped += 1

        # 2. Node processing & forwarding
        next_arrivals: List[Tuple[int, Tuple[int, int, int, int]]] = []
        for u in nodes:
            q = queues[u]
            if not q:
                continue
            k_proc = min(len(q), proc_cap[u])
            to_process = q[:k_proc]
            del q[:k_proc]

            for pkt_s, pkt_d, pkt_t0, pkt_hops in to_process:
                node_pass_counts[u] += 1.0
                if pkt_d == u:
                    if t >= warmup_steps:
                        delivered += 1
                        latencies.append(t - pkt_t0 + 1)
                        hops_list.append(pkt_hops)
                    win_del += 1
                    win_lat += (t - pkt_t0 + 1)
                else:
                    if protocol_mode == "LIRP-D":
                        nbrs = list(graph.neighbors(u))
                        cur_h = hop_dist[u].get(pkt_d, 999999)
                        closer = [v for v in nbrs if hop_dist[v].get(pkt_d, 999999) < cur_h]
                        if not closer:
                            closer = nbrs
                        nh = min(closer, key=lambda v: len(queues[v])) if closer else None
                    else:
                        nh = current_rt.get(u, {}).get(pkt_d)

                    if nh is not None and pkt_hops < n_nodes:
                        next_arrivals.append((nh, (pkt_s, pkt_d, pkt_t0, pkt_hops + 1)))
                    else:
                        if t >= warmup_steps:
                            dropped += 1

        for nh, pkt in next_arrivals:
            if len(queues[nh]) < queue_capacity:
                queues[nh].append(pkt)
            else:
                if t >= warmup_steps:
                    dropped += 1

        # 3. Optional online control-plane update every 25 steps
        if sra_online_params is not None and (t + 1) % 25 == 0:
            mode = sra_online_params.get("mode", "SRA")
            alpha_on = sra_online_params.get("alpha", 0.15)
            beta_on = sra_online_params.get("beta_I", 10.0)
            if mode in ("SRA", "Reactive_BC"):
                max_p = max(node_pass_counts.values()) or 1.0
                eff_a = 1.0 if mode == "Reactive_BC" else alpha_on
                for u in nodes:
                    norm_load = (node_pass_counts[u] / max(proc_cap[u], 1)) / (max_p / base_proc_capacity)
                    norm_load = min(1.0, max(0.0, norm_load))
                    S_online[u] = (1.0 - eff_a) * S_online[u] + eff_a * norm_load
                    C_online[u] = 1.0 + beta_on * S_online[u]
                current_rt, _ = compute_routing_tables(graph, C_online)
            node_pass_counts = {u: 0.0 for u in nodes}

        if (t + 1) % 25 == 0:
            pdr_win = win_del / max(win_gen, 1)
            lat_win = win_lat / max(win_del, 1)
            timeseries_pdr.append((t + 1, pdr_win, lat_win))
            win_gen, win_del, win_lat = 0, 0, 0

    measure_steps = max(1, total_steps - warmup_steps)
    throughput = delivered / measure_steps
    pdr = delivered / max(generated, 1)
    drop_rate = 1.0 - pdr
    avg_lat = float(np.mean(latencies)) if latencies else 0.0
    p95_lat = float(np.percentile(latencies, 95)) if latencies else 0.0
    avg_hops = float(np.mean(hops_list)) if hops_list else 0.0

    return {
        "throughput": throughput,
        "pdr": pdr,
        "drop_rate": drop_rate,
        "avg_latency": avg_lat,
        "p95_latency": p95_lat,
        "avg_hops": avg_hops,
        "timeseries": timeseries_pdr,
    }


# ------------------------------------------------------------------------------
# Worker Task for Exp-1 (Ablation & Baselines across seeds)
# ------------------------------------------------------------------------------
def worker_exp1_trial(args: Tuple[str, int, float]) -> List[Dict[str, Any]]:
    topo_name, seed, load = args
    n_nodes = 100
    if topo_name == "BA":
        g = nx.barabasi_albert_graph(n_nodes, m=4, seed=seed)
    elif topo_name == "WS":
        g = nx.watts_strogatz_graph(n_nodes, k=8, p=0.1, seed=seed)
    else:
        g = nx.erdos_renyi_graph(n_nodes, p=0.1, seed=seed)
        if not nx.is_connected(g):
            largest_cc = max(nx.connected_components(g), key=len)
            g = nx.convert_node_labels_to_integers(g.subgraph(largest_cc).copy())

    variants = [
        ("Dijkstra", {"variant": "Dijkstra", "alpha": 0.0, "beta_I": 0.0, "dwell_time": 1}),
        ("LIRP-D", {"variant": "Dijkstra", "alpha": 0.0, "beta_I": 0.0, "dwell_time": 1, "pkt_mode": "LIRP-D"}),
        ("Static_BC", {"variant": "Static_BC", "alpha": 1.0, "beta_I": 10.0, "dwell_time": 1}),
        ("IGP_Weight_Tuning", {"variant": "IGP_Weight_Tuning", "alpha": 0.3, "beta_I": 10.0, "dwell_time": 1}),
        ("Reactive_BC_alpha1", {"variant": "Reactive_BC_alpha1", "alpha": 1.0, "beta_I": 10.0, "dwell_time": 1}),
        ("Unnormalized_SRA", {"variant": "Unnormalized_SRA", "alpha": 0.1, "beta_I": 10.0, "dwell_time": 5}),
        ("SRA_NoDwell_Td1", {"variant": "Full_SRA", "alpha": 0.1, "beta_I": 10.0, "dwell_time": 1}),
        ("Full_SRA_Td5", {"variant": "Full_SRA", "alpha": 0.1, "beta_I": 10.0, "dwell_time": 5}),
    ]

    rows = []
    for name, cfg in variants:
        cp_res = run_control_plane_relaxation(
            g.copy(),
            variant=cfg["variant"],
            alpha=cfg["alpha"],
            beta_I=cfg["beta_I"],
            dwell_time=cfg["dwell_time"],
            max_iters=60,
            seed=seed,
        )
        pkt_mode = cfg.get("pkt_mode", "table")
        pkt_res = run_packet_simulation(
            g.copy(),
            routing_tables=cp_res["routing_tables"],
            load_per_node=load,
            total_steps=700,
            warmup_steps=200,
            protocol_mode=pkt_mode,
            seed=seed + 1000,
        )
        rows.append({
            "topology": topo_name,
            "seed": seed,
            "load": load,
            "method": name,
            "peak_bc_initial": cp_res["initial_peak_bc"],
            "peak_bc_final": cp_res["final_peak_bc"],
            "peak_reduction_pct": cp_res["peak_reduction_pct"],
            "apl": cp_res["final_apl"],
            "switch_count": cp_res["switch_count"],
            "switch_rate": cp_res["switch_rate"],
            "tracking_error": cp_res["mean_tail_tracking_error"],
            "throughput": pkt_res["throughput"],
            "pdr": pkt_res["pdr"],
            "drop_rate": pkt_res["drop_rate"],
            "avg_latency": pkt_res["avg_latency"],
            "p95_latency": pkt_res["p95_latency"],
            "avg_hops": pkt_res["avg_hops"],
        })
    return rows


# ------------------------------------------------------------------------------
# Worker Task for Exp-2 (Heterogeneous Demand/Capacity & Sensing Noise)
# ------------------------------------------------------------------------------
def worker_exp2_hetero_noise(args: Tuple[int, float]) -> List[Dict[str, Any]]:
    seed, noise_std = args
    rng = np.random.default_rng(seed)
    n_nodes = 100
    g = nx.barabasi_albert_graph(n_nodes, m=4, seed=seed)
    nodes = list(g.nodes())

    # Generate Pareto/Hotspot gravity traffic weights and heterogeneous node capacities
    node_mass = rng.pareto(a=1.5, size=n_nodes) + 1.0
    demand_matrix: Dict[Tuple[int, int], float] = {}
    for s in nodes:
        for t in nodes:
            if s != t:
                demand_matrix[(s, t)] = float(node_mass[s] * node_mass[t])

    # Heterogeneous capacities: some peripheral/medium nodes have lower capacity (6..16)
    degrees = dict(g.degree())
    max_deg = max(degrees.values()) or 1
    node_capacities: Dict[int, float] = {}
    for u in nodes:
        # Deliberately create non-aligned capacity heterogeneity where some medium-degree nodes have tight capacity
        base_c = 6.0 + 10.0 * rng.random()
        node_capacities[u] = base_c

    methods = [
        ("Dijkstra", "Dijkstra"),
        ("Reactive_BC_alpha1", "Reactive_BC_alpha1"),
        ("Topology_Only_SRA", "Full_SRA"),
        ("Generalized_Weighted_SRA", "Weighted_SRA"),
    ]
    rows = []
    for label, var in methods:
        cp_res = run_control_plane_relaxation(
            g.copy(),
            variant=var,
            alpha=0.1,
            beta_I=10.0,
            dwell_time=5,
            max_iters=60,
            demand_matrix=demand_matrix,
            node_capacities=node_capacities,
            noise_std=noise_std,
            seed=seed,
        )
        pkt_res = run_packet_simulation(
            g.copy(),
            routing_tables=cp_res["routing_tables"],
            load_per_node=0.85,
            total_steps=700,
            warmup_steps=200,
            node_capacities=node_capacities,
            demand_weights=demand_matrix,
            seed=seed + 2000,
        )
        # Compute generalized utilization peak \max_i (\kappa_i(W) / \mu_i)
        gen_stress = compute_structural_stress(g, cp_res["all_paths"], demand_matrix=demand_matrix, node_capacities=node_capacities)
        max_gen_stress = max(gen_stress.values()) if gen_stress else 1.0
        rows.append({
            "seed": seed,
            "noise_std": noise_std,
            "method": label,
            "max_generalized_stress": max_gen_stress,
            "feasibility_bound_gain": 1.0 / max(max_gen_stress, 1e-9),
            "throughput": pkt_res["throughput"],
            "pdr": pkt_res["pdr"],
            "drop_rate": pkt_res["drop_rate"],
            "avg_latency": pkt_res["avg_latency"],
            "p95_latency": pkt_res["p95_latency"],
            "switch_rate": cp_res["switch_rate"],
        })
    return rows


# ------------------------------------------------------------------------------
# Worker Task for Exp-3 (Dwell-Time & Hyperparameter Sensitivity)
# ------------------------------------------------------------------------------
def worker_exp3_dwell(args: Tuple[int, int, float, float]) -> Dict[str, Any]:
    seed, td, alpha, beta_I = args
    g = nx.barabasi_albert_graph(100, m=4, seed=seed)
    cp_res = run_control_plane_relaxation(
        g.copy(),
        variant="Full_SRA",
        alpha=alpha,
        beta_I=beta_I,
        dwell_time=td,
        max_iters=60,
        seed=seed,
    )
    pkt_res = run_packet_simulation(
        g.copy(),
        routing_tables=cp_res["routing_tables"],
        load_per_node=0.90,
        total_steps=600,
        warmup_steps=150,
        seed=seed + 3000,
    )
    return {
        "seed": seed,
        "T_d": td,
        "alpha": alpha,
        "beta_I": beta_I,
        "peak_reduction_pct": cp_res["peak_reduction_pct"],
        "switch_count": cp_res["switch_count"],
        "switch_rate": cp_res["switch_rate"],
        "tracking_error": cp_res["mean_tail_tracking_error"],
        "throughput": pkt_res["throughput"],
        "pdr": pkt_res["pdr"],
        "drop_rate": pkt_res["drop_rate"],
        "avg_latency": pkt_res["avg_latency"],
        "apl": cp_res["final_apl"],
    }


# ------------------------------------------------------------------------------
# Worker Task for Exp-4 (Scalability, Runtime Overhead & Real-World Backbones)
# ------------------------------------------------------------------------------
def worker_exp4_scalability(args: Tuple[str, int, int]) -> Dict[str, Any]:
    topo_type, n_nodes, seed = args
    if topo_type == "NSFNET":
        g = build_nsfnet_graph()
        n_nodes = g.number_of_nodes()
    elif topo_type == "GEANT":
        g = build_geant_graph()
        n_nodes = g.number_of_nodes()
    elif topo_type == "BA":
        g = nx.barabasi_albert_graph(n_nodes, m=4, seed=seed)
    else:
        g = nx.watts_strogatz_graph(n_nodes, k=8, p=0.1, seed=seed)

    # Measure per-step exact Brandes centrality + Dijkstra update wall-clock time
    t0 = time.perf_counter()
    cp_res = run_control_plane_relaxation(
        g.copy(),
        variant="Full_SRA",
        alpha=0.1,
        beta_I=10.0,
        dwell_time=5,
        max_iters=30,
        seed=seed,
    )
    t_total_ms = (time.perf_counter() - t0) * 1000.0
    t_per_iter_ms = t_total_ms / 30.0

    # Also measure packet-level performance on real-world topologies
    pkt_sra = run_packet_simulation(
        g.copy(), routing_tables=cp_res["routing_tables"], load_per_node=0.85,
        total_steps=600, warmup_steps=150, seed=seed + 4000
    )
    cp_dijk = run_control_plane_relaxation(g.copy(), variant="Dijkstra", max_iters=1, seed=seed)
    pkt_dijk = run_packet_simulation(
        g.copy(), routing_tables=cp_dijk["routing_tables"], load_per_node=0.85,
        total_steps=600, warmup_steps=150, seed=seed + 4000
    )

    return {
        "topology": topo_type,
        "N": n_nodes,
        "E": g.number_of_edges(),
        "seed": seed,
        "per_iter_ms": t_per_iter_ms,
        "total_30iter_ms": t_total_ms,
        "peak_reduction_pct": cp_res["peak_reduction_pct"],
        "dijkstra_throughput": pkt_dijk["throughput"],
        "sra_throughput": pkt_sra["throughput"],
        "throughput_gain_pct": (pkt_sra["throughput"] - pkt_dijk["throughput"]) / max(pkt_dijk["throughput"], 1e-9) * 100.0,
        "dijkstra_drop_rate": pkt_dijk["drop_rate"],
        "sra_drop_rate": pkt_sra["drop_rate"],
    }


# ------------------------------------------------------------------------------
# Plotting & Summary Generation
# ------------------------------------------------------------------------------
def generate_figures_and_tables(out_dir: Path, df_exp1: pd.DataFrame, df_exp2: pd.DataFrame, df_exp3: pd.DataFrame, df_exp4: pd.DataFrame, tv_traces: Dict[str, Any]) -> None:
    plt.rcParams.update({
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8.5,
        "figure.titlesize": 12,
    })

    # 1. Figure: Ablation Study & Stronger Baselines (2-panel figure)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    ba_high = df_exp1[(df_exp1["topology"] == "BA") & (np.isclose(df_exp1["load"], 0.90))]
    order = [
        "Dijkstra", "Static_BC", "LIRP-D", "IGP_Weight_Tuning",
        "Reactive_BC_alpha1", "Unnormalized_SRA", "SRA_NoDwell_Td1", "Full_SRA_Td5"
    ]
    labels = [
        "Dijkstra\n($\\alpha=0$)", "Static BC\n(Open-Loop)", "LIRP-D\n(Queue)", "IGP Weight\nTuning",
        "Reactive BC\n($\\alpha=1, T_d=1$)", "Unnorm.\nSRA", "SRA w/o $T_d$\n($T_d=1$)", "Full SRA\n($\\alpha=0.1, T_d=5$)"
    ]
    means_tp = [ba_high[ba_high["method"] == m]["throughput"].mean() for m in order]
    ci_tp = [1.96 * ba_high[ba_high["method"] == m]["throughput"].std() / math.sqrt(max(1, len(ba_high[ba_high["method"] == m]))) for m in order]
    colors = ["#7f8c8d", "#95a5a6", "#e67e22", "#d35400", "#c0392b", "#8e44ad", "#2980b9", "#27ae60"]

    x = np.arange(len(order))
    axes[0].bar(x, means_tp, yerr=ci_tp, capsize=3, color=colors, edgecolor="black", linewidth=0.6, alpha=0.9)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=28, ha="right")
    axes[0].set_ylabel("Throughput (packets/timestep)")
    axes[0].set_title("(a) High-Load Throughput Across Ablation & Baselines (BA)")
    axes[0].grid(axis="y", linestyle="--", alpha=0.5)

    means_drop = [ba_high[ba_high["method"] == m]["drop_rate"].mean() * 100.0 for m in order]
    means_sw = [ba_high[ba_high["method"] == m]["switch_rate"].mean() * 100.0 for m in order]
    w = 0.38
    axes[1].bar(x - w/2, means_drop, width=w, label="Packet Loss Rate (%)", color="#e74c3c", edgecolor="black", linewidth=0.6)
    axes[1].bar(x + w/2, means_sw, width=w, label="Route Switch Rate (% steps)", color="#3498db", edgecolor="black", linewidth=0.6)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=28, ha="right")
    axes[1].set_ylabel("Percentage (%)")
    axes[1].set_title("(b) Packet Loss vs. Control-Plane Route Churn")
    axes[1].legend(loc="upper right")
    axes[1].grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    fig.savefig(out_dir / "fig_revision_ablation_baselines.pdf", bbox_inches="tight")
    plt.close(fig)

    # 2. Figure: Non-Uniform Traffic / Heterogeneous Capacities, Time-Varying Shock, and Noise Robustness (3-panel)
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.2))

    # Panel (a): Heterogeneous W_st & \mu_i (Noise = 0)
    df_h0 = df_exp2[np.isclose(df_exp2["noise_std"], 0.0)]
    m_order = ["Dijkstra", "Reactive_BC_alpha1", "Topology_Only_SRA", "Generalized_Weighted_SRA"]
    m_labels = ["Dijkstra", "Reactive BC\n($\\alpha=1$)", "Topology-Only\nSRA ($\\kappa_i$)", "Weighted SRA\n($\\tilde{\\kappa}_i(W,\\mu)$)"]
    tp_h = [df_h0[df_h0["method"] == m]["throughput"].mean() for m in m_order]
    tp_ci = [1.96 * df_h0[df_h0["method"] == m]["throughput"].std() / math.sqrt(max(1, len(df_h0[df_h0["method"] == m]))) for m in m_order]
    pdr_h = [df_h0[df_h0["method"] == m]["pdr"].mean() * 100.0 for m in m_order]
    ax0_twin = axes[0].twinx()
    b1 = axes[0].bar(np.arange(4) - 0.18, tp_h, width=0.35, yerr=tp_ci, capsize=3, color="#2980b9", edgecolor="black", label="Throughput")
    b2 = ax0_twin.bar(np.arange(4) + 0.18, pdr_h, width=0.35, color="#27ae60", edgecolor="black", label="PDR (%)")
    axes[0].set_xticks(np.arange(4))
    axes[0].set_xticklabels(m_labels, rotation=15, ha="right")
    axes[0].set_ylabel("Throughput (packets/timestep)", color="#2980b9")
    ax0_twin.set_ylabel("Packet Delivery Ratio (%)", color="#27ae60")
    ax0_twin.set_ylim(40, 102)
    axes[0].set_title("(a) Skewed Demand $W_{st}$ & Hetero. Capacity $\\mu_i$")
    axes[0].grid(axis="y", linestyle="--", alpha=0.5)

    # Panel (b): Time-Varying Traffic Step Shock
    for mode_name, color_c, ls in [
        ("Full_SRA", "#27ae60", "-"),
        ("Reactive_BC", "#c0392b", "--"),
        ("Dijkstra", "#7f8c8d", ":"),
    ]:
        ts_list = tv_traces[mode_name]
        steps = [pt[0] for pt in ts_list]
        pdrs = [pt[1] * 100.0 for pt in ts_list]
        axes[1].plot(steps, pdrs, label=mode_name.replace("_", " "), color=color_c, linestyle=ls, linewidth=2.0)
    axes[1].axvline(300, color="black", linestyle="-.", alpha=0.6, label="Load Surge ($0.6 \\to 1.1$)")
    axes[1].axvline(600, color="purple", linestyle=":", alpha=0.6, label="Load Recovery ($1.1 \\to 0.7$)")
    axes[1].set_xlabel("Simulation Timestep")
    axes[1].set_ylabel("Windowed PDR (%)")
    axes[1].set_ylim(40, 103)
    axes[1].set_title("(b) Adaptation Under Time-Varying Traffic Burst")
    axes[1].legend(loc="lower left", fontsize=8)
    axes[1].grid(True, linestyle="--", alpha=0.5)

    # Panel (c): Sensing Noise Injection
    for m, lbl, col, mk in [
        ("Generalized_Weighted_SRA", "Weighted SRA ($\\alpha=0.1$)", "#27ae60", "o"),
        ("Topology_Only_SRA", "Topology SRA ($\\alpha=0.1$)", "#2980b9", "s"),
        ("Reactive_BC_alpha1", "Memoryless BC ($\\alpha=1.0$)", "#c0392b", "^"),
        ("Dijkstra", "Static Dijkstra", "#7f8c8d", "d"),
    ]:
        sub = df_exp2[df_exp2["method"] == m].groupby("noise_std")["pdr"].agg(["mean", "std"]).reset_index()
        axes[2].plot(sub["noise_std"] * 100.0, sub["mean"] * 100.0, marker=mk, color=col, linewidth=1.8, label=lbl)
        axes[2].fill_between(
            sub["noise_std"] * 100.0,
            (sub["mean"] - sub["std"]) * 100.0,
            (sub["mean"] + sub["std"]) * 100.0,
            color=col, alpha=0.15
        )
    axes[2].set_xlabel("Control-Plane Sensing Noise $\\sigma$ (%)")
    axes[2].set_ylabel("Packet Delivery Ratio (%)")
    axes[2].set_title("(c) Robustness to Sensing Noise Injection")
    axes[2].legend(loc="lower left", fontsize=8)
    axes[2].grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    fig.savefig(out_dir / "fig_revision_hetero_timevarying_noise.pdf", bbox_inches="tight")
    plt.close(fig)

    # 3. Figure: Scalability & Dwell-Time Sensitivity (2-panel)
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2))
    td_sub = df_exp3[np.isclose(df_exp3["alpha"], 0.1) & np.isclose(df_exp3["beta_I"], 10.0)].groupby("T_d").agg(
        pdr_mean=("pdr", "mean"),
        pdr_std=("pdr", "std"),
        sw_mean=("switch_rate", "mean"),
        sw_std=("switch_rate", "std"),
    ).reset_index()

    ax_td2 = axes[0].twinx()
    axes[0].plot(td_sub["T_d"], td_sub["pdr_mean"] * 100.0, "o-", color="#27ae60", linewidth=2.0, label="PDR (%)")
    ax_td2.plot(td_sub["T_d"], td_sub["sw_mean"] * 100.0, "s--", color="#c0392b", linewidth=2.0, label="Switch Frequency (%)")
    axes[0].set_xlabel("Minimum Dwell Time $T_d$ (iterations)")
    axes[0].set_ylabel("Packet Delivery Ratio (%)", color="#27ae60")
    ax_td2.set_ylabel("Route Switch Frequency (% steps)", color="#c0392b")
    axes[0].set_title("(a) Sensitivity to Minimum Dwell Time $T_d$")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    sc_ba = df_exp4[df_exp4["topology"] == "BA"].groupby("N")["per_iter_ms"].agg(["mean", "std"]).reset_index()
    sc_ws = df_exp4[df_exp4["topology"] == "WS"].groupby("N")["per_iter_ms"].agg(["mean", "std"]).reset_index()
    axes[1].plot(sc_ba["N"], sc_ba["mean"], "o-", color="#2980b9", linewidth=2.0, label="BA Scale-Free ($m=4$)")
    axes[1].plot(sc_ws["N"], sc_ws["mean"], "s--", color="#8e44ad", linewidth=2.0, label="WS Small-World ($k=8$)")
    axes[1].set_xlabel("Network Size $N$ (nodes)")
    axes[1].set_ylabel("Control-Plane Iteration Time (ms)")
    axes[1].set_title("(b) Computational Overhead vs. Network Scale $N$")
    axes[1].legend(loc="upper left")
    axes[1].grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    fig.savefig(out_dir / "fig_revision_dwell_scalability.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CNCOMM-2026-0222 revision simulations")
    parser.add_argument("--max-workers", type=int, default=20, help="Number of worker processes")
    parser.add_argument("--num-seeds", type=int, default=30, help="Number of independent trials per scenario")
    parser.add_argument("--out-dir", type=str, required=True, help="Output directory for results and PDF figures")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    print(f"[Campaign] Starting CNCOMM-2026-0222 revision campaign with max_workers={args.max_workers}, num_seeds={args.num_seeds}")

    # 1. Exp-1 Tasks
    exp1_tasks = [
        (topo, 100 + s, load)
        for topo in ["BA", "WS", "ER"]
        for s in range(args.num_seeds)
        for load in [0.50, 0.90, 1.20]
    ]
    exp1_rows: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.max_workers) as ex:
        futs = [ex.submit(worker_exp1_trial, task) for task in exp1_tasks]
        for f in as_completed(futs):
            exp1_rows.extend(f.result())
    df_exp1 = pd.DataFrame(exp1_rows)
    df_exp1.to_csv(out_dir / "exp1_ablation_baselines.csv", index=False)
    print(f"[Campaign] Exp-1 finished ({len(df_exp1)} rows).")

    # 2. Exp-2 Tasks (Heterogeneous demand/capacity + sensing noise)
    exp2_tasks = [
        (200 + s, noise)
        for s in range(args.num_seeds)
        for noise in [0.0, 0.05, 0.10, 0.20, 0.30]
    ]
    exp2_rows: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.max_workers) as ex:
        futs = [ex.submit(worker_exp2_hetero_noise, task) for task in exp2_tasks]
        for f in as_completed(futs):
            exp2_rows.extend(f.result())
    df_exp2 = pd.DataFrame(exp2_rows)
    df_exp2.to_csv(out_dir / "exp2_hetero_noise.csv", index=False)
    print(f"[Campaign] Exp-2 (hetero/noise) finished ({len(df_exp2)} rows).")

    # Time-varying step shock trace (averaged over args.num_seeds seeds)
    tv_accum: Dict[str, List[List[Tuple[int, float, float]]]] = {"Full_SRA": [], "Reactive_BC": [], "Dijkstra": []}
    for s in range(args.num_seeds):
        g_tv = nx.barabasi_albert_graph(100, m=4, seed=500 + s)
        cp_sra = run_control_plane_relaxation(g_tv.copy(), variant="Full_SRA", alpha=0.1, beta_I=10.0, dwell_time=5, max_iters=40, seed=500 + s)
        cp_dijk = run_control_plane_relaxation(g_tv.copy(), variant="Dijkstra", max_iters=1, seed=500 + s)
        sched = {0: 0.60, 300: 1.10, 600: 0.70}
        res_sra = run_packet_simulation(
            g_tv.copy(), cp_sra["routing_tables"], load_per_node=0.60, total_steps=850, warmup_steps=100,
            sra_online_params={"mode": "SRA", "alpha": 0.10, "beta_I": 10.0}, load_schedule=sched, seed=600 + s
        )
        res_reac = run_packet_simulation(
            g_tv.copy(), cp_dijk["routing_tables"], load_per_node=0.60, total_steps=850, warmup_steps=100,
            sra_online_params={"mode": "Reactive_BC", "alpha": 1.0, "beta_I": 10.0}, load_schedule=sched, seed=600 + s
        )
        res_dijk = run_packet_simulation(
            g_tv.copy(), cp_dijk["routing_tables"], load_per_node=0.60, total_steps=850, warmup_steps=100,
            sra_online_params=None, load_schedule=sched, seed=600 + s
        )
        tv_accum["Full_SRA"].append(res_sra["timeseries"])
        tv_accum["Reactive_BC"].append(res_reac["timeseries"])
        tv_accum["Dijkstra"].append(res_dijk["timeseries"])

    tv_traces: Dict[str, List[Tuple[int, float, float]]] = {}
    for k, runs in tv_accum.items():
        n_pts = len(runs[0])
        avg_pts = []
        for idx in range(n_pts):
            step_t = runs[0][idx][0]
            mean_pdr = float(np.mean([r[idx][1] for r in runs]))
            mean_lat = float(np.mean([r[idx][2] for r in runs]))
            avg_pts.append((step_t, mean_pdr, mean_lat))
        tv_traces[k] = avg_pts

    # 3. Exp-3 Tasks (Dwell time T_d and (alpha, beta_I) sensitivity)
    exp3_tasks = [
        (300 + s, td, 0.1, 10.0)
        for s in range(args.num_seeds)
        for td in [1, 2, 3, 5, 8, 10]
    ] + [
        (350 + s, 5, a, b)
        for s in range(15)
        for a in [0.05, 0.1, 0.25, 0.5]
        for b in [2.0, 5.0, 10.0, 20.0, 40.0]
    ]
    exp3_rows: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.max_workers) as ex:
        futs = [ex.submit(worker_exp3_dwell, task) for task in exp3_tasks]
        for f in as_completed(futs):
            exp3_rows.append(f.result())
    df_exp3 = pd.DataFrame(exp3_rows)
    df_exp3.to_csv(out_dir / "exp3_dwell_sensitivity.csv", index=False)
    print(f"[Campaign] Exp-3 finished ({len(df_exp3)} rows).")

    # 4. Exp-4 Tasks (Scalability & Real-World Topologies, 30 seeds)
    exp4_tasks = [
        (topo, n_sz, 400 + s)
        for topo in ["BA", "WS"]
        for n_sz in [50, 100, 200, 300, 500]
        for s in range(args.num_seeds)
    ] + [
        (rw_topo, 0, 450 + s)
        for rw_topo in ["NSFNET", "GEANT"]
        for s in range(args.num_seeds)
    ]
    exp4_rows: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.max_workers) as ex:
        futs = [ex.submit(worker_exp4_scalability, task) for task in exp4_tasks]
        for f in as_completed(futs):
            exp4_rows.append(f.result())
    df_exp4 = pd.DataFrame(exp4_rows)
    df_exp4.to_csv(out_dir / "exp4_scalability_realworld.csv", index=False)
    print(f"[Campaign] Exp-4 finished ({len(df_exp4)} rows).")

    # Generate PDF figures
    generate_figures_and_tables(out_dir, df_exp1, df_exp2, df_exp3, df_exp4, tv_traces)

    # Save structured summary JSON for manuscript tables
    summary = {
        "elapsed_seconds": time.time() - t_start,
        "num_seeds": args.num_seeds,
        "exp1_ba_load09": df_exp1[(df_exp1["topology"] == "BA") & (np.isclose(df_exp1["load"], 0.90))].groupby("method").agg(
            throughput_mean=("throughput", "mean"),
            throughput_std=("throughput", "std"),
            pdr_mean=("pdr", "mean"),
            pdr_std=("pdr", "std"),
            drop_mean=("drop_rate", "mean"),
            lat_mean=("avg_latency", "mean"),
            lat_p95=("p95_latency", "mean"),
            peak_red_mean=("peak_reduction_pct", "mean"),
            switch_rate_mean=("switch_rate", "mean"),
            tracking_err_mean=("tracking_error", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp1_ws_load09": df_exp1[(df_exp1["topology"] == "WS") & (np.isclose(df_exp1["load"], 0.90))].groupby("method").agg(
            throughput_mean=("throughput", "mean"),
            pdr_mean=("pdr", "mean"),
            drop_mean=("drop_rate", "mean"),
            lat_mean=("avg_latency", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp1_er_load09": df_exp1[(df_exp1["topology"] == "ER") & (np.isclose(df_exp1["load"], 0.90))].groupby("method").agg(
            throughput_mean=("throughput", "mean"),
            pdr_mean=("pdr", "mean"),
            drop_mean=("drop_rate", "mean"),
            lat_mean=("avg_latency", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp2_hetero_noise0": df_exp2[np.isclose(df_exp2["noise_std"], 0.0)].groupby("method").agg(
            max_gen_stress=("max_generalized_stress", "mean"),
            throughput_mean=("throughput", "mean"),
            throughput_std=("throughput", "std"),
            pdr_mean=("pdr", "mean"),
            pdr_std=("pdr", "std"),
            lat_mean=("avg_latency", "mean"),
            p95_lat_mean=("p95_latency", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp2_noise20": df_exp2[np.isclose(df_exp2["noise_std"], 0.20)].groupby("method").agg(
            throughput_mean=("throughput", "mean"),
            pdr_mean=("pdr", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp3_dwell": df_exp3[np.isclose(df_exp3["alpha"], 0.1) & np.isclose(df_exp3["beta_I"], 10.0)].groupby("T_d").agg(
            throughput_mean=("throughput", "mean"),
            pdr_mean=("pdr", "mean"),
            switch_rate_mean=("switch_rate", "mean"),
            tracking_err_mean=("tracking_error", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp4_scalability": df_exp4.groupby(["topology", "N"]).agg(
            E_mean=("E", "mean"),
            per_iter_ms_mean=("per_iter_ms", "mean"),
            per_iter_ms_std=("per_iter_ms", "std"),
            peak_red_mean=("peak_reduction_pct", "mean"),
            dijk_tp=("dijkstra_throughput", "mean"),
            sra_tp=("sra_throughput", "mean"),
            tp_gain_pct=("throughput_gain_pct", "mean"),
            dijk_drop=("dijkstra_drop_rate", "mean"),
            sra_drop=("sra_drop_rate", "mean"),
        ).round(4).reset_index().to_dict(orient="records"),
    }
    with open(out_dir / "summary_metrics.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"[Campaign] All figures and summary_metrics.json saved to {out_dir} in {summary['elapsed_seconds']:.1f}s.")


if __name__ == "__main__":
    main()
