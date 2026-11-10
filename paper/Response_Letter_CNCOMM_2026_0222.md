# Point-to-Point Response to Reviewers

- **Journal**: *China Communications*
- **Manuscript ID**: `CNCOMM-2026-0222`
- **Title**: *System Relaxation for Resilient Network Governance: A Model-Driven Control Mechanism Against Structural Stress Concentration*
- **Authors**: Jie Ding, Zhiyuan Ren, Yuehan Li, Wenchi Cheng, and Zhiliang Shuai

---

Dear Associate Editor-in-Chief Prof. Ying-Chang Liang, Associate Editor, and Anonymous Reviewers,

We sincerely thank the Associate Editor-in-Chief, the Associate Editor, and the two anonymous Reviewers for their thorough reading, insightful critiques, and constructive suggestions on our manuscript (ID: **CNCOMM-2026-0222**). Your comments have helped us significantly strengthen the theoretical rigor, experimental breadth, and presentation clarity of our work.

In accordance with the journal guidelines, all modifications in the revised manuscript (`main_ccjnl.tex` / `main.tex`) are **highlighted in blue text** (`\rev{...}`). Below, we first summarize the major improvements made in this revision, followed by a detailed, point-to-point response to each comment from the Associate Editor, Reviewer 1, and Reviewer 2.

---

## Executive Summary of Major Revisions

1. **Positioning, Research Gap, and Comparative Taxonomy (Section I, Table I, Section II-B)**:
   - Explicitly isolated the research gap between reactive queue-based load balancing, traffic-matrix-dependent IGP link-weight optimization (Fortz & Thorup), open-loop static centrality routing, and black-box AI/DRL controllers.
   - Expanded **Table I** into a 6-column feature-by-feature comparison covering *Control Signal*, *Feedback Loop*, *Adaptation Mode*, *Damping / Hysteresis*, *Complexity*, and *Key Limitation*.

2. **Rigorous Problem Formulation and Generalized Demand-/Capacity-Weighted Stress (Section III-A, Eq. (2), Eq. (5))**:
   - Introduced explicit **Assumptions 1–4** clarifying topological connectivity, observation cadence, capacity regularity, and baseline queue dynamics.
   - Formulated the **generalized demand- and capacity-weighted structural stress** $\widetilde{\kappa}_i(S; W, \mu)$ in **Eq. (2)**, which handles skewed end-to-end traffic matrices $W=[W_{st}]$ and heterogeneous node service capacities $\mu_i$, while recovering topological betweenness centrality as a traffic-agnostic special case.
   - Added a formal **bi-criteria discrete-time optimization problem formulation (Eq. (5))** over control epochs balancing long-run peak stress and route-switching cost subject to leaky-integrator state dynamics $S^{(k+1)}=(1-\alpha)S^{(k)}+\alpha q^{(k)}$ and minimum dwell-time spacing $\tau_{m+1}-\tau_m \ge T_d$.

