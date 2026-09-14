# Literature-review source material — YIL-113 survey

Captured from the literature-reviewer's full-text deliveries so the material lives in the
repo, not only in issue comments. Numbers are verbatim from the reviewer (full-text arXiv PDFs).

- **Batch A (neural OP/TOP)** delivered on YIL-114 (c489b0aa), accepted 2026-07-14.
- **Batch B (VRP/CO foundation models)** delivered on YIL-115 (5584bfeb), accepted 2026-07-14.

Two intake corrections the reviewer flagged (both verified, both stand):
1. **RouteFinder venue = TMLR 09/2025**, not ICML 2025 (my intake error). arXiv:2406.15007 correct.
2. Batch-A **#5 (2601.11010) is NOT neural** — pure OR (rolling-horizon ALNS + scenario sampling);
   reclassified as an OR/anticipatory-dispatch baseline. And **#2 POMO does not solve OP/TOP**
   (only TSP/CVRP/KP); reusable as training/inference tricks, not a selective-routing method.

---

## Batch A — Neural OP/TOP (gap + methodology)

### A1. Kool AM — *Attention, Learn to Solve Routing Problems!* (ICLR 2019, arXiv:1803.08475)
- Founding neural method for the **Orienteering Problem (OP)**: max Σ node prizes s.t. tour length ≤ budget T;
  single vehicle, depot→depot, visiting optional.
- Gap: earlier learned routing (Pointer Nets + actor-critic) trained poorly; RNN encoders order-dependent.
- Method: Transformer enc–dec, **no positional encoding**; 3 enc layers, 8 heads, batch-norm.
  - Subset selection: **depot is a selectable action → choosing depot ends the route**; visited-so-far = chosen subset.
  - Budget feasibility = **MASKING** (not penalty/repair): mask node j when `d(prev,j)+d(j,depot) > remaining T`.
    Depot never masked ⇒ always a legal stop. **This masking rule is the transferable feasibility template.**
  - Train: **REINFORCE + greedy-rollout baseline** (no critic).
- Result: OP n=20 — AM sampling-1280 within **1.56%** of Gurobi; SOTA GA (Compass) only ~2% better; beats OR-Tools/Tsili.

### A2. POMO (NeurIPS 2020, arXiv:2010.16011) ⚠ does NOT solve OP/TOP
- Tests only **TSP / CVRP / 0-1 Knapsack**; "orienteering" appears once, in related work. Only selective problem = KP (no travel cost).
- Gap vs Kool AM: greedy-rollout baseline gives mostly-negative advantage; first action dominates.
- Method: same AM backbone, remove the "pick start node" step.
  - **Multiple optima**: N fixed start nodes → N parallel rollouts; **shared baseline b = mean of N returns** (no critic).
  - Inference: N multi-start greedy + **×8 instance augmentation**.
- Relevance: LOW as selective routing — **multi-start symmetry does not hold for max-prize subset selection**
  (different starts → genuinely different subsets/objectives). Reusable: AM+masking, shared-baseline REINFORCE, ×8 aug.
- Result: TSP100 gap **0.14%**; CVRP beats OR-Tools. (No OP/TOP numbers.)

### A3. TOP-Former (T-ITS 2025, arXiv:2311.18662) ★ closest
- **Team Orienteering Problem (TOP)**, multi-vehicle (m=2..5): max team reward; per-vehicle budget T; shared depot; visiting optional.
- Gap: prior multi-vehicle neural TOP solvers are **decentralized/sequential** — each agent ignores others' state → suboptimal.
- Method: **centralized** enc–dec (no GNN); shared encoder run once; 3 blocks, dim 128, batch-norm.
  - **Simultaneous** multi-agent decoding: each step picks one node per agent; a chosen node is masked (−∞) for still-to-act agents.
  - Per-agent budget via **return-to-depot masking** (Eq.18): mask nodes unreachable-and-return within remaining time t^a.
  - Train: **REINFORCE + greedy-rollout baseline** (Kool-style, not POMO).
- Result: n100,m5 constant — TOP-Former **82.79 (best, 0.00%)** > ACO 81.39 (1.69%) > GAMMA; Gurobi-60s only 61.9% gap.
  Inference ~**4 ms CPU / 0.22 ms GPU**.
- Transfer deltas: single shared depot, homogeneous budget T, **STATIC node reward**, O(n²) scaling.

