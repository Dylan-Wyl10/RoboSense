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

## 2026-07-29 later — EXTENSION 1 greenlit & designed (comment 4b0e59c4): OD-conditioning
User wants: 8 gates on 4x4 (their count: 28 ODs), variable OD + variable fleet at inference; then
cross-network training later. Geometry verified: one-way E/S grid => ODs are ORDERED + reachability-
constrained; 28=C(8,2) needs bidirectional (deferred to cross-network phase, told user). Verified
placement: entries NW (N-edge cols 0,1 + W-edge rows 1,2), exits SE (S-edge cols 2,3 + E-edge rows
2,3) -> ALL 16 ordered ODs feasible. Design posted:
- Instance = {delta, [(o_k,d_k)] per veh, V in 2-8}.
- MILP -> multi-commodity (group by identical OD).
- Model: +V task tokens (emb(o)+emb(d)) in encoder; decoder segment-k masks use (o_k,d_k):
  start=CON[o_k], SEP at pred(d_k), budget mask = min-finish-to-d_k. Variable V via token count.
- Eval 3 layers: same-distribution; OD-ZERO-SHOT (hold 2-3 OD pairs out of training entirely);
  fleet-size extrapolation (train V{2,3,4,6}, test V{5,8}).
- Estimate 3 work sessions. 5x5 P1 extraction stays queued behind this (user prioritized OD ext).

## Next step on resume
Implement extension 1 in neural_route/: (1) gates in Grid (entry/exit node ids > n_links+...),
sample_instance with od_list+V; (2) milp_baseline multi-commodity; validate vs per-OD route
enumeration on 3-5 instances; (3) model task tokens + per-vehicle masks; (4) data/train/3-layer eval.
Branch exp/fm-mcvrp-local. Also pending: YIL-123 reviewer return (foundation-model synthesis).

