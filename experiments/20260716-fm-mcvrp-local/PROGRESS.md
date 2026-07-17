# FM-MCVRP-style SL spike for RouteCartTSC (YIL-113, requested 2026-07-16)

**Scope: feasibility spike** (user: 粗略地, 2×2/3×3 小网络, 看能不能部署到现有 setting).
Method source: FM-MCVRP (arXiv:2403.00026) — fixed-graph + SL-on-solver-labels recipe;
decoder adapted to our selective/max-utility TOP shape (budget masks + subset selection).

## Verified facts (this session)
- Solve loop: `src/simulation.py` triggers `RouteOptimGurobi` every `optim_interval` s (user: 100 s)
  → build_model → solve_model → getRouteFromX. Networks: `sumo_cfg/toy_net` (3×3 per slide 8) + `5x5net`.
- **Historical per-solve (instance, solution) pairs are NOT persisted** — only coverage tables
  (`result/*/PR* Testing*/pr*_cover_*.npy`) + a few x/y/omg tmp .npy. → training data must be
  (re)generated offline by wrapping RouteOptimGurobi ourselves (which is also the FM-MCVRP way).
- **HGS: NOT found** in repo / ~/ / torchnn env (user said "HGS 的代码也在" — flagged in plan comment;
  waiting for pointer). Gurobi labels are the default; PyVRP(prize-collecting) optional 2nd label machine.
- Env `torchnn`: torch 2.5.1 + CUDA True + gurobipy 11.0.3. (Earlier "no torch" was my activation error:
  must `source ~/anaconda3/etc/profile.d/conda.sh` first.)
- `result/milpLog/` empty. Working tree has PRE-EXISTING uncommitted src/ mods — do not touch.

## Plan (posted to YIL-113 as plan comment, awaiting green light on open Qs)
- P0 read build_model/solve_model semantics (ask PartB agent only if genuinely ambiguous).
- P1 offline generator: wrap RouteOptimGurobi on toy_net, randomize (veh ODs, start times, demand seed),
  time-limited Gurobi solve → save (instance.json, routes) pairs into experiments/<id>/data/. Target ~5–20k.
- P2 tokenizer (segment/cell IDs over fixed toy graph = small vocab) + small enc-dec Transformer
  (~2-4 layers, d=128, few M params) + CE teacher forcing; feasibility mask (budget/adjacency) at decode.
- P3 eval: held-out utility-gap vs Gurobi labels + vs Gurobi matched-time; 3 seeds; inference latency.

## Open questions (in plan comment)
1. Where is the HGS code the user mentioned?
2. OK to default to Gurobi-as-label-machine for the spike?

## 2026-07-16 update — user simplified the setting (comment 4827d78c): NO SUMO
Pure 3x3 one-way graph (their figure): nodes 1-12 horizontal(E), 13-24 vertical(S), 25->{1,13},
{12,24}->26. == legacy `get_small_net_param()` con dict EXACTLY (also = slide-8 toy).
Cost: c(i,t)=(i+t)//4+1 (user's NEW formula; legacy was (i+t+1)%5+1). Assumed t = node ENTRY time,
occupation spans traversal (matches omega constraints) — stated to user, awaiting correction if wrong.
Objective (from legacy build_model_smallexample — P0 done): min a1*total_cost - a2*|union (i,t) cells|/(24*45);
y[i,t]=fleet coverage counted once. veh_od per-vehicle from/to/time → different start/end already supported.

## Status
- [x] Repo recon + env verification.
- [x] Branch `exp/fm-mcvrp-local` + this dir; plan comment posted.
- [x] P0: build_model_smallexample semantics extracted (objective/variables above).
- [x] **`neural_route/toy_env.py`** (new top-level module, commit 99933e4): DAG (20 routes, verified vs
      slide-8 + hand-checked costs), simulate(), MILP-equivalent fleet_objective(), solve_exact()
      brute force 20^V (V<=4 ⇒ PROVABLE optimum — stronger than Gurobi labels on the toy).
- [ ] Validate legacy MILP vs solve_exact on same instances (catches bugs both ways).
- [ ] data_gen.py: sample departures/V → exact labels → (instance, solution) pairs.
- [ ] model.py + train.py: joint-sequence tokens [v1 route SEP v2 route ...], ~0.2-0.5M param enc-dec.
- [ ] eval.py: gap vs exact, 3 seeds.

## 2026-07-17 update — user directives applied; FULL PIPELINE BUILT & RUN (commit 0f81a3b)
User: normalize cost inside the MILP ✓ (both terms now in [0,1]; cost_norm = V*max feasible route
cost — constant scaling, objective stays linear; diversity now emerges at a=0.5/0.5).
User: 4 vehicles, same departure t=0 ✓ (defaults N_VEH=4/DEPART=0; symmetry → multiset enum, 8855).
Degenerate-instance problem solved: per-instance node offsets delta in {0,1} ("daily congestion",
FM-MCVRP demand-subset analog; max_delta=1 else horizon kills feasibility — measured 0/33/129
zero-feasible out of 200 at max_delta=1/2/3). delta IS the model input (24 values).

Pipeline now in neural_route/: toy_env (env + exact solver), milp_baseline (normalized Gurobi MILP,
5/5 == brute force), data_gen (offline exact labels; token scheme BOS/links/SEP/EOS, vocab 28),
model (0.50M enc-dec, d=96, 2 enc + 3 dec, delta-conditioned encoder, masked greedy decode),
train (CE teacher forcing + eval vs exact).

**Result (2000 train / 200 test / 40 epochs, single seed):** 190/200 valid, 106/190 = 55.8% exact-
optimal, mean normalized-obj gap 0.00088 (max 0.0079; mean exact obj 0.3917). Training ~2 min GPU.

## 2026-07-17 later — user directive: GUROBI labels only (no brute force in pipeline) + bigger nets
Commit f37ec54. Refactor complete:
- toy_env → parametric `Grid(R,C)` (Grid(3,3) == legacy topology, verified). Horizon auto-calibrated
  (worst route at max delta × 1.15) → all routes always feasible; 3x3 horizon now 61 (was legacy 45).
- milp_baseline → **time-expanded arc-flow MILP** (polynomial, zero route enumeration; aggregated
  integer flow for identical vehicles + path decomposition). Validated 5/5 == brute force on 3x3.
  Enumeration survives ONLY as small-grid validator (solve_exact) — never in the label path.
- data_gen: Gurobi labels (20 ms/inst 3x3, 74 ms/inst 4x4). model: decode mask now = graph-legality
  + horizon/budget feasibility (_min_finish_time; NOTE: memo-less recursion, fine ≤ ~5x5, memoize later).
- **3x3 w/ Gurobi labels (2000/200/40ep): 200/200 valid, 55.5% match Gurobi, mean gap 0.00101,
  decode 2 ms/inst.** Budget mask fixed all previously-invalid decodes.
- 4x4 run (2000/200/40ep) launched in background (task biuhn0mik); results → next comment/REPORT.

## Next steps
1. Collect 4x4 result; post comparison comment (3x3 vs 4x4 = the "more options" request).
2. 3-seed protocol + REPORT.md draft (spike verdict).
3. Scaling sweep (params 0.1-2M × data 1k-50k × grid 3x3/4x4/5x5) for the scaling-law question.
4. Optional: nucleus-sampling multi-decode (FM-MCVRP NS-100) to push match% up.

## Next step on resume
Read this file. If 4x4 background task done: report results (comment + REPORT.md). Then 3-seed + sweep.
Env: `source ~/anaconda3/etc/profile.d/conda.sh && conda activate torchnn`. Branch exp/fm-mcvrp-local.
