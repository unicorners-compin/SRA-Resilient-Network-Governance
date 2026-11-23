# CNCOMM-2026-0222 Major Revision Simulation Results

## Overview
This directory contains the reproducible simulation outputs and generated figures for the first-round Major Revision of **CNCOMM-2026-0222** (*"System Relaxation for Resilient Network Governance: A Model-Driven Control Mechanism Against Structural Stress Concentration"*).

## Execution Provenance
- **Hardware**: Intel Xeon Gold 6248R CPU @ 3.00 GHz (20-worker parallel `ProcessPoolExecutor` campaign)
- **Command**: `python3 scripts/run_revision_campaign.py --max-workers 20 --num-seeds 30 --out-dir results/cncomm-revision`
- **Real-World Topologies**: Official Internet Topology Zoo `.gml` files (`data/topologies/{Geant2012,Deltacom,UsCarrier}.gml`)

## Main Output Files
- `summary_metrics.json`: Aggregated statistics (mean, SD, and 95% confidence intervals across 30 seeds) for all four revision experiment suites:
  - `exp1`: Component ablation study and stronger baselines (`Dijkstra`, `LIRP-D`, `Static_BC`, `IGP_Weight_Tuning`, `Reactive_BC_alpha1`, `Unnormalized_SRA`, `SRA_NoDwell_Td1`, `Full_SRA_Td5`) across `BA`, `WS`, `ER`.
  - `exp2`: Non-uniform Pareto gravity traffic demand ($W_{st}$), non-aligned heterogeneous node capacities ($\mu_i \sim \mathrm{Uniform}[0.6, 1.6]\,\mu$), time-varying traffic surge ($\rho: 0.6 \to 1.1 \to 0.7$), and telemetry sensing noise ($\sigma \in \{0\%, 5\%, 10\%, 20\%, 30\%\}$).
  - `exp3`: Minimum dwell-time sensitivity $T_d \in \{1, 2, 3, 5, 8, 10\}$ and joint $(\alpha, \beta_I)$ sensitivity grid.
  - `exp4`: Computational complexity, wall-clock evaluation runtime (`eval_ms`) and $T_d=5$ amortized epoch runtime (`amortized_iter_ms`), and throughput scaling across `BA` ($N \in \{50, 100, 200, 300, 500\}$), `WS` ($N \in \{50, 100, 200, 300, 500\}$), and official Internet Topology Zoo carrier backbones (`Geant2012`, `Deltacom`, `UsCarrier`).
- `fig_revision_ablation_baselines.pdf`: Figure 10 in the revised manuscript (3-panel ablation, churn, and cross-topology baseline comparison).
- `fig_revision_hetero_timevarying_noise.pdf`: Figure 11 in the revised manuscript (skewed demand/heterogeneous capacity, time-varying surge delivered throughput, and sensing noise robustness).
- `fig_revision_dwell_scalability.pdf`: Figure 13 in the revised manuscript ($T_d$ sensitivity, runtime scaling with $O(N(E+N\log N))$ theoretical fit).
- `manifest.json`: SHA256 verification checksums for all campaign data files.