## 2026-07-29 night — bidirectional network built + lit table spun out (comment d5aa7c57)
User approved OD design, then directed: bidirectional 4x4 + viz for confirmation; cross-network
PAUSED; multi-veh/multi-OD is the focus; separate issue for the lit transferability table.
Done (commit 536d406): neural_route/bigrid.py — BiGrid 80 directed links, no U-turn, 8 gates
(2/side) each entry+exit = 56 ordered / 28 unordered ODs, ALL verified reachable; time-dependent
Dijkstra (FIFO ✓) replaces enumeration (cyclic graph) for horizon calib (H=212) + future budget
mask. fig7 (network + 8x8 earliest-arrival heatmap) posted for confirmation.
DECISION PENDING (user): cost asymmetry (a) keep direction-dependent (N/W pricier, id artifact
of (i+t)//4 formula) vs (b) same base cost both directions. Default (a).
Lit table: YIL-124 (backlog, ref issue) — 9 rows x 5 cols from YIL-114/115/123 verified reads +
3 quotable conclusions (headline: NO paper demonstrates cross-network transfer; all
"not addressed"). PPT version offered on request.
YIL-123 returned + prior run already posted foundation-model synthesis (comment 6e56d60d) — loop closed.

## Next step on resume
After user confirms fig7 network (+ a/b cost choice): implement multi-commodity MILP on BiGrid
(group by same OD), timing probe, then task-token model + stratified OD training-set design
(difficulty layers via earliest-arrival matrix; min per-OD coverage; hold out 3-4 OD pairs for
zero-shot). Est: MILP+timing 1 session, model 1, data/train/eval 1.

## 2026-07-30 — gates moved to corners+midpoints (user spec); Dijkstra explained; work greenlit
Commit 18ed61f: gate_pos = 4 corners (G1 NW, G3 NE, G5 SE, G7 SW) + 4 edge midpoints (G2 N, G4 E,
G6 S, G8 W). 56 ODs reachable at delta 0/1. Horizon 212 -> 418 (diagonal ODs against pricey N/W
directions; shrinks if cost-symmetry option (b) chosen — STILL PENDING, default (a)). fig8 posted.
User note "网线对照表...先做起来" interpreted as green light for next-phase work (lit table itself
already delivered = YIL-124; interpretation flagged to user). Time-dependent Dijkstra explained
with hand-checked example (G1->G2=2 vs G2->G1=13 from the heatmap).

## Next step on resume
Build multi-commodity flow MILP on BiGrid (commodities = distinct ODs, counts; y coverage same),
single-instance timing probe, then stratified OD training-set design (difficulty layers from
earliest-arrival matrix, min per-OD coverage, hold out 3-4 OD pairs), task-token model, train+eval.
Watch for user override on cost symmetry (a->b) — would need horizon recalib + regen.

## 2026-07-30 later — presentation walkthrough posted (comment 56e3967c); PPT pending template
Posted the full present-grade pipeline narrative on YIL-113: 6 modules (M1 env / M2 Gurobi label
machine / M3 offline data gen / M4 model+mask / M5 training / M6 eval) each with ✅ vs 🔧 status
tags, the step-by-step single-inference walkthrough (encode once -> masked decode loop with
per-vehicle clocks -> routes, 2-4 ms), the honest evidence-vs-design boundary, and a proposed
8-10 slide outline. USER WILL SEND A PPT TEMPLATE — when it arrives, produce the deck per that
template (existing figs 1/2/4/6/8 cover several slides; build_slides.py machinery reusable).

## 2026-07-31 — staggered departures question (comment f8304fa6): honest answer + design update
User asked: veh 1-2 depart t=0, veh 3-4 depart t=2 — can current model handle? Answer posted:
CURRENT checkpoint cannot (departure time is NOT in its input — encoder eats only delta; all
training data t=0; rule parts (clock/mask/simulator) would use true t0 so output stays feasible,
but the policy is timing-blind -> suboptimal). Design fix folded into EXTENSION 1: instance is now
{delta, [(o, d, t0)] x V}; task token = Emb(o)+Emb(d)+Proj(t0); MILP per-commodity source at
(o, t0) (few lines); training randomizes t0 incl. mixed same/staggered patterns; extra eval layer
"unseen departure patterns". UAS-MSTOP = literature precedent (heterogeneous starts learnable).
Still gated on user's final network sign-off (fig8 + cost-symmetry a/b choice).

## 2026-08-02 — GREEN LIGHT (fig8 OK, cost option B); extension-1 env+MILP BUILT (commit c5018c5)
User signed off: fig8 layout + option (b) symmetric street costs; do full 4x4 extension + training
-> stable model -> tests -> complete pipeline review; PPT from their template (archived at
experiments/20260716-fm-mcvrp-local/ppt/template.pptx) via a SEPARATE agent.
Built this session:
- bigrid option (b): base=min(id,reverse); G1<->G2 now symmetric; horizon 418->338 (max_t0=5).
  Note: vertical streets (base 41-60) pricier than horizontal (1-20) — street-class feature, disclosed.
- Tasks = (o, d, t0) per vehicle; simulate/objective/min_finish (memoised budget query) on BiInstance.
- **Objective redesign (important, disclosed to user)**: with cov normalized by n_links*H the optimum
  collapsed to min-time routes (cov term ~20x smaller than cost). Fix: BOTH terms /(V*H), alpha
  0.3/0.7 -> MILP roams fresh cells (cost==cov, 5-13x min-time coverage), solve 1.4-10.1s (V=2-4),
  proven optimal. This is the label-richness guarantee.
- bigrid_milp: multi-commodity flow (commodity=(o,d,t0) group), decomposition==objective asserted,
  4/4 validation vs min-time upper bound.

## Next steps (in order)
1. bigrid data_gen: stratified OD sampling (terciles from earliest-arrival matrix), 4 held-out OD
   pairs, V in {2,3,4,6} train / {5,8} eval, t0 in {0..5}; MIPGap 1-2%; PARALLEL label farm
   (nohup, 12-16 workers, PID in PROGRESS per session discipline; ~5k first batch).
2. bigrid model: task tokens (Emb(o)+Emb(d)+Proj(t0)); variable-length routes (seq cap from labels);
   masks via inst.min_finish. Train 40ep; eval 3 layers (same-dist / OD-zero-shot / V-extrapolation).
3. Stable checkpoint + config + 3 seeds -> full pipeline REVIEW comment + REPORT.md.
4. Delegate PPT to a separate agent (template + content brief from the review).

## 2026-08-02 later — LABEL FARM RUNNING (user asked "are you actually executing?")
Honest state: between comment-triggered runs nothing was executing (event-driven runtime); fixed by
launching the farm detached THIS session per §6:
- **PID 3063842**, log: experiments/20260716-fm-mcvrp-local/data/farm.log,
  pid file: data/farm.pid. Script: data/run_farm.sh (sequential: 5000 train seed0 -> 500 test
  seed10000 -> 300 zeroshot seed20000 -> 300 vextrap seed30000; 12 workers, MIPGap 2%, 60s cap).
- Generator: neural_route/bigrid_datagen.py (commit pending above). Resumable: rerun the same
  command and it skips existing idx. Verified producing (8 labels in first ~70s; rate prints
  every 100 in farm.log). Expect several hours; check `wc -l data/*.jsonl` on resume.
## Next step on resume
1) Check farm: `ps -p $(cat .../data/farm.pid)`, `tail farm.log`, `wc -l data/*.jsonl`. If done:
   build bigrid model (task tokens Emb(o)+Emb(d)+Proj(t0); variable-len seqs; min_finish masks),
   train 40ep, 3-layer eval, 3 seeds -> stable checkpoint -> pipeline REVIEW -> delegate PPT
   (template at experiments/20260716-fm-mcvrp-local/ppt/template.pptx).
