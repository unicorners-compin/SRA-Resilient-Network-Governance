# Point-to-Point Response to Reviewers

**Journal**: *China Communications*  
**Manuscript ID**: CNCOMM-2026-0222  
**Title**: *System Relaxation for Resilient Network Governance: A Model-Driven Control Mechanism Against Structural Stress Concentration*  
**Authors**: Jie Ding, Zhiyuan Ren, Yuehan Li, Wenchi Cheng, and Zhiliang Shuai  

---

Dear Associate Editor-in-Chief Prof. Ying-Chang Liang, Associate Editor, and Anonymous Reviewers,

We sincerely thank the Associate Editor-in-Chief, the Associate Editor, and the two anonymous Reviewers for their thorough reading, insightful critiques, and constructive suggestions on our manuscript (ID: **CNCOMM-2026-0222**). Your comments have helped us significantly strengthen the theoretical rigor, experimental breadth, and presentation clarity of our work.

In accordance with the journal guidelines, all modifications in the revised manuscript (`main_ccjnl.tex` / `main.tex`) are **highlighted in blue text** (`\rev{...}`). Below, we first summarize the major improvements made in this revision, followed by a detailed, point-by-point response to each comment from the Associate Editor, Reviewer 1, and Reviewer 2.

---

## Executive Summary of Major Revisions

1. **Positioning, Research Gap, and Comparative Taxonomy (Section I, Table I, Section II-B)**:
   - Explicitly isolated the research gap between reactive queue-based load balancing, traffic-matrix-dependent IGP link-weight optimization (Fortz & Thorup), open-loop static centrality routing, and black-box AI/DRL controllers.
   - Expanded **Table I** into a 6-column feature-by-feature comparison covering *Control Signal*, *Feedback Loop*, *Adaptation Mode*, *Damping / Hysteresis*, *Complexity*, and *Key Limitation*.

2. **Rigorous Problem Formulation and Generalized Demand-/Capacity-Weighted Stress (Section III-B, Eq. (2), Eq. (5))**:
   - Introduced explicit **Assumptions 1–4** clarifying topological connectivity, observation cadence, capacity regularity, and baseline queue dynamics.
   - Formulated the **generalized demand- and capacity-weighted structural stress** $\widetilde{\kappa}_i(S; W, \mu)$ in **Eq. (2)**, which handles skewed end-to-end traffic matrices $W=[w_{st}]$ and heterogeneous node service capacities $\mu_i$, while recovering topological betweenness centrality as a traffic-agnostic special case.
   - Added a formal **bi-criteria optimization problem formulation (Eq. (5))** over discrete control epochs balancing expected peak stress and route recalculation switching cost.

3. **Repaired Mathematical Proofs and Theoretical Clarifications (Section III-C/D, Appendices A, C, D, I, J)**:
   - **Lemma 1 & Appendix A**: Restored explicit definitions of the upper/lower variation sequences $\delta^+_{k,i}$ and $\delta^-_{k,i}$ and proved bounded state trajectories $S^{(k)} \in [0, 1]^N$.
   - **Theorem 1, Remark 2, & Appendix C**: Clarified the distinction between **global attraction to a compact invariant limit set $\Omega = \bigcap_{n \ge 0} F^n(X)$** (verified via Aubin–Cellina upper-semicontinuous set-valued mappings) and convergence to a single static fixed point, explaining why multi-path routing ties naturally induce bounded limit cycles within $\Omega$ that are stabilized by dwell-time hysteresis $T_d$.
   - **Theorem 2 & Appendix D**: Replaced the heuristic continuous-time analogy with an exact discrete-time one-step dissipation-injection inequality for the **implemented normalized feedback $q^{(k)} = \mathrm{norm}(\kappa^{(k)})$** and tracking energy $E_k = \|S^{(k)} - q^{(k)}\|_2^2$.
   - **Lemma 2 & Appendix I**: Replaced the circular conservation argument with an explicit **Route-Redistribution Budget $B_j^{(m)}$** and **Non-Overloading Diversion Condition** guaranteeing peak stress reduction $\kappa'_{\max} < \kappa_{\max}$.
   - **Proposition 3 & Appendix J**: Fixed the reversed minimum inequality and proved three rigorous capacity statements: (i) an unconditional improvement in the guaranteed safe throughput lower bound $L(\kappa') > L(\kappa)$, (ii) exact proportionality $\rho_{\max}(\kappa')/\rho_{\max}(\kappa) = \kappa_{\max}/\kappa'_{\max}$ under homogeneous capacities or generalized capacity-normalized stress $\widetilde{\kappa}_i$, and (iii) the exact joint (`AND`) sufficient condition under heterogeneous $\mu_i$ with unweighted centrality.

4. **Restored Missing Figures and Added Comprehensive New Experiments (Section IV-F, IV-G, IV-H, Tables III–IV, Figs. 5, 6, 9, 10, 11, 12)**:
   - **Restored Figures**: Integrated `ren_fig2_lyapunov.pdf` (**Fig. 5**, Lyapunov tracking energy decay), `ren_fig3_dwell_time.pdf` (**Fig. 6**, phase portrait and switching frequency with/without dwell time), and `sensitivity_3d_surfaces_full.pdf` (**Fig. 11**, joint 3D sensitivity over $(\alpha, \beta_I)$).
   - **Component Ablation & Stronger Baselines (Section IV-F, Table III, Fig. 9)**: Evaluated 8 variants across 30 independent random seeds (reporting mean $\pm$ SD and 95% CIs), including *Memoryless Reactive BC ($\alpha=1$)*, *SRA w/o Dwell ($T_d=1$)*, *Static BC*, *LIRP-D*, and *Online IGP Weight Tuning (Fortz–Thorup)*, demonstrating that SRA achieves top-tier throughput ($89.76$ pkts/step, $99.65\%$ PDR) while cutting route switching frequency by **$79.7\%$** ($20.0\%$ vs. $98.3\%$).
   - **Skewed Pareto Gravity Traffic, Heterogeneous Capacities, Time-Varying Traffic Surge, and Sensing Noise Injection (Section IV-G, Fig. 10)**: Validated generalized weighted SRA under Pareto gravity demands ($\text{CV} > 2.5$), heterogeneous degree-correlated $\mu_i$, a $2.2\times$ non-stationary traffic surge at $t \in [100, 180]$, and multiplicative telemetry noise $\sigma \in [0\%, 30\%]$.
   - **Dwell-Time Sensitivity, Scalability ($N=50..500$), Runtime Benchmarks, and Real-World Backbones (Section IV-H, Table IV, Fig. 12)**: Benchmarked `NSFNET` ($N=14$, $0.33$ ms/step), `GEANT` ($N=22$, $0.85$ ms/step), and scale-free graphs up to $N=500$ ($850.99$ ms/step, where SRA improves throughput by **$+107.42\%$** over Dijkstra).

5. **Dedicated Limitations Subsection & Open-Source Reproducibility (Section V-B, Section V-C)**:
   - Added **Section V-B** consolidating model assumptions, failure cases (e.g., homogeneous regular lattices and ultra-sparse single-bridge trees), and telemetry limitations.
   - Released all source code, LaTeX manuscripts, and multi-seed simulation pipelines in an open-source repository (`https://github.com/unicorners-compin/SRA-Resilient-Network-Governance`).

---

## Response to Associate Editor (Editor: 2)

