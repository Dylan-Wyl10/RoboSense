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

## 4x4 result (background run biuhn0mik, 2026-07-17)
2000/200/40ep, Gurobi labels: **200/200 valid, 137/200 = 68.5% match/beat Gurobi ref, mean gap
0.00032, max 0.00496, decode 3 ms/inst.** Larger grid ⇒ closer to Gurobi (68.5% vs 55.5% on 3x3) —
plausible (more near-optimal ties) but unconfirmed; revisit with 3 seeds. Comparison comment posted.

## 2026-07-27 — case-by-case comparison (user request)
train.py exports per-instance CSV (obj/cost/cov/gap, identical-routes flag, both parties' routes)
+ model checkpoint (commit 71973b8). 3x3 seed0 breakdown: 97/200 identical route sets,
14/200 alternative-optima ties (same obj, different routes), 89/200 worse (all gap lives here,
mean 0.00226), 0 beats (Gurobi optimal on these). Worst case = two vehicles duplicated a route
(coverage waste) — failure mode is "insufficient dispersion", not illegality. 3x3 CSV posted to
YIL-113. 4x4 per-case rerun relaunched (prev killed by session teardown); on completion post 4x4
digest + CSV as follow-up comment. Then: 3-seed REPORT, scaling sweep.

## 2026-07-28 — measured cost benchmark + 4x4 review delivered
RTX 3090: labels 20-43 ms (3x3) / 74-99 ms (4x4) per inst -> ~1.5 / ~3-4 min for 2200; training
0.4 s/epoch (14 s / 40 ep) BOTH grids; peak VRAM 99 / 131 MB (0.4-0.5% of 24 GB); end-to-end
~2-3 / ~4-6 min. Bottleneck = labeling, not NN (CPU-trainable at this scale). 4x4 cases: 133
identical / 4 alt-optima / 63 worse (mean 0.0010) / 0 beat; worst idx=122 = coverage-overbuy
(cov 260 vs 200, cost +10, net loss under current alpha) — DIFFERENT failure mode than 3x3's
duplicate-route; alpha-pricing behavioral note for later tuning. fig4/fig5 in results/, posted.
Remaining: 3-seed REPORT + scaling sweep (incl. 5x5).

## 2026-07-28 later — 5x5 (760-cell) validation scoped (user request); recon done, plan posted
Confirmed from result/middle_result0520/x_tmp.npy: real problem = (8 veh, 760 CTM cells, 150 steps).
CTMcell_index.json = newline list of 760 cell names (NOT json). Offline extraction feasible:
ctmcomponent.py has NO sumo/traci imports; Network (src/utili/network.py:191) builds from static
files (net.xml + linkdirction_5x5.csv + demand/turn); traci only in simulation.py. Plan (defaults
posted, non-blocking): P1 dump network_5x5.json via offline Network+CTM.init(); P2 time ONE
time-expanded-flow MILP instance at 760x150 (go/no-go number) + instance spec (8 veh, entry->exit,
synthetic per-cell congestion delta first, real CTM snapshots phase-2, signals baked into c[i,t]);
P3 parallel label farm (500-2200 by timing); P4 same eval + case review. Q1 answered: same-
distribution generalization verified; OOD / cross-scale = graceful-degradation expected, untested.

## Next step on resume
Start P1: neural_route/extract_5x5.py — instantiate Network(sizeX,sizeY,net_file,...) + CTM(...).init()
offline (see simulation.py:40 for ctor args; sumo_cfg/5x5net/ has all files), dump cells/adjacency/
free-flow times. Then P2 MILP timing probe. Branch exp/fm-mcvrp-local.

## 2026-07-28 late — signal mechanism decoded (user caution verified); sample-size method set
Signal chain (line-verified): cell.sig_flag multiplies merge/diverge flows (ctmcomponent 258-264,
345-346); runCTM calls node.getEdgeSignalPhase(t*5) each step (ctmcomponent:995) -> sets C6/C7
stopline cells 0/1 (network.py:136). traci provides ONLY (a) edge->phase-index map
(getControlledLinks; derivable offline via sumolib TLS connections) and (b) the cycle anchor
(getPhase/getNextSwitch). Future g/r is code-projected: (t_idx+range)%cycle<20, phase_split_time
=[20,3,2]x8 cycle=100s; net.xml has 50 STATIC tlLogic with explicit per-intersection offsets ->
OFFLINE replication is exact: sig_flag(e,t) = ((t+offset)%100)<20 on C6/C7 + net.xml phase map.
P1 must include a sigflag parity check vs archived CTMsigflag logs. Bonus: offsets = extra
instance-variability axis. Sample size: agreed 2200 insufficient; P2 = MILP timing (tight+relaxed
MIPGap) + 1k/2k/5k data-scaling slope -> extrapolate (prior guess 10-20k, levers: relaxed-gap
labels per FM-MCVRP, curriculum pretrain on small grids, 12-16-worker label farm).

## 2026-07-29 — OD-transfer / pct-gap / foundation-model questions (comment 557fa4fb)
Q1 answered: current model CANNOT transfer OD (25->26 hardcoded, not an input feature; decode
anchored to CON[START]) — by design, not method limit. Fix offered (pending user nod): OD as
instance input + randomized-OD training (veh_od already supports; UAS-MSTOP precedent). ~1 day.
Q2: prior gaps were ABSOLUTE (normalized units). Pct distributions computed + fig6 posted:
3x3 mean 0.26% max 2.60%; 4x4 mean 0.09% max 1.34%; median 0 both. "GBDT" interpreted as Gurobi
(flagged); offered real GBDT baseline as optional ablation if actually meant.
Q3: delegated to literature-reviewer as YIL-123 (1b9381dc) — per-paper: input tied to fixed graph
vs coordinate-based; dataset-switch mode (zero-shot/fine-tune/retrain + numbers); cross-graph
evidence; their "foundation model" criteria. Preliminary take posted: ours = single-network
single-OD amortized solver; FM-MCVRP-level ("per-city FM") reachable via OD-conditioning +
wider instance distribution; cross-network FM needs coordinate/feature cell encoding (arch step).
On reviewer return: synthesize comparison table + gap list for the user.
