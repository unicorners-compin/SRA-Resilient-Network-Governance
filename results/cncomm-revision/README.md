# CNCOMM-2026-0222 Major Revision Simulation Results

## Overview
This directory contains the formal simulation outputs and generated figures for the first-round Major Revision of **CNCOMM-2026-0222** (*"System Relaxation for Resilient Network Governance: A Model-Driven Control Mechanism Against Structural Stress Concentration"*).

## Execution & Tencent Cloud COS Archive Provenance
- **Compute Host**: `node09` (Intel Xeon Gold 6248R @ 3.00 GHz, 44-core Task Spooler pool via `/home/rzy/research/bin/node09-ts-run 20`)
- **Run ID**: `cncomm-2026-0222-rev-20261109T113518Z`
- **GitHub Actions Run ID**: `42610260124` (`unicorners-compin/SRA-Resilient-Network-Governance`)
- **Tencent Cloud COS Bucket**: `compin-team-docs-1326842184` (`ap-chengdu`)
- **COS Prefix**: `users/rzy/simulation-results/SRA-Resilient-Network-Governance/cncomm-2026-0222-rev-20261109T113518Z/`
  - Archive: `cncomm-2026-0222-rev-20261109T113518Z.tar.gz` (SHA256: `8492bb00259101d6a7afecac054bdc9a540488d48b9e5d99603c40bc970411eb`)
  - Manifest: `manifest.json` (SHA256: `edd50a1604d6a4403d03ed304aef6b9ea539b2d19f62ed576f65836e9fd6d048`)

## Main Output Files
- `summary_metrics.json`: Aggregated metrics (mean, SD, and 95% confidence intervals across 30 seeds) for all four revision experiment suites:
  - `exp1`: Component ablation study and stronger baselines (`Dijkstra`, `Memoryless Reactive BC`, `SRA w/o Dwell`, `Static BC`, `LIRP-D`, `IGP Weight Tuning (Fortz-Thorup)`, `SRA Linear`, `Full SRA`).
  - `exp2`: Non-uniform Pareto gravity traffic demand $W_{st}$, heterogeneous node capacities $\mu_i$, time-varying $2.2\times$ traffic surge, and telemetry sensing noise $\sigma \in \{0\%, 5\%, 10\%, 20\%, 30\%\}$.
  - `exp3`: Dwell-time sensitivity $T_d \in \{1, 2, 3, 5, 8, 10\}$ and joint $(\alpha, \beta_I)$ grid sensitivity.
  - `exp4`: Computational complexity, wall-clock runtime per iteration, and scalability across `BA` ($N \in \{50, 100, 200, 300, 500\}$) and real-world research backbones (`NSFNET`, `GEANT`).
- `fig_revision_ablation_baselines.pdf`: Figure 9 in the revised manuscript (ablation & baseline comparison).
- `fig_revision_hetero_timevarying_noise.pdf`: Figure 10 in the revised manuscript (skewed demand, time-varying surge, and noise robustness).
- `fig_revision_dwell_scalability.pdf`: Figure 12 in the revised manuscript ($T_d$ sensitivity, runtime scaling, and throughput scaling up to $N=500$).