2) If farm died: restart same command (resumable), investigate tail of farm.log.

## 2026-08-02 latest — PLATFORM WATCHDOG ADDED (user request)
Autopilot "YIL-113 label-farm watchdog" id 7c6293c2-ac18-4d91-be2c-59ce5bb5dbd5, ACTIVE, run_only,
assignee = ML_Optimize_Research_Agent, schedule cron "37 */2 * * *" (every 2h, America/Indiana/
Indianapolis), trigger bd540480, first run 2026-08-02T20:37Z. Playbook in the autopilot description:
check pid/log/counts -> restart resumable farm if dead (+comment) -> on FARM COMPLETE post final
stats + PAUSE ITSELF -> silence when healthy. Farm status at setup: 348/5000 train, 0 errors,
0.4 inst/s, ETA ~3h (train shard) + ~1h (test/zeroshot/vextrap shards).
Resume layers: (1) generator skips finished idx (JSONL); (2) watchdog restarts dead farm;
(3) PROGRESS.md carries PID/log/commands for manual resume.

## 2026-08-02 night — METHODOLOGY DECK v1 DELIVERED (parallel to farm)
method_deck_v1.pptx (12 slides, commit af3e03f) built from user's template.pptx and attached to
YIL-113. Built it MYSELF (not a spawned agent — accuracy over delegation; user allowed either).
Fixed during render-check: figure overflow + STALE fig8 (option-a horizon 418) -> regenerated
fig8b_bigrid_optionb.png (horizon 338, symmetric arrivals). Slide 11 = [RESULTS PENDING]
placeholder; v2 after extension-1 training (fill results + add per-case pages).
Farm at deck delivery: 2000/5000 train (40%), 0 errors, PID alive 1h15m, ETA ~2h for train shard.

## 2026-08-02 ~20:00 EDT — FARM COMPLETE (watchdog confirmed; autopilot paused)
farm.log ends `FARM COMPLETE Sun 02 Aug 2026 07:55:53 PM EDT`; PID 3063842 exited cleanly.
All 4 shards at target, **6100 labels total, 0 error lines** (grep -c error):
train_seed0 5000/5000, test_seed10000 500/500, zeroshot_seed20000 300/300, vextrap_seed30000 300/300.
Completion comment posted on YIL-113; watchdog autopilot 7c6293c2 paused per its playbook.
Training NOT auto-started (bigrid model code not yet built — next-step list below still applies).

## Next step on resume
Data is ready. Build bigrid model (task tokens Emb(o)+Emb(d)+Proj(t0); variable-len seqs;
min_finish masks), train 40ep, 3-layer eval (same-dist / OD-zero-shot / V-extrapolation),
3 seeds -> stable checkpoint -> pipeline REVIEW comment -> PPT v2 (results slides).
Branch exp/fm-mcvrp-local. Env: `source ~/anaconda3/etc/profile.d/conda.sh && conda activate torchnn`.