3. **Repaired Mathematical Proofs and Theoretical Clarifications (Section III-C/D/E, Appendices A, B, C, D, I, J)**:
   - **Lemma 1 & Appendix A**: Defined the coordinate-wise box-violation sequences $\delta^+_{k,i} := \max\{S_i^{(k)}-1, 0\}$ and $\delta^-_{k,i} := \max\{-S_i^{(k)}, 0\}$, proving positive invariance of $X = [0, 1]^N$ and exponential attraction from perturbed initial states $S^{(0)} \in [-1/\beta_I+\epsilon, \infty)^N$.
   - **Proposition 1, Theorem 1, Remark 2, & Appendices B–C**: Defined the Krasovskii set-valued regularization $\mathcal{N}(S) := \bigcap_{\delta>0}\overline{\mathrm{co}}(\mathrm{norm}(\kappa(B_\delta(S))))$ and clarified the distinction between **global attraction on $X$ to the compact invariant limit set $\Omega = \bigcap_{n \ge 0} F^n(X)$** (verified via Aubin–Cellina upper-semicontinuous set-valued mappings) and convergence to a single static fixed point, explaining why multi-path routing ties can induce bounded limit cycles or invariant subsets within $\Omega$ that are temporally regularized by dwell-time gating $T_d$.
   - **Theorem 2 & Appendix D**: Replaced the heuristic continuous-time analogy with an exact discrete-time one-step Drop-Jump inequality for the **implemented normalized feedback $q^{(k)} = \mathrm{norm}(\kappa^{(k)})$** and tracking energy $E_k = \|S^{(k)} - q^{(k)}\|_2^2$, proving $E_{k+1} \le (1-\alpha)E_k + \frac{1}{\alpha}\|q^{(k)}-q^{(k+1)}\|_2^2 \le (1-\alpha)E_k + \bar{\Delta}^2/\alpha$ and $\limsup_{k\to\infty} E_k \le \bar{\Delta}^2/\alpha^2$.
   - **Lemma 2 & Appendix I**: Replaced the circular conservation argument with an explicit **Route-Redistribution Budget $B_j^{(m)} := (\kappa_j^{(m+1)} - \kappa_j^{(m)})_+$** and **Non-Overloading Diversion Condition** ($\kappa_j^{(m)} + B_j^{(m)} \le \kappa_{\max}^{(m)} - \delta$) guaranteeing strict peak stress reduction $\kappa_{\max}^{(m+1)} \le \kappa_{\max}^{(m)} - \delta$.
   - **Proposition 3 & Appendix J**: Fixed the reversed minimum inequality ($\rho_{\max}(\kappa) = \min_{i\in V}(\mu_i/\kappa_i) \ge \mu_{\min}/\kappa_{\max} =: L(\kappa)$) and proved three rigorous capacity statements: (i) an unconditional improvement in the guaranteed safe arrival-rate lower bound $L(\kappa') > L(\kappa)$, (ii) exact proportionality $\rho_{\max}(\kappa')/\rho_{\max}(\kappa) = \kappa_{\max}/\kappa'_{\max}$ under homogeneous capacities ($\mu_i \equiv \mu$) or $\rho_{\max}(\widetilde{\kappa}')/\rho_{\max}(\widetilde{\kappa}) = \widetilde{\kappa}_{\max}/\widetilde{\kappa}'_{\max}$ under generalized capacity-normalized stress $\widetilde{\kappa}_i(S;W,\mu)$, and (iii) the exact joint (`AND`) sufficient slack conditions ($\mu_u/(\kappa_{\max}-d) \ge \rho_0$ and $\mu_j/(\kappa_j+B_j) \ge \rho_0,\ \forall j\neq u$) under heterogeneous $\mu_i$ with unweighted centrality.