### A4. UAS-MSTOP (2023, arXiv:2303.01963)
- **Multi-Start TOP**: TOP for **mid-mission re-planning** — K vehicles start from different current positions with different remaining fuel f_k.
- Gap: AM/POMO assume all vehicles start at depot (pre-planning); don't model heterogeneous starts + remaining energy.
- Method: **Deep Dynamic Transformer (DDTM)**, 4 enc / 2 dec; **re-runs encoder after each vehicle completes** (graph state changes).
  - Nested inner/outer loop: build one vehicle to return-depot, update instance, next vehicle from its own start.
  - Budget = **action masking** on "can't reach & return within remaining fuel".
  - **Data-efficient training**: instance-augmentation baseline (K=8 distance-preserving transforms) replaces greedy rollout
    → −30% epoch time; + max-entropy (α=0.01).
- Result: MSTOP ×8N! gap — n10 0.19%, n20 0.78%, n≥50 reference-best; >90% instances gap=0 at n20.
- Relevance: HIGH if our fleet must re-plan mid-shift from current position / remaining charge.

### A5. DTOP-SC (2026, arXiv:2601.11010) ⚠ NOT neural
- **Dynamic TOP in Spatial Crowdsourcing**: workers=vehicles, tasks=profit nodes, tasks arrive online (release times);
  heterogeneous per-worker OD + time windows; max total profit; selective; multi-worker.
- **Method class = pure OR / metaheuristic**: Scen-RH-ALNS (scenario-sampling rolling-horizon ALNS). Zero neural nets, no RL.
  - Event-driven rolling horizon; each epoch solves a static HT-TOPTW snapshot with ALNS (destroy/repair + 2-opt + SA accept).
  - **Scenario-sampling lookahead** (Bent–Van Hentenryck consensus): sample S futures + N_vir virtual tasks, solve augmented
    instances, vote on first real task per worker. S=15, N_vir=5, α=0.2.
- Result: vs MPA on 1161 DTOP instances (high dynamism) — profit within 0.79–3.23%, but decision time **0.14 s vs ~195 s** (2–3 orders faster).
- Relevance: structurally very close (selective, per-vehicle budget, multi-vehicle, +TW/OD) — use as a **strong non-learning /
  anticipatory-dispatch baseline**, not a neural method.

### Batch-A shared gap (our novelty)
All 5 are **node-based** (points in a unit square), reward **static**, budget/depot mostly homogeneous (only A4 heterogeneous
starts/fuel, A5 heterogeneous OD/TW). None does **road-segment/arc-level, time-varying sensing-utility, per-vehicle-budget selective
routing on a real fixed network** — that is our open contribution.

---

## Batch B — VRP/CO foundation models (features + unification mechanism)

### B1. RouteFinder — *Towards Foundation Models for VRPs* (TMLR 09/2025, arXiv:2406.15007)
- Berto et al. (KAIST / Bielefeld / RSM / VU / Omelet / AI4CO). Unifies **48 VRP variants**.
- **Unification = attribute composition**: every variant = a subset of one super-problem **MDOVRPMBLTW**
  (multi-depot + open + backhaul + distance-limit + time-windows); attributes toggled on/off.
- Features: unified VRP env; **global attribute embedding φ₀..φₖ into a DEEP encoder** (vs MTPOMO/MVMoE shallow decoder);
  modern encoder (RMSNorm, pre-norm, SwiGLU, FlashAttention = RF-TE, usually best); **Mixed-Batch Training**;
  multi-variant reward normalization; **Efficient Adapter Layers (EAL)** — zero-pad projection `W'=[W;0]` for unseen attributes.
- Train: **RL** (REINFORCE + POMO shared baseline); A100 9–24 h/model.
- Result: beats MTPOMO/MVMoE on all 48 variants; gap ~1–5% vs HGS-PyVRP/OR-Tools; inference 1–2 s vs 10–20 min.

### B2. FM-MCVRP — *Learning to Deliver* (MIT, 2024, arXiv:2403.00026) ★ most relevant to us
- Chin, Winkenbach, Srivastava. **LLM-style supervised learning on a FIXED city graph**: a **T5 enc-dec** learns
  "the next node to visit" from many (sub-optimal) historical solutions.