## 2026-08-03 — FARM COMPLETE + FIRST EXTENSION-1 MODEL TRAINED & EVALUATED (commit a0788ac)
Farm: 6100/6100 labels, 0 errors (5000 train / 500 test / 300 zeroshot / 300 vextrap); route len
med 10 (roaming ~2x min = sensing behavior in labels); vextrap solves hit 60s cap (looser refs).
Watchdog: fired 3x silently (healthy), now PAUSED by me (farm done).
Training (bigrid_train.py): BiRouteModel 1.05M, 60ep ~4min GPU, checkpoint results/
bigrid_model_seed0.pt (best val_gap 0.0722, still converging).
**3-layer eval (masked greedy):**
- L1 same-dist: 500/500 feasible, mean gap 0.0813 (~21% of |obj|), 4/500 match Gurobi
- L2 OD-ZERO-SHOT: 300/300 feasible, mean gap 0.0866 — ONLY +6.5% rel. vs L1 => OD transfer WORKS
- L3 V-extrap {5,8}: 300/300 feasible, mean gap 0.0605, **51/300 BEAT the (time-capped) Gurobi ref**
Honest read: much harder task than toy (roaming tours, 56 ODs, var V) — v1 quality far from toy's
0.1-0.3%; but feasibility 1100/1100, OD-conditioning validated, first beats-reference cases appear.
Levers queued: longer training (300ep run LAUNCHED, PID 3203182, log results/train300.log),
data slope 1k/2k/5k, NS multi-sample decode, bigger d. 
## Next step on resume
Collect train300 (results/bigrid_model_seed0_ep300.pt), re-eval 3 layers; then 1k/2k/5k slope,
NS-16 decode eval; per-case CSV + route viz for bigrid; REPORT.md + full pipeline REVIEW comment;
deck v2 (fill slide 11 + results pages). 3 seeds if time.

## 2026-08-03 later — 300ep collected (NEGATIVE-ISH result) + alpha-conditioning designed
train300 done: CE 0.32->0.085 but best val_gap WORSE (0.0722->0.0736) = imitation overfitting.
ep300 3-layer eval: L1 0.0776 (was 0.0813, +5/500 match), L2 0.0869 (flat), L3 0.0602 (59/300 beat).
Conclusion: longer training exhausted; levers = DATA VOLUME (slope 1k/2k/5k->extend farm) + NS
multi-sample decode + possibly larger d. Alpha-conditioning (user Q): design = global config token
MLP([alpha2]) in encoder; farm randomizes alpha2 in {0.5..0.9} (below ~0.5 collapses to min-time);
labels per-instance alpha; eval adds unseen-alpha interpolation (train {0.5,0.7,0.9} test {0.6,0.8}).
RouteFinder global-attribute-embedding = literature precedent. Fold into NEXT farm batch (with slope
extension). Default proceeding unless user redirects.

## 2026-08-03 night — alpha objective ANALYSIS (user challenge; farm extension ON HOLD pending discussion)
User challenged "a2<0.5 useless" claim. Verified with code + math + sweep (fixed V=3 instance,
MIPGap 0.5%):
- Current objective (bigrid_milp:94): min (a1*cost - a2*cov)/(V*H) — BOTH terms same denominator
  => normalized, same scale. (Legacy small-example had mismatched norms: cost raw, cov/(links*T).)
- Marginal coupling: 1 step through fresh cell => dC=dK=1 => dObj=(a1-a2)/VH. Sign flips at
  a2/a1=1 REGARDLESS of normalization => knife-edge at 0.5 is structural, not scaling.
- Sweep: a2=0.30/0.45 -> cost=cov=170 (EXACT min-time routes); a2=0.50 -> 843 (degenerate tie);
  a2=0.55/0.70/0.90 -> 1001 (horizon-saturated roaming, nearly invariant).
- => alpha in this formulation is a BINARY REGIME SWITCH (min-time vs full-roam), not a dial;
  H does the real limiting. My earlier "completely useless" refined: below 0.5 coverage still
  tie-breaks among min-cost solutions (invisible here: min-time already 0-overlap).
- Design options posted for a REAL dial: (a) per-vehicle BUDGET B<=H conditioning (natural,
  shift-time semantics, no objective change); (c) per-cell utility weights w_i (matches real PartB
  sensing landscape; a2/a1 becomes visit-worthiness threshold -> continuous response).
  Farm extension WAITS for user's choice (their instinct: discuss before scaling — correct).