4. **Restored Missing Figures and Added Comprehensive New Experiments (Section IV-F, IV-G, IV-H, Tables 4–5 / Tables IV–V, Figs. 6, 7, 10, 11, 12, 13)**:
   - **Restored Figures**: Integrated `ren_fig2_lyapunov.pdf` (**Fig. 6**, Lyapunov tracking energy decay), `ren_fig3_dwell_time.pdf` (**Fig. 7**, phase portrait and switching frequency with/without dwell time), and `sensitivity_3d_surfaces_full.pdf` (**Fig. 12**, joint 3D sensitivity over $(\alpha, \beta_I)$).
   - **Component Ablation & Stronger Baselines (Section IV-F, Table 4 / Table IV, Fig. 10)**: Evaluated 8 variants across 30 independent random seeds (reporting mean $\pm$ SD and normal-approximation 95% CIs $[\bar{x} \pm 1.96\,s/\sqrt{30}]$), including *Memoryless Reactive BC ($\alpha=1$)*, *Unnormalized SRA (No $\mathrm{norm}(\cdot)$)*, *SRA w/o Dwell ($T_d=1$)*, *Static BC*, *LIRP-D*, and *Online IGP Weight Tuning (Fortz–Thorup)*, demonstrating that Full SRA ($\alpha=0.1, \beta_I=10, T_d=5$) achieves top-tier throughput ($89.76 \pm 0.76$ pkts/step, $99.65\%$ PDR) while cutting route switching frequency by **$79.7\%$** ($20.0\%$ vs. $98.3\%$).
   - **Skewed Pareto Gravity Traffic, Heterogeneous Capacities, Time-Varying Surge, and Sensing Noise (Section IV-G, Fig. 11)**: Validated generalized weighted SRA under Pareto gravity demands ($w_i \sim \mathrm{Pareto}(1.5)$, $W_{st} \propto w_s w_t$), heterogeneous capacities, a $2\times$ non-stationary traffic surge, and multiplicative telemetry noise $\sigma \in \{0\%, 5\%, 10\%, 20\%\}$.
   - **Dwell-Time Sensitivity, Scalability ($N=50..500$), Runtime Benchmarks, and Real-World Backbones (Section IV-H, Table 5 / Table V, Fig. 13)**: Benchmarked `NSFNET` ($N=14$, $0.35$ ms/step), `GEANT` ($N=22$, $0.89$ ms/step), and scale-free graphs up to $N=500$ ($902.95$ ms/step, where SRA improves seedwise relative throughput by **$+108.33\%$** over Dijkstra).

5. **Dedicated Limitations Subsection & Open-Source Reproducibility (Section V-B, Section V-C)**:
   - Added **Section V-B** consolidating model assumptions, failure cases (e.g., homogeneous regular lattices/tori with $<2\%$ gain and ultra-sparse single-bridge trees), and telemetry/scalability limitations.
   - Released all source code, LaTeX manuscripts, and multi-seed simulation pipelines in an open-source repository (`https://github.com/unicorners-compin/SRA-Resilient-Network-Governance`).

---

## Response to Associate Editor (Editor: 2)

- **Editor Comment 1**: Established novelty via expanded 6-column **Table 1 (Table I)**, expanded **Section II-B**, formal optimization problem **Eq. (5)** in **Section III-A**, and direct empirical benchmarking against *Fortz–Thorup Online IGP Weight Tuning* and *Static Centrality Routing* in **Section IV-F (Table 4 / Table IV, Fig. 10)**.
- **Editor Comment 2**: Repaired all proofs in **Section III-C/D/E** and **Appendices A, B, C, D, I, and J**, clarifying compact limit set attraction $\Omega = \bigcap_{n \ge 0} F^n(X)$ on $X=[0,1]^N$ vs. unique fixed points (**Theorem 1 & Remark 2**), exact discrete-time Drop-Jump tracking energy bounds (**Theorem 2**), non-circular route-redistribution budgets (**Lemma 2**), and exact capacity lower-bound & heterogeneous slack conditions (**Proposition 3**).
- **Editor Comment 3**: Added comprehensive 30-seed ablation studies, stronger baselines, Pareto gravity / heterogeneous capacity / time-varying surge / sensing noise experiments, dwell-time sensitivity, and runtime/scalability benchmarks up to $N=500$ and on `NSFNET`/`GEANT` in **Sections IV-F, IV-G, and IV-H**.
- **Editor Comment 4**: Formalized **Assumptions 1–4** in **Section III-A**, introduced generalized demand-/capacity-weighted stress $\widetilde{\kappa}_i(S; W, \mu)$ in **Eq. (2)**, consolidated limitations in **Section V-B**, and open-sourced all code and data in **Section V-C**.

---

## Response to Reviewer 1 (R1.1 – R1.34)

All 34 checklist items have been addressed point-by-point in `Response_Letter_CNCOMM_2026_0222.tex` and reflected in `main_ccjnl.tex` and `main.tex`.

---

## Response to Reviewer 2 (Comments 1 – 5)

All 5 detailed technical and mathematical comments have been thoroughly addressed in `Response_Letter_CNCOMM_2026_0222.tex` and reflected in `main_ccjnl.tex` and `main.tex`.
