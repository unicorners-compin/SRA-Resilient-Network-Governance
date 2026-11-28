#!/usr/bin/env python3
"""
CNCOMM-2026-0222 Major Revision Simulation Campaign
===================================================
Executes the 4 supplementary experiment blocks required by the Editor, Reviewer 1, and Reviewer 2:
  1. Exp-1: Component Ablation Study & Stronger Baselines (30 independent trials on BA, WS, ER)
     - Static Dijkstra (alpha=0)
     - Memoryless Reactive BC (alpha=1.0, T_d=1)
     - Unnormalized Stress SRA (fixed 1/N^2 scale, T_d=5)
     - SRA without Dwell Time (alpha=0.1, T_d=1)
     - Full SRA (alpha=0.1, beta_I=10.0, T_d=5)
     - Stronger Baseline 1: Static BC-Weighted Routing (open-loop centrality weighting)
     - Stronger Baseline 2: Dynamic IGP/OSPF Weight Tuning (Fortz-Thorup convex piecewise congestion penalty)
     - LIRP-D (Local queue-aware deflection)
  2. Exp-2: Generalized Demand/Capacity-Weighted Stress, Time-Varying Traffic & Noise Injection
     - (a) Non-uniform Pareto/Gravity traffic matrix W_st + heterogeneous node capacities bimodal mu_i (35% legacy, 65% core):
           Comparing Dijkstra, Reactive BC, Topology-Only SRA, and Generalized Weighted SRA (\tilde{\kappa}_i)
     - (b) Time-varying traffic surge (load schedule 0.60 -> 1.10 at t=350 -> 0.70 at t=700 over 1000 steps)
     - (c) Control-plane sensing noise injection (\sigma \in {0%, 5%, 10%, 20%, 30%})
  3. Exp-3: Hyperparameter Sensitivity (alpha, beta_I, and Minimum Dwell Time T_d)
     - Joint evaluation across T_d \in {1, 2, 3, 5, 8, 10} and (alpha, beta_I)
  4. Exp-4: Computational Complexity, Scalability (N \in {50, 100, 200, 300, 500}),
     and Real-World Internet Topology Zoo Carrier Backbones (Geant2012, Deltacom, UsCarrier)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
TOPOLOGY_DIR = REPO_ROOT / "data" / "topologies"


# ------------------------------------------------------------------------------
# Official Internet Topology Zoo Loader (Geant2012, Deltacom, UsCarrier)
# ------------------------------------------------------------------------------
def _parse_gml_regex_fallback(text: str) -> nx.Graph:
    """Lightweight regex fallback parser for Topology Zoo GML files."""
    g = nx.Graph()
    for block in re.findall(r"node\s*\[(.*?)\]", text, flags=re.DOTALL):
        m = re.search(r"\bid\s+(\d+)", block)
        if m:
            g.add_node(int(m.group(1)))
    for block in re.findall(r"edge\s*\[(.*?)\]", text, flags=re.DOTALL):
        ms = re.search(r"\bsource\s+(\d+)", block)
        mt = re.search(r"\btarget\s+(\d+)", block)
        if ms and mt:
            g.add_edge(int(ms.group(1)), int(mt.group(1)))
    return g


def load_topology_zoo_gml(name: str) -> nx.Graph:
    """
    Load an official Internet Topology Zoo .gml file as a connected simple
    undirected graph with contiguous integer node labels 0..N-1.
    """
    gml_path = TOPOLOGY_DIR / f"{name}.gml"
    if not gml_path.exists():
        raise FileNotFoundError(f"Missing Topology Zoo GML file: {gml_path}")
    try:
        mg = nx.read_gml(gml_path, label="id")
        g = nx.Graph(mg)
    except Exception:
        g = _parse_gml_regex_fallback(gml_path.read_text(encoding="utf-8", errors="ignore"))
    g.remove_edges_from(nx.selfloop_edges(g))
    if not nx.is_connected(g):
        largest_cc = max(nx.connected_components(g), key=len)
        g = g.subgraph(largest_cc).copy()
    return nx.convert_node_labels_to_integers(g)


# ------------------------------------------------------------------------------
# Core Routing & Discrete-Time Packet Simulation Engine
# ------------------------------------------------------------------------------
def compute_routing_tables(
    graph: nx.Graph,
    node_costs: Dict[int, float],
) -> Tuple[Dict[int, Dict[int, int]], Dict[Tuple[int, int], List[int]]]:
    """Compute all-pairs shortest paths and next-hop tables under symmetric edge weight 0.5*(C_u + C_v)."""
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
        capacities = service_capacities(graph.nodes(), node_capacities)
        for u in stress:
            stress[u] = stress[u] / capacities[u]

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


def service_capacities(nodes, node_capacities=None, base_proc_capacity=10.0):
    """The same integer service rates are used by sensing and forwarding."""
    return {u: max(1, int(round(node_capacities[u] if node_capacities is not None
                                else base_proc_capacity))) for u in nodes}


def run_control_plane_relaxation(
    graph: nx.Graph, variant: str, alpha: float = 0.1, beta_I: float = 10.0,
    dwell_time: int = 5, max_iters: int = 200, demand_matrix=None,
    node_capacities=None, noise_std: float = 0.0, seed: int = 42,
    measure_runtime: bool = False, record_trace: bool = False,
) -> Dict[str, Any]:
    """Algorithm 1: sense only at block boundaries; cool with held feedback.

    Timing includes routing, sensing and the active update in each evaluation.
    The dedicated timing pass always samples 50 iterations, without early exit.
    Returned routes are the last installed routes, with no off-schedule final solve.
    """
    if max_iters < 1 or dwell_time < 1:
        raise ValueError("max_iters and dwell_time must be positive")
    if variant in ("IGP_Weight_Tuning", "IGP_Damped_FT", "Reactive_BC_alpha1"):
        dwell_time = 1
    if measure_runtime:
        max_iters = 50
    rng = np.random.default_rng(seed)
    nodes = list(graph.nodes())
    S, C = dict.fromkeys(nodes, 0.0), dict.fromkeys(nodes, 1.0)
    q = dict.fromkeys(nodes, 0.0)
    routing_tables, all_paths = compute_routing_tables(graph, C)
    initial_raw_bc = compute_structural_stress(graph, all_paths)
    initial_peak_bc = max(initial_raw_bc.values(), default=0.0)
    signature = lambda paths: tuple((pair, tuple(path)) for pair, path in sorted(paths.items()))
    prev_paths_sig = signature(all_paths)
    v_trace, peak_trace, apl_trace, switch_history, trace = [], [], [], [], []
    gen_peak_trace: List[float] = []
    block_routing_tables: List[Dict[int, Dict[int, int]]] = []
    recompute_times_ms = []
    weighted = variant in ("Weighted_SRA", "Generalized_Weighted_SRA")
    igp = variant in ("IGP_Weight_Tuning", "IGP_Damped_FT")
    iterative = variant not in ("Dijkstra", "Static_BC")
    converged_early = False
    raw_peak = initial_peak_bc
    gen_peak = raw_peak
    if not measure_runtime and (demand_matrix is not None or node_capacities is not None):
        gen_raw = compute_structural_stress(
            graph, all_paths, demand_matrix=demand_matrix, node_capacities=node_capacities)
        gen_peak = max(gen_raw.values(), default=0.0)
    apl = float(np.mean([len(p) - 1 for p in all_paths.values()])) if all_paths else 0.0
    t_loop_start = time.perf_counter()
    for k in range(max_iters):
        active = (k % dwell_time == 0) if iterative else (variant == "Static_BC" and k == 1)
        switched, paths_unchanged = False, True
        t_rec0 = time.perf_counter()
        if active:
            # Initial unit-cost routes have already been installed above.
            routing_tables, all_paths = compute_routing_tables(graph, C)
            block_routing_tables.append(routing_tables)
            new_sig = signature(all_paths)
            paths_unchanged = new_sig == prev_paths_sig
            switched = k > 0 and not paths_unchanged
            prev_paths_sig = new_sig
            if iterative:
                sensed = compute_structural_stress(
                    graph, all_paths,
                    demand_matrix=demand_matrix if weighted or igp else None,
                    node_capacities=node_capacities if weighted or igp else None,
                    noise_std=noise_std, rng=rng)
                denom = float(len(nodes)**2) if variant == "Unnormalized_SRA" else (max(sensed.values()) or 1.0)
                q = {u: sensed[u] / denom for u in nodes}
            if not measure_runtime:
                raw = compute_structural_stress(graph, all_paths, demand_matrix=demand_matrix)
                raw_peak = max(raw.values(), default=0.0)
                gen_peak = raw_peak
                if demand_matrix is not None or node_capacities is not None:
                    gen_raw = compute_structural_stress(
                        graph, all_paths, demand_matrix=demand_matrix, node_capacities=node_capacities)
                    gen_peak = max(gen_raw.values(), default=0.0)
                apl = float(np.mean([len(p)-1 for p in all_paths.values()])) if all_paths else 0.0
        old_S = S.copy()
        if variant == "Static_BC" and k == 0:
            # Open-loop unweighted BC, optionally corrupted by one-shot telemetry noise.
            sensed = initial_raw_bc.copy()
            if noise_std:
                sensed = {u: v * max(0.0, 1.0 + rng.normal(0, noise_std)) for u, v in sensed.items()}
            denom = max(sensed.values()) or 1.0
            S = {u: sensed[u] / denom for u in nodes}
            C = {u: 1.0 + beta_I * S[u] for u in nodes}
        elif igp:
            for u in nodes:
                penalty = fortz_thorup_penalty(q[u])
                C[u] = penalty if variant == "IGP_Weight_Tuning" else 0.7 * C[u] + 0.3 * penalty
                S[u] = q[u]
        elif iterative:
            eff_alpha = 1.0 if variant == "Reactive_BC_alpha1" else alpha
            for u in nodes:
                S[u] = (1.0 - eff_alpha) * S[u] + eff_alpha * q[u]
                C[u] = 1.0 + beta_I * S[u]
        if active:
            recompute_times_ms.append((time.perf_counter()-t_rec0)*1000.0)
        delta = max((abs(S[u]-old_S[u]) for u in nodes), default=0.0)
        v_trace.append(sum((S[u]-q[u])**2 for u in nodes) if iterative else 0.0)
        peak_trace.append(raw_peak)
        gen_peak_trace.append(gen_peak)
        apl_trace.append(apl)
        switch_history.append(int(switched))
        if record_trace:
            trace.append(dict(k=k, active=active, S=S.copy(), C=C.copy(), q=q.copy(),
                              paths_sig=prev_paths_sig, max_abs_delta_S=delta))
        if (iterative and not measure_runtime and k >= dwell_time and active
                and delta <= 1e-5 and paths_unchanged):
            converged_early = True
            break
    loop_total_ms = (time.perf_counter()-t_loop_start)*1000.0
    iters_ran = len(switch_history)
    final_raw = compute_structural_stress(graph, all_paths, demand_matrix=demand_matrix)
    final_peak = max(final_raw.values(), default=0.0)
    n_tail_blocks = max(8, 2 * math.ceil(20 / dwell_time))
    tail_len = min(iters_ran, n_tail_blocks * dwell_time)
    tail_peak = float(np.mean(peak_trace[-tail_len:]))
    if variant in ("Dijkstra", "Static_BC") or converged_early or len(block_routing_tables) <= 1:
        orbit_routing_tables = [routing_tables]
    else:
        orbit_routing_tables = block_routing_tables[-min(8, len(block_routing_tables)):]
    return dict(
        orbit_routing_tables=orbit_routing_tables, dwell_time_used=dwell_time,
        last_snapshot_peak_bc=final_peak,
        tail_max_generalized_stress=float(np.mean(gen_peak_trace[-tail_len:])),
        routing_tables=routing_tables, all_paths=all_paths, node_costs=C,
        initial_peak_bc=initial_peak_bc, final_peak_bc=tail_peak,
        peak_reduction_pct=(initial_peak_bc-tail_peak)/max(initial_peak_bc, 1e-9)*100,
        final_apl=float(np.mean([len(p)-1 for p in all_paths.values()])) if all_paths else 0.0,
        switch_count=sum(switch_history), switch_rate=sum(switch_history)/iters_ran,
        tail_switch_rate=float(np.mean(switch_history[-50:])),
        iters_executed=iters_ran, converged_early=converged_early,
        switch_history=switch_history, final_tracking_error=v_trace[-1],
        mean_tail_tracking_error=float(np.mean(v_trace[-15:])),
        v_trace=v_trace, peak_trace=peak_trace, gen_peak_trace=gen_peak_trace, apl_trace=apl_trace, trace=trace,
        recompute_times_ms=recompute_times_ms,
        eval_ms=float(np.mean(recompute_times_ms)) if recompute_times_ms else 0.0,
        loop_total_ms=loop_total_ms, amortized_iter_ms=loop_total_ms/iters_ran)


def run_control_plane_diagnostic(*args, **kwargs) -> Dict[str, Any]:
    """Use the same block schedule and convergence test as the timing engine."""
    return run_control_plane_relaxation(*args, **kwargs)


def run_packet_simulation(
    graph: nx.Graph,
    routing_tables: Dict[int, Dict[int, int]],
    load_per_node: float = 0.85,
    total_steps: int = 1000,
    warmup_steps: int = 200,
    base_proc_capacity: float = 10.0,
    queue_capacity: int = 50,
    node_capacities: Dict[int, float] | None = None,
    demand_weights: Dict[Tuple[int, int], float] | None = None,
    protocol_mode: str = "table",
    sra_online_params: Dict[str, Any] | None = None,
    load_schedule: Dict[int, float] | None = None,
    demand_schedule: Dict[int, Dict[Tuple[int, int], float]] | None = None,
    seed: int = 42,
    orbit_routing_tables: List[Dict[int, Dict[int, int]]] | None = None,
    orbit_step_interval: int = 25,
) -> Dict[str, Any]:
    """
    Discrete-timestep packet queuing simulator matching Table II parameters:
      - Processing capacity: 10 packets/timestep (or heterogeneous mu_i)
      - Queue buffer capacity: 50 packets
      - Supports static/pre-converged routing tables, LIRP-D queue deflection, or online time-varying adaptation.
    """
    rng = np.random.default_rng(seed)
    nodes = list(graph.nodes())
    n_nodes = len(nodes)
    queues: Dict[int, List[Tuple[int, int, int, int]]] = {u: [] for u in nodes}
    proc_cap = service_capacities(nodes, node_capacities, base_proc_capacity)

    hop_dist = dict(nx.all_pairs_shortest_path_length(graph)) if protocol_mode == "LIRP-D" else {}

    od_pairs = [(s, t) for s in nodes for t in nodes if s != t]
    if demand_weights is not None:
        probs = np.array([demand_weights.get(pair, 1.0) for pair in od_pairs], dtype=float)
        probs /= probs.sum()
    else:
        probs = None

    if sra_online_params is not None and sra_online_params.get("init_costs") is not None:
        init_costs = sra_online_params["init_costs"]
        beta_init = float(sra_online_params.get("beta_I", 10.0))
        C_online = {u: float(init_costs.get(u, 1.0)) for u in nodes}
        S_online = {u: min(1.0, max(0.0, (C_online[u] - 1.0) / max(beta_init, 1e-9))) for u in nodes}
    else:
        S_online = {u: 0.0 for u in nodes}
        C_online = {u: 1.0 for u in nodes}
    node_pass_counts = {u: 0.0 for u in nodes}
    current_rt = {u: dict(routing_tables.get(u, {})) for u in nodes}

    initial_online_costs = C_online.copy()
    online_switch_count = 0
    online_epochs = 0
    generated = 0
    delivered = 0
    dropped = 0
    latencies: List[int] = []
    hops_list: List[int] = []
    timeseries_pdr: List[Tuple[int, float, float, float]] = []

    win_gen = 0
    win_del = 0
    win_lat = 0

    demand_probs = {}
    for step, weights in (demand_schedule or {}).items():
        values = np.array([weights.get(pair, 1.0) for pair in od_pairs], dtype=float)
        demand_probs[step] = values / values.sum()
    for t in range(total_steps):
        if t in demand_probs:
            probs = demand_probs[t]
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

        if (sra_online_params is None and orbit_routing_tables is not None
                and len(orbit_routing_tables) > 1 and orbit_step_interval > 0):
            current_rt = orbit_routing_tables[(t // orbit_step_interval) % len(orbit_routing_tables)]

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
                if u != pkt_s and u != pkt_d:
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
            alpha_on = sra_online_params.get("alpha", 0.10)
            beta_on = sra_online_params.get("beta_I", 10.0)
            if mode in ("Weighted_SRA", "Topology_SRA", "SRA", "Reactive_BC"):
                if mode == "Weighted_SRA":
                    raw_scores = {u: node_pass_counts[u] / max(proc_cap[u], 1) for u in nodes}
                else:
                    raw_scores = {u: node_pass_counts[u] for u in nodes}
                max_s = max(raw_scores.values()) or 1.0
                eff_a = 1.0 if mode == "Reactive_BC" else alpha_on
                for u in nodes:
                    norm_load = min(1.0, max(0.0, raw_scores[u] / max_s))
                    S_online[u] = (1.0 - eff_a) * S_online[u] + eff_a * norm_load
                    C_online[u] = 1.0 + beta_on * S_online[u]
                new_rt, _ = compute_routing_tables(graph, C_online)
                online_switch_count += int(new_rt != current_rt)
                current_rt = new_rt
            online_epochs += 1
            node_pass_counts = {u: 0.0 for u in nodes}

        if (t + 1) % 25 == 0:
            pdr_win = win_del / max(win_gen, 1)
            lat_win = win_lat / max(win_del, 1)
            tp_win = win_del / 25.0
            timeseries_pdr.append((t + 1, pdr_win, lat_win, tp_win))
            win_gen, win_del, win_lat = 0, 0, 0

    measure_steps = max(1, total_steps - warmup_steps)
    throughput = delivered / measure_steps
    pdr = delivered / max(generated, 1)
    drop_rate = max(0.0, 1.0 - pdr)
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
        "online_switch_rate": online_switch_count / max(online_epochs, 1),
        "initial_online_costs": initial_online_costs,
        "proc_cap": proc_cap,
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
        ("IGP_Damped_FT", {"variant": "IGP_Damped_FT", "alpha": 0.3, "beta_I": 10.0, "dwell_time": 1}),
        ("Reactive_BC_alpha1", {"variant": "Reactive_BC_alpha1", "alpha": 1.0, "beta_I": 10.0, "dwell_time": 1}),
        ("Unnormalized_SRA", {"variant": "Unnormalized_SRA", "alpha": 0.1, "beta_I": 10.0, "dwell_time": 5}),
        ("SRA_NoDwell_Td1", {"variant": "Full_SRA", "alpha": 0.1, "beta_I": 10.0, "dwell_time": 1}),
        ("Full_SRA_Td5", {"variant": "Full_SRA", "alpha": 0.1, "beta_I": 10.0, "dwell_time": 5}),
    ]

    rows = []
    for name, cfg in variants:
        cp_res = run_control_plane_diagnostic(
            g.copy(),
            variant=cfg["variant"],
            alpha=cfg["alpha"],
            beta_I=cfg["beta_I"],
            dwell_time=cfg["dwell_time"],
            max_iters=200,
            seed=seed,
        )
        pkt_mode = cfg.get("pkt_mode", "table")
        pkt_res = run_packet_simulation(
            g.copy(),
            routing_tables=cp_res["routing_tables"],
            orbit_routing_tables=cp_res["orbit_routing_tables"],
            orbit_step_interval=5 * cp_res["dwell_time_used"],
            load_per_node=load,
            total_steps=1000,
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
            "tail_switch_rate": cp_res["tail_switch_rate"],
            "iters_executed": cp_res["iters_executed"],
            "converged_early": cp_res["converged_early"],
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

    node_mass = rng.pareto(a=1.5, size=n_nodes) + 1.0
    demand_matrix: Dict[Tuple[int, int], float] = {}
    for s in nodes:
        for t in nodes:
            if s != t:
                demand_matrix[(s, t)] = float(node_mass[s] * node_mass[t])

    # Degree-independent bimodal capacities, rounded to actual service rates.
    node_capacities = heterogeneous_capacities(nodes, rng)

    methods = [
        ("Dijkstra", "Dijkstra"),
        ("Static_BC", "Static_BC"),
        ("IGP_Weight_Tuning", "IGP_Weight_Tuning"),
        ("Reactive_BC_alpha1", "Reactive_BC_alpha1"),
        ("Topology_Only_SRA", "Full_SRA"),
        ("Generalized_Weighted_SRA", "Weighted_SRA"),
    ]
    rows = []
    for label, var in methods:
        if noise_std > 0 and var == "IGP_Weight_Tuning":
            continue
        cp_res = run_control_plane_diagnostic(
            g.copy(),
            variant=var,
            alpha=0.1,
            beta_I=10.0,
            dwell_time=5,
            max_iters=200,
            demand_matrix=demand_matrix,
            node_capacities=node_capacities,
            noise_std=noise_std,
            seed=seed,
        )
        pkt_res = run_packet_simulation(
            g.copy(),
            routing_tables=cp_res["routing_tables"],
            orbit_routing_tables=cp_res["orbit_routing_tables"],
            orbit_step_interval=5 * cp_res["dwell_time_used"],
            load_per_node=0.85,
            total_steps=1000,
            warmup_steps=200,
            node_capacities=node_capacities,
            demand_weights=demand_matrix,
            seed=seed + 2000,
        )
        max_gen_stress = cp_res["tail_max_generalized_stress"]
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
            "tail_switch_rate": cp_res["tail_switch_rate"],
            "iters_executed": cp_res["iters_executed"],
            "converged_early": cp_res["converged_early"],
        })
    return rows


# ------------------------------------------------------------------------------
# Worker Task for Time-Varying Traffic Surge (Fig. 11(b))
# ------------------------------------------------------------------------------
def heterogeneous_capacities(nodes, rng):
    """Degree-independent random partition: 35% legacy and 65% core routers."""
    shuffled = rng.permutation(list(nodes))
    cut = int(round(0.35 * len(shuffled)))
    return {int(u): int(round(rng.uniform(3.0, 5.0) if i < cut else rng.uniform(10.0, 16.0)))
            for i, u in enumerate(shuffled)}


def time_varying_inputs(nodes, rng):
    mass = rng.pareto(a=1.5, size=len(nodes)) + 1.0
    shifted = mass[rng.permutation(len(nodes))]
    matrices = [{(s, t): float(values[i]*values[j])
                 for i, s in enumerate(nodes) for j, t in enumerate(nodes) if s != t}
                for values in (mass, shifted)]
    return matrices


def worker_tv_trial(seed: int) -> Dict[str, Any]:
    rng = np.random.default_rng(700 + seed)
    g = nx.barabasi_albert_graph(100, m=4, seed=500 + seed)
    nodes = list(g.nodes())
    w1, w2 = time_varying_inputs(nodes, rng)
    capacities = heterogeneous_capacities(nodes, rng)
    unit_rt, paths = compute_routing_tables(g, dict.fromkeys(nodes, 1.0))
    bc = compute_structural_stress(g, paths)
    denom = max(bc.values()) or 1.0
    static_rt, _ = compute_routing_tables(g, {u: 1.0 + 10.0*bc[u]/denom for u in nodes})
    output = {}
    metrics = {}
    for method in ("Dijkstra", "Static_BC", "Reactive_BC", "Topology_SRA", "Weighted_SRA"):
        online = None if method in ("Dijkstra", "Static_BC") else dict(mode=method, alpha=0.1, beta_I=10.0)
        result = run_packet_simulation(
            g.copy(), static_rt if method == "Static_BC" else unit_rt,
            total_steps=1000, warmup_steps=200, load_per_node=0.60,
            node_capacities=capacities, demand_weights=w1, demand_schedule={350: w2},
            sra_online_params=online, load_schedule={0: 0.60, 350: 1.10, 700: 0.70}, seed=600+seed)
        output[method] = result["timeseries"]
        metrics[method] = {"online_switch_rate": result["online_switch_rate"]}
    output["online_metrics"] = metrics
    return output


# ------------------------------------------------------------------------------
# Worker Task for Exp-3 (Dwell-Time & Hyperparameter Sensitivity)
# ------------------------------------------------------------------------------
def worker_exp3_dwell(args: Tuple[int, int, float, float]) -> Dict[str, Any]:
    seed, td, alpha, beta_I = args
    g = nx.barabasi_albert_graph(100, m=4, seed=seed)
    cp_res = run_control_plane_diagnostic(
        g.copy(),
        variant="Full_SRA",
        alpha=alpha,
        beta_I=beta_I,
        dwell_time=td,
        max_iters=200,
        seed=seed,
    )
    pkt_res = run_packet_simulation(
        g.copy(),
        routing_tables=cp_res["routing_tables"],
        orbit_routing_tables=cp_res["orbit_routing_tables"],
        orbit_step_interval=5 * cp_res["dwell_time_used"],
        load_per_node=0.90,
        total_steps=1000,
        warmup_steps=200,
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
        "tail_switch_rate": cp_res["tail_switch_rate"],
        "iters_executed": cp_res["iters_executed"],
        "tracking_error": cp_res["mean_tail_tracking_error"],
        "throughput": pkt_res["throughput"],
        "pdr": pkt_res["pdr"],
        "drop_rate": pkt_res["drop_rate"],
        "avg_latency": pkt_res["avg_latency"],
        "apl": cp_res["final_apl"],
    }


# ------------------------------------------------------------------------------
# Worker Task for Exp-4 (Scalability, Runtime Overhead & Official Topology Zoo Backbones)
# ------------------------------------------------------------------------------
def worker_exp4_scalability(args: Tuple[str, int, int]) -> List[Dict[str, Any]]:
    topo_type, n_nodes, seed = args
    if topo_type in ("Geant2012", "Deltacom", "UsCarrier"):
        g = load_topology_zoo_gml(topo_type)
        n_nodes = g.number_of_nodes()
    elif topo_type == "BA":
        g = nx.barabasi_albert_graph(n_nodes, m=4, seed=seed)
    else:
        g = nx.watts_strogatz_graph(n_nodes, k=8, p=0.1, seed=seed)

    # Measure exact wall-clock runtime of active recomputations (eval_ms)
    # and T_d=5 amortized loop time per epoch (amortized_iter_ms)
    cp_rt = run_control_plane_relaxation(
        g.copy(),
        variant="Full_SRA",
        alpha=0.1,
        beta_I=10.0,
        dwell_time=5,
        max_iters=50,
        seed=seed,
        measure_runtime=True,
    )
    eval_ms = cp_rt["eval_ms"]
    amortized_iter_ms = cp_rt["amortized_iter_ms"]

    # Measure structural relaxation and packet-level performance under uniform fixed config
    cp_diag = run_control_plane_diagnostic(
        g.copy(),
        variant="Full_SRA",
        alpha=0.1,
        beta_I=10.0,
        dwell_time=5,
        max_iters=200,
        seed=seed,
    )
    pkt_sra = run_packet_simulation(
        g.copy(), routing_tables=cp_diag["routing_tables"], load_per_node=0.85,
        orbit_routing_tables=cp_diag["orbit_routing_tables"],
        orbit_step_interval=5 * cp_diag["dwell_time_used"],
        total_steps=1000, warmup_steps=200, seed=seed + 4000
    )
    cp_dijk = run_control_plane_diagnostic(g.copy(), variant="Dijkstra", max_iters=200, seed=seed)
    pkt_dijk = run_packet_simulation(
        g.copy(), routing_tables=cp_dijk["routing_tables"], load_per_node=0.85,
        orbit_routing_tables=cp_dijk["orbit_routing_tables"],
        orbit_step_interval=5 * cp_dijk["dwell_time_used"],
        total_steps=1000, warmup_steps=200, seed=seed + 4000
    )

    row = {
        "topology": topo_type,
        "N": n_nodes,
        "E": g.number_of_edges(),
        "seed": seed,
        "eval_ms": eval_ms,
        "amortized_iter_ms": amortized_iter_ms,
        "total_50iter_ms": cp_rt["loop_total_ms"],
        "peak_reduction_pct": cp_diag["peak_reduction_pct"],
        "dijkstra_throughput": pkt_dijk["throughput"],
        "sra_throughput": pkt_sra["throughput"],
        "throughput_gain_pct": (pkt_sra["throughput"] - pkt_dijk["throughput"]) / max(pkt_dijk["throughput"], 1e-9) * 100.0,
        "dijkstra_drop_rate": pkt_dijk["drop_rate"],
        "sra_drop_rate": pkt_sra["drop_rate"],
    }

    row.update(method="Full_SRA", throughput=pkt_sra["throughput"], pdr=pkt_sra["pdr"],
               switch_rate=cp_diag["switch_rate"], tail_switch_rate=cp_diag["tail_switch_rate"],
               iters_executed=cp_diag["iters_executed"], tracking_error=cp_diag["mean_tail_tracking_error"])
    rows = [row]
    if topo_type == "BA":
        cp = run_control_plane_diagnostic(g.copy(), variant="Unnormalized_SRA", max_iters=200, seed=seed)
        pkt = run_packet_simulation(g.copy(), cp["routing_tables"], load_per_node=0.85,
                                    orbit_routing_tables=cp["orbit_routing_tables"],
                                    orbit_step_interval=5 * cp["dwell_time_used"],
                                    total_steps=1000, warmup_steps=200, seed=seed+4000)
        rows.append(dict(topology=topo_type, N=n_nodes, E=g.number_of_edges(), seed=seed,
                         method="Unnormalized_SRA", **{k: pkt[k] for k in
                         ("throughput", "pdr", "drop_rate", "avg_latency", "p95_latency")},
                         switch_rate=cp["switch_rate"], tail_switch_rate=cp["tail_switch_rate"],
                         iters_executed=cp["iters_executed"], tracking_error=cp["mean_tail_tracking_error"],
                         peak_reduction_pct=cp["peak_reduction_pct"]))
    return rows


# ------------------------------------------------------------------------------
# Plotting & Summary Generation
# ------------------------------------------------------------------------------
def paired_statistics(frame, reference, metrics):
    """Seed-paired differences; Holm correction over comparators per outcome."""
    from scipy.stats import wilcoxon
    baseline = frame[frame.method == reference].set_index("seed")
    result = {}
    for method in sorted(set(frame.method) - {reference}):
        other = frame[frame.method == method].set_index("seed")
        paired = baseline[list(metrics)].join(other[list(metrics)], how="inner", lsuffix="_ref", rsuffix="_method")
        result[method] = {}
        for metric in metrics:
            diffs = (paired[metric+"_ref"] - paired[metric+"_method"]).dropna().to_numpy()
            n = len(diffs)
            result[method][metric] = dict(
                n=n, mean_diff=float(np.mean(diffs)) if n else 0.0,
                ci95_diff=float(1.96*np.std(diffs, ddof=1)/math.sqrt(n)) if n > 1 else 0.0,
                wilcoxon_p_raw=float(wilcoxon(diffs, alternative="two-sided").pvalue) if np.any(diffs != 0) else 1.0)
    for metric in metrics:
        ordered = sorted(result, key=lambda method: result[method][metric]["wilcoxon_p_raw"])
        adjusted = 0.0
        for rank, method in enumerate(ordered):
            adjusted = max(adjusted, min(1.0, (len(ordered)-rank)*result[method][metric]["wilcoxon_p_raw"]))
            result[method][metric]["holm_p"] = adjusted
    return result


def ci95_series(std_s: pd.Series, cnt_s: pd.Series) -> pd.Series:
    return 1.96 * std_s / np.sqrt(np.maximum(cnt_s, 1))


def generate_figures_and_tables(
    out_dir: Path,
    df_exp1: pd.DataFrame,
    df_exp2: pd.DataFrame,
    df_exp3: pd.DataFrame,
    df_exp4: pd.DataFrame,
    tv_stats: Dict[str, Any],
) -> None:
    plt.rcParams.update({
        "font.size": 9.5,
        "axes.titlesize": 10.5,
        "axes.labelsize": 9.5,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 7.8,
        "figure.titlesize": 11.5,
    })

    # 1. Figure 10: Ablation Study & Stronger Baselines (3-panel figure (a)(b)(c))
    fig, axes = plt.subplots(1, 3, figsize=(18, 4.8))
    order = [
        "Dijkstra", "Reactive_BC_alpha1", "LIRP-D", "Static_BC",
        "IGP_Weight_Tuning", "IGP_Damped_FT", "Unnormalized_SRA", "SRA_NoDwell_Td1", "Full_SRA_Td5",
    ]
    short_lbl = {
        "Dijkstra": "Dijkstra ($\\alpha=0$)",
        "Reactive_BC_alpha1": "Reactive BC ($\\alpha=1$)",
        "LIRP-D": "LIRP-D (Queue)",
        "Static_BC": "Static BC",
        "IGP_Weight_Tuning": "IGP Tuning (Memoryless)",
        "IGP_Damped_FT": "IGP Damped",
        "Unnormalized_SRA": "Unnorm. SRA",
        "SRA_NoDwell_Td1": "SRA w/o $T_d$ ($T_d=1$)",
        "Full_SRA_Td5": "Full SRA ($T_d=5$)",
    }
    tick_labels = [short_lbl[m] for m in order]
    colors = {
        "Dijkstra": "#7f8c8d",
        "Reactive_BC_alpha1": "#c0392b",
        "LIRP-D": "#e67e22",
        "Static_BC": "#95a5a6",
        "IGP_Weight_Tuning": "#d35400",
        "IGP_Damped_FT": "#a67c00",
        "Unnormalized_SRA": "#8e44ad",
        "SRA_NoDwell_Td1": "#2980b9",
        "Full_SRA_Td5": "#27ae60",
    }
    markers = {
        "Dijkstra": "d",
        "Reactive_BC_alpha1": "^",
        "LIRP-D": "v",
        "Static_BC": "P",
        "IGP_Weight_Tuning": "X",
        "IGP_Damped_FT": "*",
        "Unnormalized_SRA": "p",
        "SRA_NoDwell_Td1": "s",
        "Full_SRA_Td5": "o",
    }

    # Panel (a): Throughput vs Offered Load on BA (N=100)
    ba_df = df_exp1[df_exp1["topology"] == "BA"]
    for m in order:
        sub = ba_df[ba_df["method"] == m].groupby("load")["throughput"].agg(["mean", "std", "count"]).reset_index()
        ci = ci95_series(sub["std"], sub["count"])
        lw = 2.4 if m == "Full_SRA_Td5" else 1.5
        ls = "-" if m in ("Full_SRA_Td5", "SRA_NoDwell_Td1", "IGP_Weight_Tuning") else "--"
        axes[0].plot(sub["load"], sub["mean"], marker=markers[m], linestyle=ls, linewidth=lw, color=colors[m], label=short_lbl[m])
        axes[0].fill_between(sub["load"], sub["mean"] - ci, sub["mean"] + ci, color=colors[m], alpha=0.12)
    axes[0].set_xticks([0.50, 0.90, 1.20])
    axes[0].set_xlabel("Offered Load $\\rho$ (packets/node/timestep)")
    axes[0].set_ylabel("Throughput (packets/timestep)")
    axes[0].set_title("(a) BA Throughput vs. Offered Load (95% CI)")
    axes[0].grid(True, linestyle="--", alpha=0.45)
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2, fontsize=7.0, framealpha=0.92)

    # Panel (b): Packet Loss vs Route Switch Rate at rho=0.9 on BA
    ba_high = ba_df[np.isclose(ba_df["load"], 0.90)]
    loss_m = [ba_high[ba_high["method"] == m]["drop_rate"].mean() * 100.0 for m in order]
    loss_ci = [
        1.96 * ba_high[ba_high["method"] == m]["drop_rate"].std() * 100.0 / math.sqrt(max(1, len(ba_high[ba_high["method"] == m])))
        for m in order
    ]
    sw_m = [ba_high[ba_high["method"] == m]["switch_rate"].mean() * 100.0 for m in order]
    sw_ci = [
        1.96 * ba_high[ba_high["method"] == m]["switch_rate"].std() * 100.0 / math.sqrt(max(1, len(ba_high[ba_high["method"] == m])))
        for m in order
    ]
    x = np.arange(len(order))
    w = 0.38
    axes[1].bar(x - w / 2, loss_m, width=w, yerr=loss_ci, capsize=2.5, label="Packet Loss Rate (%)", color="#e74c3c", edgecolor="black", linewidth=0.5)
    axes[1].bar(x + w / 2, sw_m, width=w, yerr=sw_ci, capsize=2.5, label="Route Switch Rate (%)", color="#3498db", edgecolor="black", linewidth=0.5)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(tick_labels, rotation=28, ha="right", fontsize=7.8)
    axes[1].set_ylabel("Percentage (%)")
    axes[1].set_ylim(0, 122)
    axes[1].set_title("(b) Loss vs. Control-Plane Switch Rate ($\\rho=0.9$)")
    axes[1].legend(loc="upper left", fontsize=7.8, framealpha=0.92)
    axes[1].grid(axis="y", linestyle="--", alpha=0.45)

    # Panel (c): Cross-Topology Throughput Comparison at rho=0.9 (BA, WS, ER)
    topo_list = ["BA", "WS", "ER"]
    key_methods = [
        ("Dijkstra", "Dijkstra", "#7f8c8d"),
        ("Reactive_BC_alpha1", "Reactive BC ($\\alpha=1$)", "#c0392b"),
        ("IGP_Weight_Tuning", "IGP Tuning (Memoryless)", "#d35400"),
        ("IGP_Damped_FT", "IGP Damped", "#a67c00"),
        ("Static_BC", "Static BC (Open-Loop)", "#95a5a6"),
        ("Full_SRA_Td5", "Full SRA ($T_d=5$)", "#27ae60"),
    ]
    xt = np.arange(len(topo_list))
    bw = 0.13
    for idx_m, (m_key, m_lbl, col_m) in enumerate(key_methods):
        offset = (idx_m - (len(key_methods) - 1) / 2.0) * bw
        sub_t = df_exp1[(df_exp1["method"] == m_key) & (np.isclose(df_exp1["load"], 0.90))]
        vals, errs = [], []
        for tp_name in topo_list:
            s_tp = sub_t[sub_t["topology"] == tp_name]["throughput"]
            vals.append(s_tp.mean())
            errs.append(1.96 * s_tp.std() / math.sqrt(max(1, len(s_tp))))
        axes[2].bar(xt + offset, vals, width=bw, yerr=errs, capsize=2, label=m_lbl, color=col_m, edgecolor="black", linewidth=0.5)
    axes[2].set_xticks(xt)
    axes[2].set_xticklabels(["BA\n(Scale-Free)", "WS\n(Small-World)", "ER\n(Random)"])
    axes[2].set_ylabel("Throughput (packets/timestep)")
    axes[2].set_ylim(0, 105)
    axes[2].set_title("(c) Cross-Topology Throughput ($\\rho=0.9$, 95% CI)")
    axes[2].legend(loc="lower right", fontsize=7.2, framealpha=0.92)
    axes[2].grid(axis="y", linestyle="--", alpha=0.45)

    plt.tight_layout()
    fig.savefig(out_dir / "fig_revision_ablation_baselines.pdf", bbox_inches="tight")
    plt.close(fig)

    # 2. Figure 11: Heterogeneous Demand/Capacity, Time-Varying Surge, and Sensing Noise (3-panel)
    fig, axes = plt.subplots(1, 3, figsize=(18, 4.8))

    # Panel (a): Skewed Pareto W_st & Heterogeneous bimodal mu_i (35% legacy, 65% core) (Noise = 0)
    df_h0 = df_exp2[np.isclose(df_exp2["noise_std"], 0.0)]
    m_order = ["Dijkstra", "Static_BC", "IGP_Weight_Tuning", "Reactive_BC_alpha1", "Topology_Only_SRA", "Generalized_Weighted_SRA"]
    m_labels = ["Dijkstra", "Static BC", "IGP Tuning", "Reactive BC", "Topology SRA", "Weighted SRA"]
    tp_h = [df_h0[df_h0["method"] == m]["throughput"].mean() for m in m_order]
    tp_ci = [1.96 * df_h0[df_h0["method"] == m]["throughput"].std() / math.sqrt(max(1, len(df_h0[df_h0["method"] == m]))) for m in m_order]
    pdr_h = [df_h0[df_h0["method"] == m]["pdr"].mean() * 100.0 for m in m_order]
    pdr_ci = [1.96 * df_h0[df_h0["method"] == m]["pdr"].std() * 100.0 / math.sqrt(max(1, len(df_h0[df_h0["method"] == m]))) for m in m_order]

    ax0_twin = axes[0].twinx()
    b1 = axes[0].bar(np.arange(len(m_order)) - 0.18, tp_h, width=0.35, yerr=tp_ci, capsize=3, color="#2980b9", edgecolor="black", linewidth=0.6, label="Throughput (pkts/step)")
    b2 = ax0_twin.bar(np.arange(len(m_order)) + 0.18, pdr_h, width=0.35, yerr=pdr_ci, capsize=3, color="#27ae60", edgecolor="black", linewidth=0.6, label="PDR (%)")
    axes[0].set_xticks(np.arange(len(m_order)))
    axes[0].set_xticklabels(m_labels, rotation=14, ha="right", fontsize=8.2)
    axes[0].set_ylabel("Throughput (packets/timestep)", color="#2980b9")
    axes[0].set_ylim(0, 95)
    ax0_twin.set_ylabel("Packet Delivery Ratio (%)", color="#27ae60")
    ax0_twin.set_ylim(0, 114)
    axes[0].set_title("(a) Skewed $W_{st}$ & Hetero. Capacity $\\mu_i$")
    axes[0].legend([b1, b2], ["Throughput (pkts/step)", "PDR (%)"], loc="upper left", fontsize=7.8, framealpha=0.92)
    axes[0].grid(axis="y", linestyle="--", alpha=0.45)

    # Panel (b): Time-Varying Traffic Surge (Delivered Throughput with 95% CI + Offered Load Reference)
    tv_steps = tv_stats["steps"]
    offered_curve = [60.0 if t_step <= 350 else (110.0 if t_step <= 700 else 70.0) for t_step in tv_steps]
    axes[1].plot(tv_steps, offered_curve, color="#34495e", linestyle=":", linewidth=1.3, label="Offered Rate ($N\\rho$)")
    for mode_name, lbl_tv, color_c, ls in [
        ("Weighted_SRA", "Weighted SRA ($\\tilde{\\kappa}_i$)", "#1e8449", "-"),
        ("Topology_SRA", "Topology SRA ($\\kappa_i$)", "#2980b9", "-."),
        ("Reactive_BC", "Reactive BC ($\\alpha=1$)", "#c0392b", "--"),
        ("Static_BC", "Static BC", "#a67c00", ":"),
        ("Dijkstra", "Static Dijkstra", "#7f8c8d", (0, (3, 1, 1, 1))),
    ]:
        mean_arr = np.array(tv_stats[mode_name]["tp_mean"])
        ci_arr = np.array(tv_stats[mode_name]["tp_ci"])
        axes[1].plot(tv_steps, mean_arr, label=lbl_tv, color=color_c, linestyle=ls, linewidth=1.9)
        axes[1].fill_between(tv_steps, mean_arr - ci_arr, mean_arr + ci_arr, color=color_c, alpha=0.14)
    axes[1].axvspan(350, 700, color="#f39c12", alpha=0.08)
    axes[1].axvline(350, color="black", linestyle="-.", linewidth=1.0, alpha=0.7)
    axes[1].axvline(700, color="purple", linestyle=":", linewidth=1.1, alpha=0.7)
    axes[1].text(525, 108, "Surge + hotspot shift\n($\\rho: 0.6 \\to 1.1$)", ha="center", va="top", fontsize=7.6, color="#7e5109")
    axes[1].text(850, 108, "Recovery\n($\\rho \\to 0.7$)", ha="center", va="top", fontsize=7.6, color="purple")
    axes[1].set_xlabel("Simulation Timestep")
    axes[1].set_ylabel("Delivered Throughput (packets/timestep)")
    axes[1].set_ylim(0, 120)
    axes[1].set_title("(b) Real-Time Throughput Under Surge + Hotspot Shift")
    axes[1].legend(loc="lower right", fontsize=7.3, framealpha=0.92)
    axes[1].grid(True, linestyle="--", alpha=0.45)

    # Panel (c): Sensing Noise Injection (95% CI shaded bands)
    for m, lbl, col, mk in [
        ("Generalized_Weighted_SRA", "Weighted SRA ($\\alpha=0.1$)", "#1e8449", "o"),
        ("Topology_Only_SRA", "Topology SRA ($\\alpha=0.1$)", "#2980b9", "s"),
        ("Reactive_BC_alpha1", "Memoryless BC ($\\alpha=1.0$)", "#c0392b", "^"),
        ("Static_BC", "Static BC", "#a67c00", "P"),
        ("Dijkstra", "Static Dijkstra", "#7f8c8d", "d"),
    ]:
        sub = df_exp2[df_exp2["method"] == m].groupby("noise_std")["pdr"].agg(["mean", "std", "count"]).reset_index()
        ci = ci95_series(sub["std"], sub["count"])
        axes[2].plot(sub["noise_std"] * 100.0, sub["mean"] * 100.0, marker=mk, color=col, linewidth=1.9, label=lbl)
        axes[2].fill_between(
            sub["noise_std"] * 100.0,
            np.clip((sub["mean"] - ci) * 100.0, 0.0, 100.0),
            np.clip((sub["mean"] + ci) * 100.0, 0.0, 100.0),
            color=col, alpha=0.16,
        )
    axes[2].set_xlabel("Control-Plane Sensing Noise $\\sigma$ (%)")
    axes[2].set_ylabel("Packet Delivery Ratio (%)")
    axes[2].set_title("(c) Robustness to Telemetry Noise (95% CI)")
    axes[2].legend(loc="lower left", fontsize=7.6, framealpha=0.92)
    axes[2].grid(True, linestyle="--", alpha=0.45)

    plt.tight_layout()
    fig.savefig(out_dir / "fig_revision_hetero_timevarying_noise.pdf", bbox_inches="tight")
    plt.close(fig)

    # 3. Figure 13: Dwell-Time Sensitivity & Computational Scalability (2-panel, 95% CI + O(...) fit)
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.3))
    td_sub = df_exp3[np.isclose(df_exp3["alpha"], 0.1) & np.isclose(df_exp3["beta_I"], 10.0)].groupby("T_d").agg(
        pdr_mean=("pdr", "mean"),
        pdr_std=("pdr", "std"),
        pdr_cnt=("pdr", "count"),
        tail_sw_mean=("tail_switch_rate", "mean"),
        sw_mean=("switch_rate", "mean"),
        sw_std=("switch_rate", "std"),
        sw_cnt=("switch_rate", "count"),
    ).reset_index()
    pdr_ci = ci95_series(td_sub["pdr_std"], td_sub["pdr_cnt"])
    sw_ci = ci95_series(td_sub["sw_std"], td_sub["sw_cnt"])

    ax_td2 = axes[0].twinx()
    l1, = axes[0].plot(td_sub["T_d"], np.clip(td_sub["pdr_mean"] * 100.0, 0.0, 100.0), "o-", color="#27ae60", linewidth=2.0, label="PDR (%) [95% CI]")
    axes[0].fill_between(td_sub["T_d"], np.clip((td_sub["pdr_mean"] - pdr_ci) * 100.0, 0.0, 100.0), np.clip((td_sub["pdr_mean"] + pdr_ci) * 100.0, 0.0, 100.0), color="#27ae60", alpha=0.18)
    l2, = ax_td2.plot(td_sub["T_d"], np.clip(td_sub["sw_mean"] * 100.0, 0.0, 105.0), "s--", color="#c0392b", linewidth=2.0, label="Switch Frequency (%)")
    axes[0].set_xticks([1, 2, 3, 5, 8, 10])
    ax_td2.fill_between(td_sub["T_d"], np.clip((td_sub["sw_mean"] - sw_ci) * 100.0, 0.0, 105.0), np.clip((td_sub["sw_mean"] + sw_ci) * 100.0, 0.0, 105.0), color="#c0392b", alpha=0.16)
    axes[0].set_xlabel("Minimum Dwell Time $T_d$ (iterations)")
    axes[0].set_ylabel("Packet Delivery Ratio (%)", color="#27ae60")
    ax_td2.set_ylabel("Route Switch Frequency (% steps)", color="#c0392b")
    axes[0].set_ylim(min(50.0, float((td_sub["pdr_mean"] - pdr_ci).min() * 100.0) - 5.0), 104)
    ax_td2.set_ylim(0, 105)
    axes[0].set_title("(a) Sensitivity to Minimum Dwell Time $T_d$")
    axes[0].legend([l1, l2], ["PDR (%) [95% CI]", "Route Switch Frequency (%)"], loc="center right", fontsize=8.0, framealpha=0.92)
    axes[0].grid(True, linestyle="--", alpha=0.45)

    sc_ba = df_exp4[(df_exp4["topology"] == "BA") & (df_exp4.method == "Full_SRA")].groupby("N").agg(
        E=("E", "mean"),
        mean=("eval_ms", "mean"),
        std=("eval_ms", "std"),
        cnt=("eval_ms", "count"),
        amort=("amortized_iter_ms", "mean"),
    ).reset_index()
    sc_ws = df_exp4[(df_exp4["topology"] == "WS") & (df_exp4.method == "Full_SRA")].groupby("N").agg(
        E=("E", "mean"),
        mean=("eval_ms", "mean"),
        std=("eval_ms", "std"),
        cnt=("eval_ms", "count"),
        amort=("amortized_iter_ms", "mean"),
    ).reset_index()
    ba_ci = ci95_series(sc_ba["std"], sc_ba["cnt"])
    ws_ci = ci95_series(sc_ws["std"], sc_ws["cnt"])

    axes[1].errorbar(sc_ba["N"], sc_ba["mean"], yerr=ba_ci, fmt="o-", capsize=3, color="#2980b9", linewidth=2.0, label="BA Scale-Free ($m=4$)")
    axes[1].fill_between(sc_ba["N"], sc_ba["mean"] - ba_ci, sc_ba["mean"] + ba_ci, color="#2980b9", alpha=0.14)
    axes[1].errorbar(sc_ws["N"], sc_ws["mean"], yerr=ws_ci, fmt="s--", capsize=3, color="#8e44ad", linewidth=2.0, label="WS Small-World ($k=8$)")
    axes[1].fill_between(sc_ws["N"], sc_ws["mean"] - ws_ci, sc_ws["mean"] + ws_ci, color="#8e44ad", alpha=0.14)

    # Theoretical O(N(E + N log2 N)) curve fitted by least squares to BA eval times
    basis_ba = sc_ba["N"] * (sc_ba["E"] + sc_ba["N"] * np.log2(sc_ba["N"]))
    coef = float(np.dot(basis_ba, sc_ba["mean"]) / np.dot(basis_ba, basis_ba))
    n_dense = np.linspace(50, 500, 100)
    e_dense = 4.0 * n_dense - 16.0
    theo_ms = coef * n_dense * (e_dense + n_dense * np.log2(n_dense))
    axes[1].plot(n_dense, theo_ms, "k:", linewidth=1.6, label="Theoretical Fit $O(N(E+N\\log N))$")

    axes[1].set_xlabel("Network Size $N$ (nodes)")
    axes[1].set_ylabel("Wall-Clock Time per Evaluation (ms)")
    axes[1].set_title("(b) Computational Overhead vs. Network Scale $N$ (95% CI)")
    axes[1].legend(loc="upper left", fontsize=8.0, framealpha=0.92)
    axes[1].grid(True, linestyle="--", alpha=0.45)

    plt.tight_layout()
    fig.savefig(out_dir / "fig_revision_dwell_scalability.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CNCOMM-2026-0222 revision simulations")
    parser.add_argument("--max-workers", type=int, default=20, help="Number of worker processes")
    parser.add_argument("--num-seeds", type=int, default=30, help="Number of independent trials per scenario")
    parser.add_argument("--out-dir", type=str, required=True, help="Output directory for results and PDF figures")
    parser.add_argument("--include-ab-grid", action="store_true", help="Also run the 15-seed (alpha, beta_I) grid sweep in Exp-3")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    print(f"[Campaign] Starting CNCOMM-2026-0222 revision campaign with max_workers={args.max_workers}, num_seeds={args.num_seeds}")

    # 1. Exp-1 Tasks (BA, WS, ER across 3 loads and num_seeds trials)
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

    # 2b. Time-varying traffic surge traces (30 seeds parallel)
    tv_runs: List[Dict[str, List[Tuple[int, float, float, float]]]] = []
    with ProcessPoolExecutor(max_workers=args.max_workers) as ex:
        futs = [ex.submit(worker_tv_trial, s) for s in range(args.num_seeds)]
        for f in as_completed(futs):
            tv_runs.append(f.result())

    methods_tv = ["Weighted_SRA", "Topology_SRA", "Static_BC", "Reactive_BC", "Dijkstra"]
    n_pts = len(tv_runs[0]["Weighted_SRA"])
    tv_steps = [pt[0] for pt in tv_runs[0]["Weighted_SRA"]]
    tv_stats: Dict[str, Any] = {"steps": tv_steps}
    for m_tv in methods_tv:
        tp_mat = np.array([[run[m_tv][i][3] for i in range(n_pts)] for run in tv_runs])
        pdr_mat = np.array([[run[m_tv][i][1] for i in range(n_pts)] for run in tv_runs])
        tp_mean = tp_mat.mean(axis=0)
        tp_ci = 1.96 * tp_mat.std(axis=0, ddof=1 if len(tv_runs) > 1 else 0) / math.sqrt(max(1, len(tv_runs)))
        pdr_mean = pdr_mat.mean(axis=0)
        tv_stats[m_tv] = {
            "tp_mean": np.round(tp_mean, 4).tolist(),
            "tp_ci": np.round(tp_ci, 4).tolist(),
            "pdr_mean": np.round(pdr_mean, 4).tolist(),
            "online_switch_rate": float(np.mean([run["online_metrics"][m_tv]["online_switch_rate"] for run in tv_runs])),
            "pre_surge_tp_mean": float(tp_mean[np.array(tv_steps) <= 350].mean()),
            "surge_tp_mean": float(tp_mean[(np.array(tv_steps) > 350) & (np.array(tv_steps) <= 700)].mean()),
            "post_recovery_tp_mean": float(tp_mean[np.array(tv_steps) > 700].mean()),
        }
    print("[Campaign] Exp-2b (time-varying surge traces) finished.")

    # 3. Exp-3 Tasks (Dwell time T_d and (alpha, beta_I) sensitivity)
    exp3_tasks = [
        (300 + s, td, 0.1, 10.0)
        for s in range(args.num_seeds)
        for td in [1, 2, 3, 5, 8, 10]
    ]
    if args.include_ab_grid:
        exp3_tasks += [
            (350 + s, 5, a, b)
            for s in range(15)
            for a in [0.05, 0.1, 0.25, 0.5]
            for b in [2.0, 5.0, 10.0, 20.0, 40.0]
            if (a, b) != (0.1, 10.0)  # baseline Td=5 already has the main 30-seed cohort
        ]
    exp3_rows: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.max_workers) as ex:
        futs = [ex.submit(worker_exp3_dwell, task) for task in exp3_tasks]
        for f in as_completed(futs):
            exp3_rows.append(f.result())
    df_exp3 = pd.DataFrame(exp3_rows)
    df_exp3.to_csv(out_dir / "exp3_dwell_sensitivity.csv", index=False)
    print(f"[Campaign] Exp-3 finished ({len(df_exp3)} rows).")

    # 4. Exp-4 Tasks (Scalability & Official Topology Zoo Backbones, 30 seeds)
    # Run sequentially over seeds within parallel pool to reduce cross-process cache contention
    # for runtime benchmarking; still parallelized across tasks cleanly.
    exp4_tasks = [
        (topo, n_sz, 400 + s)
        for topo in ["BA", "WS"]
        for n_sz in [50, 100, 200, 300, 500]
        for s in range(args.num_seeds)
    ] + [
        (rw_topo, 0, 450 + s)
        for rw_topo in ["Geant2012", "Deltacom", "UsCarrier"]
        for s in range(args.num_seeds)
    ]
    exp4_rows: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.max_workers) as ex:
        futs = [ex.submit(worker_exp4_scalability, task) for task in exp4_tasks]
        for f in as_completed(futs):
            exp4_rows.extend(f.result())
    df_exp4 = pd.DataFrame(exp4_rows)
    df_exp4.to_csv(out_dir / "exp4_scalability_realworld.csv", index=False)
    print(f"[Campaign] Exp-4 finished ({len(df_exp4)} rows).")

    # Generate PDF figures
    generate_figures_and_tables(out_dir, df_exp1, df_exp2, df_exp3, df_exp4, tv_stats)

    # Save structured summary JSON for manuscript tables
    summary = {
        "exp1_ba_load09_paired_vs_full_sra": paired_statistics(
            df_exp1[(df_exp1.topology == "BA") & np.isclose(df_exp1.load, 0.90)],
            "Full_SRA_Td5", ("throughput", "pdr", "switch_rate")),
        "exp2_paired_vs_weighted_sra": paired_statistics(
            df_exp2[np.isclose(df_exp2.noise_std, 0.0)], "Generalized_Weighted_SRA",
            ("max_generalized_stress", "throughput", "pdr", "drop_rate", "avg_latency", "p95_latency", "switch_rate")),
        "exp4_unnorm_scale": df_exp4[df_exp4.method == "Unnormalized_SRA"].groupby("N")[
            ["throughput", "pdr", "switch_rate", "tracking_error", "peak_reduction_pct"]].mean().reset_index().to_dict(orient="records"),
        "elapsed_seconds": round(time.time() - t_start, 2),
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
            tail_switch_rate_mean=("tail_switch_rate", "mean"),
            iters_executed_mean=("iters_executed", "mean"),
            tracking_err_mean=("tracking_error", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp1_ws_load09": df_exp1[(df_exp1["topology"] == "WS") & (np.isclose(df_exp1["load"], 0.90))].groupby("method").agg(
            throughput_mean=("throughput", "mean"),
            throughput_std=("throughput", "std"),
            pdr_mean=("pdr", "mean"),
            drop_mean=("drop_rate", "mean"),
            lat_mean=("avg_latency", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp1_er_load09": df_exp1[(df_exp1["topology"] == "ER") & (np.isclose(df_exp1["load"], 0.90))].groupby("method").agg(
            throughput_mean=("throughput", "mean"),
            throughput_std=("throughput", "std"),
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
        "exp2_noise_all": df_exp2.groupby(["method", "noise_std"]).agg(
            throughput_mean=("throughput", "mean"),
            throughput_std=("throughput", "std"),
            pdr_mean=("pdr", "mean"),
            pdr_std=("pdr", "std"),
        ).round(4).reset_index().to_dict(orient="records"),
        "exp2_tv_surge": {k: v for k, v in tv_stats.items() if k != "steps"},
        "exp3_dwell": df_exp3[np.isclose(df_exp3["alpha"], 0.1) & np.isclose(df_exp3["beta_I"], 10.0)].groupby("T_d").agg(
            throughput_mean=("throughput", "mean"),
            throughput_std=("throughput", "std"),
            pdr_mean=("pdr", "mean"),
            pdr_std=("pdr", "std"),
            switch_rate_mean=("switch_rate", "mean"),
            tail_switch_rate_mean=("tail_switch_rate", "mean"),
            iters_executed_mean=("iters_executed", "mean"),
            tracking_err_mean=("tracking_error", "mean"),
        ).round(4).to_dict(orient="index"),
        "exp4_scalability": df_exp4[df_exp4.method == "Full_SRA"].groupby(["topology", "N"]).agg(
            E_mean=("E", "mean"),
            eval_ms_mean=("eval_ms", "mean"),
            eval_ms_std=("eval_ms", "std"),
            amortized_ms_mean=("amortized_iter_ms", "mean"),
            amortized_ms_std=("amortized_iter_ms", "std"),
            peak_red_mean=("peak_reduction_pct", "mean"),
            peak_red_std=("peak_reduction_pct", "std"),
            dijk_tp=("dijkstra_throughput", "mean"),
            dijk_tp_std=("dijkstra_throughput", "std"),
            sra_tp=("sra_throughput", "mean"),
            sra_tp_std=("sra_throughput", "std"),
            tp_gain_pct=("throughput_gain_pct", "mean"),
            tp_gain_std=("throughput_gain_pct", "std"),
            dijk_drop=("dijkstra_drop_rate", "mean"),
            sra_drop=("sra_drop_rate", "mean"),
        ).round(4).reset_index().to_dict(orient="records"),
    }
    with open(out_dir / "summary_metrics.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"[Campaign] All figures and summary_metrics.json saved to {out_dir} in {summary['elapsed_seconds']:.1f}s.")


if __name__ == "__main__":
    main()
