# System Relaxation for Resilient Network Governance (SRA)

Official repository for the manuscript:

> **System Relaxation for Resilient Network Governance: A Model-Driven Control Mechanism Against Structural Stress Concentration**  
> *Jie Ding, Zhiyuan Ren, Yuehan Li, Wenchi Cheng, and Zhiliang Shuai*  
> Submitted to *China Communications* (Manuscript ID: **CNCOMM-2026-0222**, Major Revision).

---

## Repository Structure

- `paper/`
  - `sra_CC/main_ccjnl.tex`: Revised manuscript formatted in the official *China Communications* (`ccjnl`) template, with all first-round revision changes highlighted in blue (`\rev{...}`).
  - `main.tex`: Revised manuscript in the IEEE Transactions (`IEEEtran`) format, synchronized with `main_ccjnl.tex` and highlighted in blue (`\rev{...}`).
  - `Response_Letter_CNCOMM_2026_0222.md` & `Response_Letter_CNCOMM_2026_0222.tex`: Point-to-Point Response Letter addressing all comments from the Associate Editor, Reviewer 1 (34 points), and Reviewer 2 (5 major concerns).
  - `references.bib` / `sra_CC/references.bib`: Updated BibTeX bibliography.
  - Figures (`*.pdf`, `*.png`): All vector figures including restored stability/sensitivity plots (`ren_fig2_lyapunov.pdf`, `ren_fig3_dwell_time.pdf`, `sensitivity_3d_surfaces_full.pdf`) and new revision experiment figures (`fig_revision_ablation_baselines.pdf`, `fig_revision_hetero_timevarying_noise.pdf`, `fig_revision_dwell_scalability.pdf`).
- `scripts/`
  - `run_revision_campaign.py`: Multi-seed parallel simulation campaign runner implementing all 4 revision experiment suites (Exp-1: Component Ablation & Stronger Baselines including Fortz–Thorup IGP Weight Tuning and Static Centrality; Exp-2: Skewed Pareto Gravity Demand, Heterogeneous Capacities, Time-Varying Traffic Surge, and Telemetry Noise Injection; Exp-3: Dwell-Time $T_d$ and $(\alpha, \beta_I)$ Sensitivity; Exp-4: Computational Complexity, Runtime Overhead, and Scalability across $N=50..500$ + Real-World `NSFNET` & `GEANT` Backbones).
- `src/`
  - Original simulation notebook (`SRA算法.ipynb`).
- `results/cncomm-revision/`
  - `summary_metrics.json`: Complete 30-seed statistical results (mean, SD, 95% CI).
  - `manifest.json` & `README.md`: Execution provenance and Tencent Cloud COS archive index (`users/rzy/simulation-results/SRA-Resilient-Network-Governance/cncomm-2026-0222-rev-20261109T113518Z/`).

---

## Reproducing the Simulation Campaign

```bash
python3 scripts/run_revision_campaign.py --max-workers 20 --num-seeds 30 --out-dir results/cncomm-revision
```
