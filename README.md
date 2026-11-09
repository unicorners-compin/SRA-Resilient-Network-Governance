# SRA-Resilient-Network-Governance

**System Relaxation for Resilient Network Governance: A Model-Driven Control Mechanism Against Structural Stress Concentration**  
*Manuscript ID: CNCOMM-2026-0222 (China Communications)*

## Repository Structure

- `paper/`: Complete LaTeX manuscript sources, bibliographies, and figures migrated from Google Drive (`论文 - 2026 - SRA`).
  - `paper/main.tex`: Main manuscript (IEEEtran layout).
  - `paper/sra_CC/main_ccjnl.tex`: Official *China Communications* (`ccjnl.cls`) manuscript and `figures/`.
  - `paper/mainV2.tex` & `paper/sm.tex`: Extended manuscript and supplementary material with Lyapunov drop-jump, dwell-time anti-chattering, and 3D hyperparameter sensitivity figures.
- `src/`: Core discrete-event simulation modules (`base_simulator.py`, `sra_final.py`, `dijkstra_final.py`, `lirp_d_final.py`, `qroute_final.py`).
- `scripts/`: Multi-topology simulation runners, sensitivity analysis scripts, and the original `SRA_algo.ipynb`.
- `docs/`: Revision plans, mathematical audits, and point-to-point response documents (`CNCOMM-2026-0222-Revision-Plan.md`).
- `results/`: Simulation outputs and statistical validation artifacts.