- Data setup (≈ our robotaxi fixed-road-network daily instances):
  - Fixed graph G′ = **10,001 nodes** (10k customers + depot); each instance = a random node **subset** (a day's demand).
    **ALL instances are subgraphs of the SAME fixed graph** — the essential difference from ordinary CVRP.
  - **38.1M training instances** (381 sizes × 100k), each labeled by **one HGS run @5 s** (deliberately cheap/sub-optimal — mimics real historical data).
  - T5, **206M params**, LM objective, **curriculum learning** (small→large); decode by **nucleus sampling** (top-p).
- Headline (**SL beats its training data**): vs its own HGS@5s labels, NS-1000 beats training solutions at **≥100 customers**
  (400 → **−1.05%**, statistically significant). Mechanism: under a tight budget HGS quality degrades with scale faster than the
  model, which aggregates knowledge across millions of instances.
- Result: single model spans sizes **20–800** & all capacities; beats AM (diverges at ≥400); within **3.02%** of LKH-3 at 400.

### B3. GOAL — *A Generalist CO Agent Learner* (ICLR 2025, arXiv:2406.15079)
- Drakulic, Michel, Andreoli (NAVER LABS). One **backbone + light per-task adapters** across routing/scheduling/packing/graph.
- **Unification = generalist backbone + adapter**: shared trunk learns commonality, light input/output adapters learn specifics.
- Features: **shared codebook**; **mixed-attention blocks** (inject edge info into every attention kernel);
  **multi-type transformer** (replicate blocks per node/edge type, share parameters).
- Train: **imitation learning** on expert trajectories; 8 CO tasks (ATSP/CVRP/CVRPTW/OP; JSSP/UMS; Knapsack; MVC).
  Fine-tune to new problems: supervised few-shot (minutes) or ExIt-style (hours); SL fine-tune > from-scratch.
- Result: single-task GOAL is SOTA on **7 of 8** tasks (except CVRP: 2.34% vs POMO 1.21% / RF-TE 1.50%); multi-task only slightly worse.

### B4. UniCO — *Unified CO via Problem Reduction to Matrix-Encoded General TSP* (ICLR 2025, OpenReview yEwakMNIex)
- Pan et al. (SJTU Thinklab). **Unification = problem reduction**: reduce every problem to one canonical form
  (**general TSP over any positive cost matrix**), solve with one TSP solver, transform the tour back.
- Features: reductions for **ATSP, 2D-TSP, HCP, 3SAT**; two solvers — **MatPOENet** (Graph Transformer + RL, MatNet + Pseudo
  One-hot Embedding + Mix-Score Attention) and **MatDIFFNet** (Graph Diffusion + SL, extends Euclidean-TSP diffusion to matrix TSP).
- Result: unified MatPOENet*-8x avg opt-gap **~1.4%** at N≈20, high find-rate, beats LKH(10k/500) on some tasks.
  Cross-task transfer (3SAT): 50→200 fine-tune steps reach **95.96→97.08%** find-rate (≈ from-scratch 96.08%) vs 17.92% no-tune.
- Source note: OpenReview returned only a JS shell this run; headline cross-checked vs the workspace's same-day pdf-sourced UniCO
  page + official GitHub (Thinklab-SJTU/UniCO). **DB has two duplicate UniCO pages (…971d… all-caps + …a6e6… normal) — flag for human merge.**

### Three unification philosophies (+ one orthogonal)
| Paper | Unification mechanism | Training | Scope |
|---|---|---|---|
| RouteFinder | Attribute composition (super-variant env + global attribute embedding + mixed batch) | RL | 48 VRP variants |
| FM-MCVRP | LLM-style SL on fixed-graph sub-instances | Supervised (learns sub-optimal labels, **beats** them) | single MCVRP, sizes 20–800 |
| GOAL | Generalist backbone + light adapter (mixed-attention / multi-type) | Imitation | 8 CO families + fine-tune new |
| UniCO | Problem reduction → matrix general-TSP | RL (MatPOENet) / SL (MatDIFFNet) | ATSP / 2D-TSP / HCP / 3SAT |

Axes: (1) attribute composition (RouteFinder); (2) generalist backbone + adapter (GOAL; RouteFinder EAL adjacent);
(3) problem reduction (UniCO). **FM-MCVRP is an orthogonal 4th axis** — single-problem × fixed graph × LLM-style SL ×
beats-training-data × cross-scale generalization → closest to our robotaxi fixed road network.
