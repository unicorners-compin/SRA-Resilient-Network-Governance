# System Relaxation for Resilient Network Governance (SRA)

Official repository for the manuscript:

> **System Relaxation for Resilient Network Governance: A Model-Driven Control Mechanism Against Structural Stress Concentration**  
> *Jie Ding, Zhiyuan Ren, Yuehan Li, Wenchi Cheng, and Zhiliang Shuai*  
> Submitted to *China Communications* (Manuscript ID: **CNCOMM-2026-0222**, Major Revision).

---

## Repository Structure

- `paper/`
  - `sra_CC/main_ccjnl.tex` & `sra_CC/main_ccjnl.pdf`: Revised manuscript formatted in the official *China Communications* (`ccjnl`) template, with all first-round revision changes highlighted in blue (`\rev{...}`).
  - `sra_CC/main_ccjnl_clean.tex` & `sra_CC/main_ccjnl_clean.pdf`: Clean (unmarked) *China Communications* manuscript compiled from the synchronized source.
  - `main.tex` & `main.pdf`: Revised manuscript in the IEEE Transactions (`IEEEtran`) format, synchronized with `main_ccjnl.tex` and highlighted in blue (`\rev{...}`).
  - `sm.tex` & `sm.pdf`: Standalone Supplementary Material containing complete formal mathematical proofs (Sections S-A through S-J).
  - `sra_CC/Response_Letter_CNCOMM_2026_0222.tex` & `Response_Letter_CNCOMM_2026_0222.pdf` (`Response_Letter_CNCOMM_2026_0222.md`): Point-to-Point Response Letter addressing all comments from the Associate Editor, Reviewer 1 (34 points), and Reviewer 2 (5 major concerns).
  - `refs.bib` / `references.bib` / `sra_CC/refs.bib`: Synchronized BibTeX bibliography.
  - Figures (`*.pdf`, `*.eps`): Vector figures including stability/sensitivity plots (`ren_fig2_lyapunov.pdf`, `ren_fig3_dwell_time.pdf`, `sensitivity_3d_surfaces_full.pdf`) and revision experiment figures (`fig_revision_ablation_baselines.pdf`, `fig_revision_hetero_timevarying_noise.pdf`, `fig_revision_dwell_scalability.pdf`).
- `data/topologies/`
  - Official Internet Topology Zoo GML carrier topologies (`Geant2012.gml`, `Deltacom.gml`, `UsCarrier.gml`).
- `scripts/`
  - `run_revision_campaign.py`: Multi-seed parallel simulation campaign runner implementing all 4 revision experiment suites (Exp-1: Component Ablation & Stronger Baselines including Fortz–Thorup IGP Weight Tuning and Static Centrality; Exp-2: Skewed Pareto Gravity Demand, Heterogeneous Capacities, Time-Varying Traffic Surge, and Telemetry Noise Injection; Exp-3: Dwell-Time $T_d$ and $(\alpha, \beta_I)$ Sensitivity; Exp-4: Computational Complexity, Runtime Overhead, and Scalability across $N=50..500$ + Real-World Internet Topology Zoo `Geant2012`, `Deltacom`, and `UsCarrier` backbones).
- `src/`
  - Discrete-event simulator components (`base_simulator.py`, `dijkstra_final.py`, `lirp_d_final.py`, `qroute_final.py`, `sra_final.py`).
- `results/cncomm-revision/`
  - `summary_metrics.json`, `exp1_ablation_baselines.csv`, `exp2_hetero_noise.csv`, `exp3_dwell_sensitivity.csv`, `exp4_scalability_realworld.csv`, `manifest.json`, and `README.md`: Complete 30-seed statistical results (mean, SD, 95% CI) and SHA256 verification manifest.

---

## Reproducing the Simulation Campaign

```bash
python3 scripts/run_revision_campaign.py --max-workers 20 --num-seeds 30 --out-dir results/cncomm-revision
```