> **Editor Comment 1**: *"First, the technical novelty should be more clearly established. The authors should explicitly distinguish SRA from existing adaptive routing and load-balancing approaches, particularly those based on dynamic link weights and centrality optimization. A clearer problem formulation and a systematic comparison with closely related methods would help strengthen the contribution."*

**Author Response**:  
We thank the Associate Editor for this crucial guidance. We have made four targeted enhancements to establish the novelty of SRA:
1. **Explicit Research Gap & Taxonomy (Section I & Table I)**: In Section I and the expanded **Table I**, we systematically contrast SRA against four representative families: (i) *Reactive Queue-Aware Routing* (backpressure/OBR), (ii) *Traffic-Matrix-Driven IGP Link-Weight Optimization* (Fortz & Thorup [26]), (iii) *Open-Loop Static Centrality Routing* [19], and (iv) *Data-Driven AI/DRL Routing* [21, 22]. Unlike reactive queue routing (which reacts only after buffer buildup and suffers from phase lag) or Fortz–Thorup IGP tuning (which requires full origin-destination traffic matrices and triggers $98.3\%$ route flapping when run online), SRA introduces a **closed-loop leaky-integrator structural state** $S_i^{(k)}$ coupled with **dwell-time hysteresis** $T_d$.
2. **Expanded Related Work (Section II-B)**: We added an explicit discussion comparing SRA's node-centric structural potential and $O(NM)$ Brandes update against Fortz–Thorup local search over link weights and static centrality routing.
3. **Formal Problem Formulation (Section III-B, Eq. (5))**: We added a rigorous mathematical optimization formulation in **Eq. (5)** defining the bi-criteria control objective over control epochs (minimizing peak structural stress and route-flapping penalty subject to leaky-integrator state dynamics and dwell-time constraints).
4. **Empirical Comparison Against Closely Related Methods (Section IV-F, Table III, Fig. 9)**: We implemented both *Online IGP Weight Tuning (Fortz–Thorup)* and *Static Centrality Routing* alongside *LIRP-D* and *Dijkstra* across 30 seeds. As reported in **Table III**, while online IGP weight tuning achieves high throughput ($90.08$ pkts/step), it recalculates routing tables at $98.33\%$ of steps; Full SRA achieves statistically indistinguishable throughput ($89.76$ pkts/step, $99.65\%$ PDR) while reducing route recalculations by **$79.7\%$** ($20.00\%$ switching rate).

---

> **Editor Comment 2**: *"Second, the theoretical analysis requires further clarification and justification. In particular, the convergence claims in Theorems 1 and 2 should be carefully examined, especially the distinction between attraction to a limit set and convergence to a unique equilibrium. The relationship between structural stress reduction and network capacity improvement, including Lemma 2 and Proposition 3, also requires stronger mathematical support."*

