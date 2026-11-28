# CNCOMM-2026-0222 Major Revision Simulation Results

## Overview
This directory contains the reproducible simulation outputs and generated figures for the first-round Major Revision of **CNCOMM-2026-0222** (*"System Relaxation for Resilient Network Governance: A Model-Driven Control Mechanism Against Structural Stress Concentration"*).

## Execution Provenance
- **Hardware**: Intel Xeon Gold 6248R CPU @ 3.00 GHz (36-worker parallel `ProcessPoolExecutor` campaign)
- **Command**: `python3 scripts/run_revision_campaign.py --max-workers 36 --num-seeds 30 --out-dir results/cncomm-revision`
- **Real-World Topologies**: Official Internet Topology Zoo `.gml` files (`data/topologies/{Geant2012,Deltacom,UsCarrier}.gml`)

## Main Output Files
- `summary_metrics.json`: Aggregated statistics (mean, SD, 95% confidence intervals, and paired Holm–Bonferroni Wilcoxon tests across 30 seeds; $K_{\max}=200$, $T=1000$, warmup $=200$, steady-state orbit replay) for all four revision experiment suites:
  - `exp1`: Component ablation study and stronger baselines (`Dijkstra`, `LIRP-D`, `Static_BC`, `IGP_Weight_Tuning`, `IGP_Damped_FT`, `Reactive_BC_alpha1`, `Unnormalized_SRA`, `SRA_NoDwell_Td1`, `Full_SRA_Td5`) across `BA`, `WS`, `ER`.
  - `exp2`: Non-uniform Pareto gravity traffic demand ($W_{st}$), degree-independent bimodal heterogeneous node capacities ($35\%$ legacy $\mu_i \sim \mathrm{Uniform}[3, 5]$, $65\%$ core $\mu_i \sim \mathrm{Uniform}[10, 16]$ pkts/step), fair-start time-varying traffic surge + hotspot demand shift ($\rho: 0.6 \to 1.1 \to 0.7$, $W^{(1)} \to W^{(2)}$ at $t=350$), and telemetry sensing noise ($\sigma \in \{0\%, 5\%, 10\%, 20\%, 30\%\}$).
  - `exp3`: Minimum dwell-time sensitivity $T_d \in \{1, 2, 3, 5, 8, 10\}$ under unified $K_{\max}=200$ and steady-state orbit replay.
  - `exp4`: Computational complexity, wall-clock evaluation runtime (`eval_ms`) and $T_d=5$ amortized epoch runtime (`amortized_iter_ms`), throughput scaling across `BA` ($N \in \{50, 100, 200, 300, 500\}$, incl. cross-scale `Unnormalized_SRA`), `WS` ($N \in \{50, 100, 200, 300, 500\}$), and official Internet Topology Zoo carrier backbones (`Geant2012`, `Deltacom`, `UsCarrier`).
- `fig_revision_ablation_baselines.pdf`: Figure 10 in the revised manuscript (3-panel ablation, churn, and cross-topology baseline comparison).
- `fig_revision_hetero_timevarying_noise.pdf`: Figure 11 in the revised manuscript (skewed demand/heterogeneous capacity, time-varying surge delivered throughput, and sensing noise robustness).
- `fig_revision_dwell_scalability.pdf`: Figure 13 in the revised manuscript ($T_d$ sensitivity, runtime scaling with $O(N(E+N\log N))$ theoretical fit).
- `manifest.json`: SHA256 verification checksums for all campaign data files.

## Tencent Cloud COS Archive (Readback Verified)
- **Bucket / Region**: `compin-team-docs-1326842184` (`ap-chengdu`)
- **Archive Tarball Key**: `users/rzy/simulation-results/SRA-Resilient-Network-Governance/cncomm-revision-v2-30seed-20261128/cncomm-revision-v2-30seed-20261128.tar.gz` (`296912` bytes, SHA-256: `57be5201d19861967c12aa1617434744ebc3f3e80863b486724b84a6b659bac6`)
- **Manifest Key**: `users/rzy/simulation-results/SRA-Resilient-Network-Governance/cncomm-revision-v2-30seed-20261128/cncomm-revision-v2-30seed-20261128.manifest.json` (`834` bytes, SHA-256: `67c5428a34dbe83a949425f18cf2f6d2be231d30fafeb4c3a8ffdd45159d1fa6`)
- **Readback Check**: `compin-cos-direct head` + `get` + `sha256sum` + `cmp -s` (`CMP_TAR_OK`, `CMP_MAN_OK`).