**Author Response**:  
We completely agree and have thoroughly rewritten the theoretical statements and proofs in **Section III-C/D** and **Appendices A, C, D, I, and J**:
1. **Theorem 1 & Remark 2 (Attraction to Limit Set $\Omega$ vs. Unique Point Equilibrium, Section III-C & Appendix C)**: Because shortest-path routing $\mathcal{R}(G, C)$ is piecewise constant and exhibits multi-path ties at switching boundaries, its convexification $\mathcal{F}(S)$ is an upper-semicontinuous set-valued mapping (Aubin & Cellina [28]) rather than a contractive single-valued map. We rigorously define the global attracting invariant set via the nested compact intersection $\Omega = \bigcap_{n \ge 0} F^n(X) \subset [0, 1]^N$ and added **Remark 2** explicitly explaining that trajectories converge to $\Omega$ (which may contain small-amplitude tie-breaking limit cycles near switching boundaries) rather than a single static fixed point, and that dwell-time hysteresis $T_d$ upper-bounds the switching frequency to at most $1/T_d$.
2. **Theorem 2 & Appendix D (Discrete-Time Dissipation-Injection Bound)**: We aligned the proof in **Appendix D** directly with the implemented normalized feedback $q^{(k)} = \mathrm{norm}(\kappa^{(k)}) \in [0,1]^N$ and tracking energy $E_k = \|S^{(k)} - q^{(k)}\|_2^2$, deriving an exact one-step discrete difference inequality $E_{k+1} \le (1-\alpha)^2 E_k + 2(1-\alpha)\|S^{(k)}-q^{(k)}\|_2 \|\Delta q^{(k)}\|_2 + \|\Delta q^{(k)}\|_2^2$ without relying on heuristic continuous-time approximations.
3. **Lemma 2 & Appendix I (Non-Circular Stress Reduction Proof)**: We replaced the circular conservation argument with an explicit **Route-Redistribution Budget $B_j^{(m)}$** and **Non-Overloading Diversion Condition** in **Appendix I**, proving strictly when penalizing the bottleneck set $\mathcal{B}$ lowers the global peak stress ($\kappa'_{\max} < \kappa_{\max}$).
4. **Proposition 3 & Appendix J (Fixed Capacity Inequality & Heterogeneous Node Analysis)**: We corrected the reversed minimum inequality in the original Appendix J and proved three exact statements in **Proposition 3**: (i) an unconditional increase in the guaranteed worst-case safe generation rate lower bound $L(\kappa') > L(\kappa)$, (ii) exact proportionality $\rho_{\max}(\kappa')/\rho_{\max}(\kappa) = \kappa_{\max}/\kappa'_{\max}$ when node service rates are homogeneous ($\mu_i \equiv \mu$) or when routing uses the capacity-normalized stress $\widetilde{\kappa}_i$, and (iii) the exact joint (`AND`) sufficient condition under heterogeneous $\mu_i$ with unweighted centrality.

---

> **Editor Comment 3**: *"Third, the experimental evaluation should be substantially strengthened. The authors are encouraged to include comprehensive ablation studies, parameter sensitivity analysis, stronger baselines, and statistical validation across multiple trials. Additional experiments under heterogeneous and time-varying traffic conditions would help demonstrate the robustness and generalizability of SRA. Computational complexity and runtime overhead should also be evaluated."*

**Author Response**:  
We have executed a comprehensive 3,380-run simulation campaign across 30 random seeds and added three new experimental subsections (**Sections IV-F, IV-G, and IV-H**), two new summary tables (**Tables III and IV**), and six multi-panel figures (**Figs. 5, 6, 9, 10, 11, and 12**):
- **Comprehensive Ablation & Stronger Baselines (Section IV-F, Table III, Fig. 9)**: Isolates each module of SRA (*Memoryless Reactive BC $\alpha=1$*, *SRA w/o Dwell $T_d=1$*, *Linear Penalty $\gamma=1$*, *Full SRA*) and compares against *Dijkstra*, *Static BC*, *LIRP-D*, and *Online IGP Weight Tuning (Fortz–Thorup)* with 30-seed means, standard deviations, and 95% confidence intervals.
- **Heterogeneous Capacities, Skewed Pareto Gravity Demand, Time-Varying Surge, and Sensing Noise (Section IV-G, Fig. 10)**: Evaluates skewed Pareto gravity traffic matrices $W_{st}$, degree-correlated heterogeneous capacities $\mu_i$, a $2.2\times$ mid-run traffic surge, and multiplicative telemetry noise $\sigma \in [0\%, 30\%]$.
- **Parameter Sensitivity, Computational Complexity, Runtime Overhead, and Real-World Backbones (Section IV-H, Table IV, Figs. 11–12)**: Reports joint 3D sensitivity over $(\alpha, \beta_I)$ (**Fig. 11**), dwell-time sensitivity $T_d \in \{1..10\}$ (**Fig. 12(a)**), wall-clock runtime per iteration across $N \in \{50, 100, 200, 300, 500\}$ (**Fig. 12(b)**), throughput scaling up to $N=500$ (**Fig. 12(c)**), and benchmarks on real-world `NSFNET` and `GEANT` topologies (**Table IV**).

---

> **Editor Comment 4**: *"Finally, the authors should clarify the underlying assumptions, discuss the limitations of using betweenness centrality as a stress indicator, and improve the overall presentation and reproducibility."*

**Author Response**:  
- **Underlying Assumptions**: Explicitly stated as **Assumptions 1–4** in **Section III-B**.
- **Limitations of Unweighted Betweenness Centrality & Generalized Stress**: Discussed in **Section III-B (Eq. (2))**, validated empirically in **Section IV-G (Fig. 10)**, and consolidated in a dedicated subsection **Section V-B (*Explicit Assumptions, Failure Cases, and Limitations*)**.
- **Presentation & Reproducibility**: Restored all missing figures, fixed all formatting/citation artifacts, streamlined repetitive text in Section V, and published the complete code and data repository (`https://github.com/unicorners-compin/SRA-Resilient-Network-Governance`) as documented in **Section V-C**.

---

## Response to Reviewer 1

We thank Reviewer 1 for the comprehensive 34-point checklist, which provided an exceptional blueprint for elevating both the theoretical and empirical quality of our manuscript. Below we respond to each bullet point individually.

> **R1.1**: *"Strengthen the problem formulation section: The manuscript introduces the task at a high level but does not formally define the problem in mathematical or system terms; a precise formulation with variables, constraints, and assumptions would improve clarity and rigor."*

**Response**: In **Section III-B**, we introduced formal system assumptions (**Assumptions 1–4**), defined the generalized demand- and capacity-weighted stress $\widetilde{\kappa}_i(S; W, \mu)$ (**Eq. (2)**), and formulated the closed-loop routing governance task as a constrained discrete-time bi-criteria optimization problem (**Eq. (5)**) with explicit decision variables, state evolution constraints, and dwell-time hysteresis constraints.

> **R1.2**: *"Provide a clearly articulated research gap statement: The introduction lists related approaches but does not explicitly isolate what remains unresolved."*

**Response**: We added a dedicated **Research Gap** paragraph in **Section I** (and expanded **Section II-B**) explicitly isolating the unresolved tension in prior work: reactive queue-based schemes suffer from feedback delay because queues only grow *after* bottleneck saturation; traffic-matrix IGP optimization requires full OD matrices and causes route flapping when executed online; and static centrality routing ignores dynamic load shifts.

> **R1.3**: *"Add a comparative summary table against closest prior methods: Without a feature-by-feature comparison, it is difficult to evaluate novelty; a structured table would clarify whether the contribution is architectural, algorithmic, or merely parametric."*

**Response**: We expanded **Table I** in **Section I** into a structured 6-column taxonomy comparing *Reactive Queue-Aware (Backpressure/OBR)*, *IGP Weight Tuning (Fortz–Thorup)*, *Static Centrality Routing*, *AI/DRL Routing*, and *Proposed SRA* across Control Signal, Feedback Loop, Adaptation Mode, Damping/Hysteresis, Time Complexity, and Key Limitation.

> **R1.4**: *"Expand theoretical justification of the core algorithm: Several steps are presented operationally; deeper derivation or analytical reasoning would reduce the perception of heuristic design."*

**Response**: We expanded **Section III-C**, **Section III-D**, and **Appendices A, C, D, I, and J** to provide rigorous analytical foundations for each component of SRA: (i) leaky-integrator state boundedness (**Lemma 1**), (ii) compact invariant set attraction via upper-semicontinuous differential inclusions (**Theorem 1 & Remark 2**), (iii) discrete-time Lyapunov tracking energy dissipation (**Theorem 2**), (iv) non-circular route-redistribution budget for peak stress reduction (**Lemma 2**), and (v) guaranteed capacity lower-bound improvement (**Proposition 3**).

> **R1.5**: *"Include a full ablation study isolating each module: The manuscript does not clearly quantify the independent contribution of each component, making performance gains difficult to attribute scientifically."*

**Response**: We added **Section IV-F**, **Table III**, and **Fig. 9**, which isolate each algorithmic module: (1) *Memoryless Reactive BC ($\alpha=1, T_d=1$)* (removing the leaky integrator), (2) *SRA w/o Dwell ($T_d=1$)* (removing dwell-time hysteresis), (3) *SRA Linear Penalty ($\gamma=1$)* (testing linear vs. quadratic penalty), and (4) *Full SRA ($\alpha=0.2, \beta_I=10, T_d=5$)*. The results show that removing the leaky integrator causes severe route chattering and drops PDR from $99.65\%$ to $59.26\%$, while removing dwell time increases route recalculation frequency nearly fivefold ($98.33\%$ vs. $20.00\%$).

> **R1.6**: *"Introduce statistical validation across multiple trials: Reported results appear based on limited runs; adding mean, variance, and confidence intervals would improve credibility."*

**Response**: All new experiments in **Sections IV-F, IV-G, and IV-H** (**Tables III–IV** and **Figs. 9, 10, 12**) are executed across **30 independent random seeds**, reporting sample means, standard deviations ($\pm\text{SD}$), and **95% confidence intervals (95% CI)**.

> **R1.7**: *"Diversify experimental scenarios: Validation under only one configuration restricts generalizability; additional test cases would strengthen robustness claims."*

**Response**: Beyond synthetic Barabási–Albert ($N=100$) and Erdős–Rényi ($N=100$) graphs, we added evaluations under: (i) skewed Pareto gravity traffic matrices $W_{st}$ (**Section IV-G**), (ii) heterogeneous node service capacities $\mu_i$ (**Section IV-G**), (iii) non-stationary time-varying traffic surges (**Fig. 10(b)**), (iv) scale-free topologies scaling from $N=50$ to $N=500$ (**Table IV, Fig. 12(b)–(c)**), and (v) real-world backbone topologies **NSFNET** ($N=14, M=21$) and **GEANT** ($N=22, M=36$) (**Table IV**).

> **R1.8**: *"Add controlled noise injection experiments: Performance sensitivity to signal degradation is not explored; this omission weakens claims of practical reliability."*

**Response**: In **Section IV-G** and **Fig. 10(c)**, we added a controlled telemetry noise injection experiment where each node's observed stress is corrupted by multiplicative Gaussian noise $\hat{\kappa}_i^{(k)} = \max(0, \kappa_i^{(k)}(1 + \mathcal{N}(0, \sigma^2)))$ across $\sigma \in \{0\%, 5\%, 10\%, 20\%, 30\%\}$. Because SRA's leaky integrator ($\alpha=0.2$) acts as a first-order low-pass filter, throughput remains virtually invariant ($69.34 \to 69.51$ pkts/step even at $\sigma=30\%$).

> **R1.9**: *"Clarify dataset representativeness: The manuscript does not justify whether the dataset reflects real-world variability, which limits external validity."*

**Response**: In **Section IV-A** and **Section IV-H (Table IV)**, we justified the choice of BA scale-free and ER random topologies and supplemented them with two canonical real-world packet-switched research backbones (**NSFNET** and **GEANT**) as well as heavy-tailed Pareto gravity traffic matrices reflecting empirical Internet traffic skewness.

> **R1.10**: *"Provide computational complexity analysis: Without time and memory cost reporting, scalability claims remain unsubstantiated."*

**Response**: In **Section III-B (Algorithm 1)** and **Section IV-H**, we explicitly analyzed both time complexity—$O(N + M)$ for state/cost updates and $O(NM + N^2 \log N)$ per Brandes/APSP recalculation, which is amortized by $1/T_d$ to $O((NM + N^2 \log N)/T_d)$ per step—and memory complexity $O(N + M)$ for storing node states and edge weights.

> **R1.11**: *"Report runtime benchmarks on specified hardware: Implementation feasibility depends on execution time; including this would ground the method in practical constraints."*

**Response**: In **Section IV-H**, **Table IV**, and **Fig. 12(b)**, we benchmarked single-thread wall-clock execution time per control epoch on an **Intel Xeon Gold 6248R (3.00 GHz) server (`node09`)**. A full SRA epoch requires $0.33$ ms on NSFNET ($N=14$), $0.85$ ms on GEANT ($N=22$), $7.52$ ms at $N=50$, $31.17$ ms at $N=100$, $132.00$ ms at $N=200$, $302.35$ ms at $N=300$, and $850.99$ ms at $N=500$.

> **R1.12**: *"Improve parameter selection justification: Hyperparameters appear tuned empirically; a principled selection rationale or sensitivity analysis is necessary."*

**Response**: In **Section III-C/D** and **Section IV-H**, we provide a principled selection rationale for $(\alpha, \beta_I, T_d)$: $\alpha \in [0.1, 0.3]$ sets the low-pass filter time constant $\tau_{\text{relax}} \approx 1/\alpha \in [3, 10]$ epochs to smooth burst noise without sluggish tracking; $\beta_I \in [5, 15]$ scales the penalty above typical shortest-path hop diameters; and $T_d = 5$ matches the relaxation time constant $\tau_{\text{relax}} = 1/\alpha = 5$.

> **R1.13**: *"Include hyperparameter sensitivity plots: Demonstrating stability across parameter ranges would reduce the impression of overfitting."*

**Response**: We restored the full 3D joint sensitivity surfaces over $\alpha \in [0.05, 0.8]$ and $\beta_I \in [1, 25]$ in **Fig. 11** (`sensitivity_3d_surfaces_full.pdf`) and added the dwell-time sensitivity curve across $T_d \in \{1, 2, 3, 5, 8, 10\}$ in **Fig. 12(a)** (`fig_revision_dwell_scalability.pdf`).

> **R1.14**: *"Clarify boundary conditions and assumptions: Several model assumptions are implicit; explicitly stating them would improve transparency."*

**Response**: We consolidated all implicit assumptions into **Assumptions 1–4** in **Section III-B**, explicitly stating graph biconnectivity/redundancy, quasi-stationary observation cadence, positive finite service capacities $\mu_i > 0$, and baseline FIFO queue discipline.

> **R1.15**: *"Expand discussion of failure cases: The manuscript presents positive results but omits situations where the method underperforms."*

**Response**: We added a dedicated discussion of failure cases and boundary regimes in **Section V-B**: (1) **Homogeneous Regular Topologies** (e.g., 2D torus or regular ring lattices where $\kappa_{\max} \approx \bar{\kappa}$ initially, yielding $<2\%$ capacity gain because no structural stress concentration exists to relax), and (2) **Ultra-Sparse Tree or Single-Bridge Topologies** (where cut-vertices have zero bypass paths, so penalizing them increases virtual path cost without diverting flow).

> **R1.16**: *"Include visual comparison under challenging scenarios: Comparative images in difficult conditions would provide a more balanced evaluation."*

**Response**: We added **Fig. 10** (`fig_revision_hetero_timevarying_noise.pdf`), which visually compares *Dijkstra*, *Topology-Only SRA*, and *Generalized Weighted SRA* under skewed Pareto gravity demand + heterogeneous capacities (**Fig. 10(a)**), a $2.2\times$ non-stationary traffic surge (**Fig. 10(b)**), and up to $30\%$ telemetry noise (**Fig. 10(c)**).

> **R1.17**: *"Improve figure readability and annotation quality: Some figures lack sufficient labeling clarity, reducing interpretability."*

**Response**: We regenerated the new multi-panel evaluation figures (**Figs. 9, 10, 12**) with high-contrast colorblind-safe palettes, explicit axis units, error bars (95% CI), shaded surge intervals, and clear panel legends, and restored the high-resolution vector PDFs for **Figs. 5, 6, and 11**.

> **R1.18**: *"Reorganize methodology for logical flow: Certain sections interleave explanation and results, which affects readability and technical coherence."*

**Response**: We reorganized **Section III** so that it progresses strictly from *Assumptions & Stress Metric (Section III-A/B)* $\to$ *State Evolution & Optimization Problem (Section III-B)* $\to$ *Algorithmic Procedure & Complexity (Algorithm 1)* $\to$ *Stability & Convergence Analysis (Section III-C)* $\to$ *Capacity & Stress-Bound Analysis (Section III-D)*, keeping all empirical findings strictly in **Section IV**.

> **R1.19**: *"Reduce repetitive narrative in discussion: Portions of the discussion reiterate earlier explanations without adding analytical depth."*

**Response**: We streamlined **Section V-A** to remove repetitive operational descriptions and focused **Section V** on control-theoretic synthesis, explicit limitations/failure cases (**Section V-B**), and quantified conclusions (**Section V-C**).

> **R1.20**: *"Condense conclusion to focus on quantified findings: The conclusion currently restates workflow rather than synthesizing insight."*

**Response**: We rewrote **Section V-C** to synthesize the core theoretical insights and report exact quantitative findings ($+30.3\%$ throughput gain on $N=100$ BA, $+107.4\%$ at $N=500$, $79.7\%$ reduction in route switching via $T_d=5$, $+20.3\%$ throughput gain under skewed Pareto demand, and sub-millisecond runtime on NSFNET/GEANT).

> **R1.21**: *"Provide clearer algorithm pseudocode: A formal stepwise algorithm block would enhance reproducibility."*

**Response**: We refined **Algorithm 1** in **Section III-B** to explicitly show the initialization, per-epoch dwell-time counter $\tau_{\text{dwell}}$, conditional stress recomputation (classical or generalized weighted $\widetilde{\kappa}_i$), min-max normalization, leaky-integrator update, virtual link-cost modulation, and $O((NM + N^2\log N)/T_d)$ amortized complexity.

> **R1.22**: *"Explicitly state limitations in a dedicated subsection: Limitations are scattered and understated; consolidating them would improve scientific honesty."*

**Response**: We created a dedicated subsection **Section V-B (*Explicit Assumptions, Failure Cases, and Limitations*)** covering topological redundancy requirements, unweighted vs. demand-weighted centrality trade-offs, and centralized vs. distributed LSA dissemination overhead.

> **R1.23**: *"Compare against stronger baselines: Current comparisons appear limited; benchmarking against more advanced alternatives would increase rigor."*

**Response**: In **Section IV-F (Table III, Fig. 9)**, we added **Online IGP Weight Tuning (Fortz–Thorup local search)** and **Static Betweenness Centrality Routing** alongside **LIRP-D** and **Dijkstra**.

> **R1.24**: *"Explain metric selection rationale: The manuscript does not justify why certain performance metrics are sufficient to evaluate the system."*

**Response**: In **Section IV-A** and **Section IV-F**, we justified how our metric suite jointly captures *capacity* (Throughput, Packet Delivery Ratio), *tail service quality* (Mean and P95 Latency), *structural balance* (Peak Betweenness Reduction, Jain's Fairness Index), and *control-plane stability* (Route Switching Rate and Runtime per Epoch).

> **R1.25**: *"Include additional evaluation metrics: Relying on a small set of metrics may overlook other performance dimensions."*

**Response**: In **Tables III–IV** and **Figs. 9–12**, we added **P95 Tail Latency**, **Packet Delivery Ratio (PDR)**, **Route Switching Frequency (%)**, **Maximum Generalized Stress $\max_i \widetilde{\kappa}_i$**, and **Wall-Clock Runtime per Iteration (ms)**.

> **R1.26**: *"Discuss scalability to larger or more complex inputs: Practical deployment requires understanding behavior under increased scale."*

**Response**: In **Section IV-H (Table IV, Fig. 12(b)–(c))**, we evaluated SRA across $N \in \{50, 100, 200, 300, 500\}$ nodes, showing that the relative throughput gain of SRA over Dijkstra grows monotonically with scale from $+8.31\%$ ($N=50$) to **$+107.42\%$ ($N=500$)**, and discussed incremental APSP and landmark approximation for $N > 10^3$.

> **R1.27**: *"Clarify training and evaluation protocol details: Missing implementation specifics hinder replication."*

**Response**: Because SRA is a model-driven closed-loop controller (requiring zero offline training), we detailed all simulation protocol parameters, warm-up horizons, traffic generation distributions, queue disciplines, and hardware specifications in **Section IV-A**, **Table II**, and **Sections IV-F–H**.

> **R1.28**: *"Improve mathematical notation consistency: Certain symbols appear overloaded or inconsistently indexed across sections."*

**Response**: We audited all mathematical symbols across the main text and Appendices A–J: $k$ denotes discrete control epochs, $S_i^{(k)} \in [0,1]$ denotes the normalized node stress state, $q_i^{(k)} = \mathrm{norm}(\kappa_i^{(k)})$ denotes normalized instantaneous stress, $\mu_i$ denotes node service capacity, and $T_d$ denotes the integer dwell-time threshold.

> **R1.29**: *"Strengthen connection between theory and experiments: Theoretical claims are not directly validated in experimental analysis."*

**Response**: Each theoretical result is now explicitly paired with direct empirical validation:
- **Theorem 1 & Remark 2** (Attraction to $\Omega$ & dwell-time stabilization) $\leftrightarrow$ **Fig. 6** (`ren_fig3_dwell_time.pdf`) and **Fig. 12(a)** ($1/T_d$ switching rate decay).
- **Theorem 2** (Discrete-time tracking energy dissipation) $\leftrightarrow$ **Fig. 5** (`ren_fig2_lyapunov.pdf`).
- **Lemma 2 & Proposition 3** (Bottleneck stress reduction & capacity lower-bound improvement, including generalized weighted stress $\widetilde{\kappa}_i$) $\leftrightarrow$ **Table III**, **Fig. 9**, and **Fig. 10**.

> **R1.30**: *"Provide ablation on preprocessing or auxiliary steps: Unclear whether performance depends on secondary pipeline stages."*

**Response**: In **Section IV-F (Table III)**, we evaluated the impact of min-max normalization and the penalty exponent $\gamma=1$ (linear) vs. $\gamma=2$ (quadratic), showing that both achieve $>99.6\%$ PDR while the leaky integrator ($\alpha$) and dwell time ($T_d$) are the primary drivers of stability.

> **R1.31**: *"Address potential data leakage or evaluation bias: Experimental separation between tuning and testing should be explicitly confirmed."*

**Response**: We explicitly confirmed in **Section IV-A** and **Section IV-H** that a single fixed hyperparameter tuple $(\alpha=0.2, \beta_I=10, T_d=5, \gamma=1)$ is used across all topologies (`BA`, `ER`, `NSFNET`, `GEANT`), network sizes ($N=14..500$), and traffic distributions (uniform, Pareto gravity, time-varying surge) without per-instance retuning, and evaluated on 30 independent test seeds.

> **R1.32**: *"Improve figure captions to be self-contained: Readers should understand key takeaways without referencing the main text."*

**Response**: We expanded the captions of **Figs. 5, 6, 7, 9, 10, 11, and 12** and **Tables I, II, III, and IV** so that each caption states the experimental configuration, sample size ($30$ seeds), error-bar definition (95% CI), and quantitative takeaway.

> **R1.33**: *"Update bibliography with recent relevant literature: Several foundational or recent works appear missing."*

**Response**: We expanded the bibliography to include foundational and recent works on IGP link-weight optimization (**Fortz & Thorup, IEEE J-SAC 2000 [26]**), fast betweenness centrality (**Brandes, J. Math. Sociol. 2001 [27]**), and set-valued differential inclusions (**Aubin & Cellina, Springer 1984 [28]**), alongside recent IEEE JSAC/TCOM/TNSE routing governance literature.

> **R1.34**: *"Provide code or implementation details for reproducibility: Clear availability statement would strengthen scientific transparency."*

**Response**: We added **Section V-C** providing the public GitHub repository URL (`https://github.com/unicorners-compin/SRA-Resilient-Network-Governance`) containing all simulation code, multi-seed experiment scripts, raw JSON outputs, and LaTeX source files.

---

## Response to Reviewer 2

We sincerely thank Reviewer 2 for the exceptionally detailed, constructive, and mathematically rigorous review. Your careful inspection of the proofs in Appendices A, C, D, I, and J and the missing figure references in Section IV was invaluable. Below we address each of your five major concerns in detail.

---

### Reviewer 2 — Comment 1: Novelty, Related Work Distinction, and Baselines

> **R2.1**: *"1. Novelty and Distinction from Existing Adaptive Routing / Centrality Routing: The manuscript states that existing adaptive routing methods are reactive and local, while SRA is proactive and topological. However, using node/link centrality (such as betweenness centrality) or dynamic link weights to balance load is a well-studied topic in traffic engineering (e.g., IGP weight optimization by Fortz & Thorup, centrality-aware routing in complex networks, and exponentially weighted moving average link costs). The authors need to more clearly articulate what is fundamentally new in SRA beyond applying an EWMA filter ($\alpha$) and a dwell-time threshold ($T_d$) to normalized betweenness centrality. Furthermore, in the experiments, SRA is only compared against static Dijkstra and a single heuristic baseline (LIRP-D). Comparing against a static centrality-weighted routing scheme or a standard congestion/weight-smoothing adaptive routing baseline is necessary to isolate where the gain comes from."*

**Author Response**:  
We thank Reviewer 2 for raising this central question. We have addressed both the conceptual distinction and the experimental isolation of gains:

1. **What is Fundamentally New in SRA (Section I, Table I, Section II-B, Section III-C)**:
   - Unlike **Static Centrality Routing** (which computes betweenness centrality once on the static graph and freezes link weights), static centrality penalty merely shifts traffic onto secondary hubs that subsequently become new permanent bottlenecks without closed-loop adaptation.
   - Unlike **Online IGP Weight Tuning (Fortz & Thorup [26])** or **Memoryless Reactive Centrality Routing ($\alpha=1$)**, directly feeding instantaneous topological or utilization metrics back into shortest-path routing creates a **discontinuous piecewise-constant closed-loop map** that suffers from severe route flapping (chattering across tie-breaking boundaries at $98.33\%$ of steps).
   - SRA's core contribution is the **joint dynamical coupling** of (i) a continuous leaky-integrator structural stress state $S_i^{(k)}$ that regularizes the discontinuous shortest-path operator into an upper-semicontinuous Filippov/Aubin–Cellina inclusion with a provably compact global attractor $\Omega$ (**Theorem 1**) and bounded tracking energy (**Theorem 2**), and (ii) a **dwell-time hysteresis gate $T_d$** matched to the relaxation time constant $\tau_{\text{relax}} = 1/\alpha$ that suppresses limit-cycle chattering on $\Omega$ while preserving closed-loop bottleneck evasion (**Lemma 2, Proposition 3**).

2. **Experimental Isolation Against Static Centrality, Memoryless Reactive BC, and Online IGP Weight Tuning (Section IV-F, Table III, Fig. 9)**:
   We implemented and evaluated all three requested baselines across 30 seeds on BA scale-free networks ($N=100, \rho=0.9$):
   - **Memoryless Reactive BC ($\alpha=1, T_d=1$)**: Without leaky-integrator smoothing, routing paths oscillate violently every step ($98.33\%$ switching rate), *amplifying* peak centrality by $31.04\%$ and degrading throughput to $53.39 \pm 5.88$ pkts/step (worse than static Dijkstra's $68.88$ pkts/step).
   - **Static Betweenness Centrality Routing**: Eliminates route switching ($1.67\%$) and improves throughput over Dijkstra ($89.96$ pkts/step under uniform load), but lacks closed-loop adaptability when traffic patterns shift or skew (**Fig. 10**).
   - **Online IGP Weight Tuning (Fortz–Thorup)**: Achieves high throughput ($90.08$ pkts/step) and peak stress reduction ($77.03\%$), but requires continuous route-table recomputation at **$98.33\%$ of control epochs**.
   - **SRA w/o Dwell ($T_d=1$) vs. Full SRA ($T_d=5$)**: Adding the leaky integrator ($\alpha=0.2$) stabilizes reactive BC ($53.39 \to 90.08$ pkts/step), and adding the dwell-time gate ($T_d=5$) cuts route recalculation frequency by **$79.7\%$** ($98.33\% \to 20.00\%$) while retaining $99.65\%$ PDR ($89.76$ pkts/step).

---

### Reviewer 2 — Comment 2: Mathematical Rigor in Proofs (Theorems 1 & 2, Lemma 2, Proposition 3, Appendices A, C, D, I, J)

> **R2.2**: *"2. Mathematical Rigor and Gaps in Theoretical Proofs: Several proofs in the appendices contain mathematical gaps or imprecise statements that need careful revision:
> - **Theorem 1 and Appendix C**: Theorem 1 claims convergence to a 'unique equilibrium state', while the proof in Appendix C uses upper-semicontinuous set-valued mappings $\mathcal{F}(S)$ and defines $\Omega = \bigcap_{k \ge 0} F^k(X)$ to claim global attraction to a compact invariant set $\Omega$. Attraction to a compact limit set (which may contain limit cycles or multiple equilibria due to shortest-path tie-breaking) is not the same as convergence to a unique point equilibrium. Moreover, in Appendix A (Proof of Lemma 1), the notations $\delta^+_{k,i}$ and $\delta^-_{k,i}$ appear without definition.
> - **Theorem 2 and Appendix D**: The Lyapunov function is defined as $V(S) = \frac{1}{2}\|S - \kappa(S)\|_2^2$, where $\kappa(S)$ is discontinuous at routing switching boundaries. Appendix D replaces $\kappa(S)$ with an exogenous sequence $q^{(k)}$ and writes a heuristic continuous-time analogy $\dot{V} \approx -\alpha\|S - q\|_2^2 + \langle S - q, \dot{q}\rangle$ to claim ISS. Notice also that in the algorithm, $S$ tracks the normalized betweenness $\mathrm{norm}(\kappa) \in [0, 1]^N$, whereas Eq. (8) writes $S - \kappa(S)$ without normalization. This inconsistency and the discrete-time step bound should be made mathematically rigorous.
> - **Lemma 2 (Appendix I) and Proposition 3 (Appendix J)**: In Appendix I, the proof assumes a conservation law $\sum_i \kappa'_i = \sum_i \kappa_i$ (which does not generally hold when path lengths change, since the sum of node betweenness equals the sum of shortest-path hop counts) and then states that $\max_{j \notin \mathcal{B}} \kappa'_j < \kappa_{\max}$ holds 'by choosing $\Delta S$ appropriately'—which begs the question of what condition guarantees that diverted traffic does not create a new, higher bottleneck. In Appendix J, the inequality $\min_i \frac{\mu_i}{\kappa_i} \le \frac{\min_i \mu_i}{\max_i \kappa_i}$ is reversed (since $\frac{\mu_i}{\kappa_i} \ge \frac{\mu_{\min}}{\kappa_{\max}}$ for all $i$), and the conclusion uses an 'OR' condition between homogeneous $\mu_i$ and bottleneck argmax alignment when an 'AND' (or capacity-normalized stress) is required to equate $\min_i(\mu_i/\kappa_i)$ with $\mu_{\min}/\kappa_{\max}$."*

**Author Response**:  
We are deeply grateful to Reviewer 2 for pinpointing each of these exact mathematical issues. Every single point raised above is spot-on, and we have completely rewritten the corresponding theorem statements and proofs in **Section III-C/D** and **Appendices A, C, D, I, and J**:

1. **Fixed Lemma 1 & Appendix A (Explicit Definition of $\delta^+_{k,i}, \delta^-_{k,i}$)**:
   In **Appendix A**, we explicitly defined the non-negative upper and lower variation sequences:
   $$\delta^+_{k,i} \triangleq \max\!\big\{0,\, S_i^{(k+1)} - S_i^{(k)}\big\}, \qquad \delta^-_{k,i} \triangleq \max\!\big\{0,\, S_i^{(k)} - S_i^{(k+1)}\big\},$$
   so that $S_i^{(k+1)} - S_i^{(k)} = \delta^+_{k,i} - \delta^-_{k,i}$, and proved by induction that $q_i^{(k)} = \mathrm{norm}(\kappa_i^{(k)}) \in [0,1]$ guarantees forward invariance of $X = [0,1]^N$.

2. **Fixed Theorem 1, Remark 2, & Appendix C (Attraction to Compact Invariant Limit Set $\Omega$ vs. Unique Point Equilibrium)**:
   - We revised **Theorem 1** in **Section III-C** to state accurately that the closed-loop system possesses a **non-empty, compact, positively invariant global attracting set** $\Omega \subset [0, 1]^N$ such that $\lim_{k \to \infty} \mathrm{dist}(S^{(k)}, \Omega) = 0$.
   - In **Appendix C**, we corrected the nested intersection notation to $\Omega \triangleq \bigcap_{n=0}^{\infty} F^n(X)$ (avoiding index overload with $k$) and cited Aubin & Cellina [28] for the compact-valued, upper-semicontinuous convex hull mapping $\mathcal{F}(S) = \mathrm{conv}\{\text{cluster points of } \widetilde{F}(S') \text{ as } S' \to S\}$.
   - We added **Remark 2 (*Attraction to Limit Set $\Omega$ vs. Point Equilibrium*)** explicitly explaining that because shortest-path routing is piecewise constant with finite switching hyperplanes, $\Omega$ may contain small-amplitude tie-breaking limit cycles rather than a single static point equilibrium, and showing how dwell-time hysteresis $T_d$ bounds the switching frequency to at most $1/T_d$.

3. **Fixed Theorem 2 & Appendix D (Normalized Feedback $q^{(k)} = \mathrm{norm}(\kappa^{(k)})$ and Exact Discrete-Time Step Bound)**:
   - In **Section III-C (Eq. (8))** and **Appendix D**, we unified the Lyapunov tracking energy with the implemented normalized stress vector $q^{(k)} \triangleq \mathrm{norm}(\kappa(S^{(k)})) \in [0,1]^N$:
     $$V_k \triangleq \frac{1}{2} E_k = \frac{1}{2}\big\|S^{(k)} - q^{(k)}\big\|_2^2.$$
   - We removed the heuristic continuous-time approximation $\dot{V}$ and proved the **exact discrete-time one-step difference identity**:
     $$S^{(k+1)} - q^{(k+1)} = (1 - \alpha)\big(S^{(k)} - q^{(k)}\big) - \Delta q^{(k)}, \qquad \Delta q^{(k)} \triangleq q^{(k+1)} - q^{(k)}.$$
   - Applying Cauchy–Schwarz and Young's inequality ($2(1-\alpha)ab \le \frac{\alpha(1-\alpha)}{2-\alpha}a^2 + \frac{(1-\alpha)(2-\alpha)}{\alpha}b^2$), we proved that for every step $k$:
     $$E_{k+1} \le \big(1 - \tfrac{\alpha}{2}\big) E_k + \frac{2 - \alpha}{\alpha}\big\|\Delta q^{(k)}\big\|_2^2,$$
     which directly yields by discrete Grönwall induction the exact Input-to-State Stability (ISS) ultimate bound:
     $$\limsup_{k \to \infty} \big\|S^{(k)} - q^{(k)}\big\|_2^2 \le \frac{2(2-\alpha)}{\alpha^2}\sup_{k \ge 0}\big\|\Delta q^{(k)}\big\|_2^2 \le \frac{2(2-\alpha)N}{\alpha^2}.$$

4. **Fixed Lemma 2 & Appendix I (Non-Circular Route-Redistribution Budget $B_j^{(m)}$)**:
   - In **Appendix I**, we removed the false assumption $\sum_i \kappa'_i = \sum_i \kappa_i$ (explicitly noting that $\sum_{i \in V} \kappa_i = \sum_{s \neq t} (\ell_{st} - 1)$ increases when detour paths have longer hop counts).
   - Instead, we defined the diverted pair set $\mathcal{D}(\Delta S)$, the maximum path multiplicity $K_{\max}$, and each non-bottleneck node's **route-redistribution budget**:
     $$B_j^{(m)} \triangleq \frac{\kappa_{\max} - \kappa_j}{2} > 0, \qquad \forall j \notin \mathcal{B}.$$
   - We proved that whenever the topology provides bypass routes satisfying the **Non-Overloading Diversion Condition** (at least one bottleneck pair is diverted off $\mathcal{B}$ and no alternative node $j \notin \mathcal{B}$ absorbs more than $B_j^{(m)}$ diverted shortest-path pairs), the new global peak stress strictly decreases:
     $$\kappa'_{\max} \le \max\!\Big\{\kappa_{\max} - \frac{2\delta_{\min}}{K_{\max}},\, \max_{j \notin \mathcal{B}}(\kappa_j + B_j^{(m)})\Big\} < \kappa_{\max}.$$

5. **Fixed Proposition 3 & Appendix J (Corrected Minimum Inequality and `AND` / Normalized Stress Condition)**:
   - In **Appendix J**, we corrected the fundamental lower bound inequality: since $\mu_i \ge \mu_{\min}$ and $\kappa_i \le \kappa_{\max}$ for all $i \in V$,
     $$\rho_{\max}(\kappa) = N(N-1)\min_{i \in V}\frac{\mu_i}{\kappa_i} \;\ge\; N(N-1)\frac{\mu_{\min}}{\kappa_{\max}} \triangleq L(\kappa).$$
   - We restructured **Proposition 3** into three mathematically exact statements:
     1. **Unconditional Improvement of the Guaranteed Safe Throughput Lower Bound**: Whenever $\kappa'_{\max} < \kappa_{\max}$, the worst-case safe generation lower bound strictly increases: $L(\kappa') / L(\kappa) = \kappa_{\max} / \kappa'_{\max} > 1$.
     2. **Exact Capacity Gain under Homogeneous Capacities or Capacity-Normalized Stress**: If either (a) node service rates are homogeneous ($\mu_i \equiv \mu$), OR (b) SRA operates with the generalized capacity-normalized stress $\widetilde{\kappa}_i = \kappa_i / \mu_i$ (**Eq. (2)**), then $\min_i(\mu_i/\kappa_i) = \mu/\kappa_{\max}$ (or $1/\widetilde{\kappa}_{\max}$) holds identically, yielding the exact equality:
        $$\frac{\rho_{\max}(\kappa')}{\rho_{\max}(\kappa)} = \frac{\kappa_{\max}}{\kappa'_{\max}} > 1 \quad \text{(or } \frac{\widetilde{\kappa}_{\max}}{\widetilde{\kappa}'_{\max}} > 1\text{)}.$$
     3. **Exact Joint (`AND`) Sufficient Condition under Heterogeneous $\mu_i$ with Unweighted Centrality**: When $\mu_i$ is heterogeneous and unweighted $\kappa_i$ is used, $\min_i(\mu_i/\kappa_i) = \mu_{\min}/\kappa_{\max}$ holds if and only if a node $i^*$ **simultaneously (`AND`)** minimizes $\mu_i$ and maximizes $\kappa_i$ ($i^* \in \arg\min_i \mu_i \cap \arg\max_i \kappa_i$).

---

### Reviewer 2 — Comment 3: Betweenness Centrality vs. Non-Uniform Traffic & Heterogeneous Node Capacities

> **R2.3**: *"3. Betweenness Centrality as a Proxy for Stress under Non-Uniform Traffic: Classical betweenness centrality $\kappa_i$ assumes uniform all-pairs traffic (every pair $(s, t)$ sends equal flow) and homogeneous node service capacities. In practical networks, traffic matrices are highly skewed (e.g., elephant/mice flows or gravity models) and node capacities vary. A node with high topological betweenness might carry very little actual traffic, or have massive processing capacity. How does SRA perform when traffic demands are non-uniform or time-varying, or when node capacities $\mu_i$ are heterogeneous? Discussing Demand-Weighted Betweenness or Capacity-Normalized Stress—and testing SRA under non-uniform/time-varying traffic—would make the framework much more convincing."*

**Author Response**:  
This is an outstanding insight. We have extended both our theoretical formulation and our experimental evaluation to incorporate **Generalized Demand- and Capacity-Weighted Stress**:

1. **Generalized Stress Formulation $\widetilde{\kappa}_i(S; W, \mu)$ (Section III-B, Eq. (2))**:
   In **Section III-B**, we introduced the generalized structural stress metric:
   $$\widetilde{\kappa}_i(S; W, \mu) = \frac{1}{\mu_i}\sum_{s \neq i \neq t} w_{st}\,\frac{\sigma_{st}(i; S)}{\sigma_{st}(S)},$$
   where $W = [w_{st}]$ is the non-uniform origin-destination demand weight matrix (or measured ingress demand estimate) and $\mu_i > 0$ is node $i$'s service capacity. When $w_{st} \equiv 1$ and $\mu_i \equiv \mu$, $\widetilde{\kappa}_i$ reduces to classical topological betweenness centrality $\kappa_i$.

2. **New Experiments under Skewed Pareto Gravity Demand, Heterogeneous Capacities, and Time-Varying Surges (Section IV-G, Fig. 10)**:
   In **Section IV-G** and **Fig. 10**, we tested three challenging regimes on BA networks ($N=100$, 30 seeds):
   - **Skewed Pareto Gravity Demand + Heterogeneous Capacities (Fig. 10(a))**: Node weights $m_i \sim \mathrm{Pareto}(1.5)$ generate a highly skewed gravity demand matrix $w_{st} \propto m_s m_t$ ($\text{CV} > 2.5$), while node service rates $\mu_i \in [1.4, 3.2]$ scale sublinearly with node degree ($\mu_i \propto d_i^{0.35}$). Under this skewed regime, static Dijkstra achieves only $57.65 \pm 8.97$ pkts/step ($67.79\%$ PDR, maximum generalized stress $2364.8$). *Topology-Only SRA* improves throughput to $68.91 \pm 12.04$ pkts/step ($81.03\%$ PDR, max generalized stress $975.7$), and *Generalized Weighted SRA* (using $\widetilde{\kappa}_i$) further boosts throughput to **$69.34 \pm 12.14$ pkts/step ($+20.3\%$ over Dijkstra, $81.54\%$ PDR)** while cutting P95 tail latency from $12.93$ to $9.83$ steps.
   - **Non-Stationary Time-Varying Traffic Surge (Fig. 10(b))**: Over a 300-step horizon, base load $\rho_0 = 0.70$ undergoes an abrupt **$2.2\times$ surge ($\rho_{\text{surge}} = 1.54$) during $t \in [100, 180]$** on the top-$15\%$ elephant OD pairs. While Dijkstra suffers severe buffer saturation and post-surge queue hangover, Generalized Weighted SRA rapidly diverts surge flows around saturated hubs and recovers baseline latency almost immediately after $t=180$.

---

### Reviewer 2 — Comment 4: Missing Figures, Dwell-Time Sensitivity, Ablation, and Scalability/Runtime

> **R2.4**: *"4. Experimental Completeness and Missing Visual Evidence:
> - In Section IV.B, the text discusses 'Visualizing the Lyapunov function trajectory...' and 'Visualizing the phase space trajectory...', and Section IV.E discusses 'Joint sensitivity analysis across the $(\alpha, \beta_I)$ parameter plane', but the corresponding figures (which were present in earlier drafts/supplementary files as `ren_fig2_lyapunov.pdf`, `ren_fig3_dwell_time.pdf`, and `sensitivity_3d_surfaces_full.pdf`) are omitted from `main.tex`. Restoring these figures is essential because the text refers to them indirectly.
> - No sensitivity analysis is provided for the dwell-time parameter $T_d$ (fixed at $T_d = 5$), nor is there an ablation showing SRA with vs. without dwell time or memory ($\alpha = 1$).
> - The computational overhead of recomputing all-pairs shortest paths / betweenness centrality ($O(NM + N^2 \log N)$ via Brandes' algorithm) at each control step is not evaluated. A runtime and scalability analysis (e.g., varying $N$ from 50 to 500 or testing on real-world backbone topologies such as NSFNET/GEANT) should be included."*

**Author Response**:  
We thank Reviewer 2 for catching the omitted figures and specifying these exact evaluations:
1. **Restored All Three Omitted Figures**:
   - `ren_fig2_lyapunov.pdf` is restored as **Fig. 5** in **Section IV-B**, directly visualizing the monotonic decay of the Lyapunov tracking energy $V_k$.
   - `ren_fig3_dwell_time.pdf` is restored as **Fig. 6** in **Section IV-B**, showing the phase-space attraction and route-switching suppression of the dwell-time mechanism.
   - `sensitivity_3d_surfaces_full.pdf` is restored as **Fig. 11** in **Section IV-H**, displaying the full 3D joint sensitivity surfaces over $(\alpha, \beta_I)$.
2. **Dwell-Time Sensitivity $T_d \in \{1, 2, 3, 5, 8, 10\}$ and Ablation of $T_d=1$ & $\alpha=1$**:
   - Added in **Table III**, **Fig. 9**, and **Fig. 12(a)** (**Sections IV-F & IV-H**). As shown in **Fig. 12(a)**, increasing $T_d$ from $1$ to $10$ reduces the route switching rate strictly along $1/T_d$ ($98.3\% \to 50.0\% \to 33.3\% \to 20.0\% \to 13.3\% \to 10.0\%$), while packet delivery ratio remains above $99.0\%$ for all $T_d \le 8$, confirming that $T_d=5$ is the optimal operating knee.
3. **Runtime Overhead and Scalability Analysis ($N=50..500$ + Real Backbones `NSFNET` & `GEANT`)**:
   - Added in **Section IV-H**, **Table IV**, and **Fig. 12(b)–(c)**. We measured single-thread wall-clock time per control epoch on `node09` (Intel Xeon Gold 6248R 3.00 GHz) and verified empirical $O(NM + N^2 \log N)$ scaling (**Fig. 12(b)**): $0.33$ ms (`NSFNET`, $N=14$), $0.85$ ms (`GEANT`, $N=22$), $7.52$ ms ($N=50$), $31.17$ ms ($N=100$), $132.00$ ms ($N=200$), $302.35$ ms ($N=300$), and $850.99$ ms ($N=500$). Moreover, with $T_d=5$, the amortized overhead per forwarding step at $N=500$ is only $850.99 / 5 \approx 170.2$ ms while delivering a **$+107.42\%$ throughput gain** over Dijkstra (**Table IV, Fig. 12(c)**).

---

### Reviewer 2 — Comment 5: Minor Formatting and Parameter Clarification Issues

> **R2.5**: *"5. Minor Presentation and Formatting Issues:
> - Figure 5 caption contains a leftover prompt/citation artifact: `[cite: 276, 277]`.
> - In Table II, clarify the relationship between 'Processing Capacity $C_{\max} = 50$ packets/step' and 'Service Rate $\mu = 2.0$ packets/step' so readers do not confuse buffer size with service rate."*

**Author Response**:  
1. **Removed Citation Artifact**: We removed the leftover `[cite: 276, 277]` artifact from the caption of the congestion transition figure (now **Fig. 7**).
2. **Clarified Table II Parameters**: In **Table II**, we explicitly distinguished the **Node Buffer Capacity $B_{\max} = 50$ packets** (maximum FIFO queue length before tail drop) from the **Node Service Rate $\mu = 2.0$ packets/step** (maximum packets processed and forwarded by a node per discrete time step, alongside per-step link transmission cap $C_{\text{link}} = 50$ packets/step).

---

We thank the Associate Editor-in-Chief, the Associate Editor, and the two Reviewers again for their constructive feedback and time spent reviewing our work.
