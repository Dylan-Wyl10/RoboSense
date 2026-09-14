# 20260804-budget-conditioning — option (a): per-vehicle budget B as the real dial

Context: YIL-113. 2026-08-03 analysis showed alpha is a BINARY regime switch (min-time vs
horizon-saturated roaming), not a dial, because cost and coverage are marginally 1:1 coupled.
User decision 2026-08-04: do (a) per-vehicle budget ONLY; defer (b) heterogeneous cell utility
w_i ("keep the state where picking A or B is equivalent"). Also asked for the analysis to be
written into the existing deck, plus adjusted training + a usable pipeline.

## STATUS: COMPLETE — delivered 2026-08-04. Verdict ADOPT (see REPORT.md).

## Done

**Feasibility spike (earlier session)**
- `budget_milp.py` — per-vehicle-budget MILP (commodity key (o,d,t0,B), DAG pruned at
  min(H,t0+B), normalizer sum_v B_v, `budgets_from_slack`, `objective_budget`).
- `sweep_budget.py` -> `results_sweep.csv`. B is a continuous dial; reduces EXACTLY to the
  full-horizon MILP at B>=H; solving is faster, not slower.

**This session**
- `sweep_alpha.py` -> `results_alpha.csv`: alpha swept on the SAME instance (seed 7), 13 values
  -> 2 distinct solutions (flat 172 for a2<=0.48, flat 999 for a2>=0.52). Controlled twin of the
  budget sweep, so the two panels of figS1 share one instance.
- `budget_datagen.py` + `run_farm.sh`: 7-mode resumable farm. **10 780 labels, 0 errors, 0 hit
  the 60 s cap** (old farm: 5.1% capped), mean solve 0.90 s (old: 26 s), ~17 min on 15 workers.
  Trained rho anchors {1.0,1.5,2.0,3.0}; HELD OUT {1.25,1.75} (interp) and {4.0} (extrap);
  65% heterogeneous fleets / 35% homogeneous; `curve` mode = 60 instances x 8 rho.
- `budget_train.py`: task token gains Proj([rho, B/H]); decoder mask threshold H -> t0_v + B_v;
  5-layer eval + response curve. 1.04M params, 60 ep ~4 min/seed, 3 seeds.
- `aggregate.py` -> `results.csv` + `results/agg_3seed.json` + per-case CSVs.
- `build_figs.py` -> figS1 (switch vs dial), figS2 (response curve), figS3 (5-layer exam).
- `build_deck_v2.py` -> `ppt/method_deck_v2.pptx`: 18 slides = v1's 11 + 7 new (v1 file NOT
  modified; the stale v1 closing slide is replaced by a refreshed one in v2 only).
- `run_pipeline.sh` — farm | train | eval | report | all; every stage idempotent. Verified.

## Results (3 seeds, mean +- std)

| layer | n | feasible | rel. gap |
|---|---|---|---|
| L1 same-dist | 800 | 800/800 | 9.2% +- 0.3 (274/800 match-or-beat) |
| L2 OD zero-shot | 400 | 400/400 | 24.0% +- 0.7 |
| L3 V in {5,8} | 400 | 400/400 | 15.2% +- 0.7 |
| L4a UNSEEN budget (interp) | 400 | 400/400 | 16.7% +- 0.0 |
| L4b UNSEEN budget (extrap rho=4) | 300 | 300/300 | 27.8% +- 0.4 |

2 300 unseen cases, 100% feasible everywhere, 6-9 ms/case. Response curve: model tracks the
monotone budget ramp including at the 3 never-trained rho values; at rho=1 model is EXACTLY
optimal 60/60; undershoot grows with slack (rho=4: 514 vs 708 cells).

## Honest caveats (also stated on the slides)

- Gaps are NOT comparable with the extension-1 deck numbers: different denominator (sum B_v vs
  V*H) AND a different label set. New baseline, not an improvement claim.
- L4b (rho=4) is outside the trained range [1,3] — widen the range, don't change the model.
- Uniform-utility degeneracy unchanged: overlap=0 in ~92% of labels => coverage ~= cost. Budget
  controls HOW MUCH to roam; WHICH cells needs w_i (deferred by user decision).
- Greedy decoding only; multi-sample decoding untried.

## 2026-08-04 later — CONSOLIDATED & FROZEN (user request)

- The two earlier decks were merged into ONE self-contained document,
  `ppt/sensing_routing_method_and_results.pptx` (15 slides), reorganised around the current
  benchmark: problem → change (a) objective (why the weight was a switch + the budget) →
  change (b) model (architecture + rationale) → pipeline → eval design → results → summary.
  Per user instruction it presents the current setting's numbers plainly: NO prior-round
  results and NO cross-version gap caveats appear anywhere.
- Two method figures rebuilt because the old ones were stale for this model:
  `build_method_figs.py` → figM1 (pipeline) and figM2 (architecture, with the two redesign
  points called out). The old figB still showed d=96 / 2 encoder layers / no budget token.
- The deck build is now self-contained: `ppt/template.pptx` and `results/fig0_network.png`
  are local copies, so nothing outside this directory is read.
- Cleanup: deleted only disposables (`__pycache__`, duplicate per-case CSVs, .pid files,
  superseded eval txt/json). MOVED (not deleted) to `experiments/ARCHIVE_superseded/`:
  method_deck_v1/v2 + their builder, and the 4 pre-budget checkpoints. That directory has a
  README with the one-line command to delete it for real.
- Frozen at git tag `benchmark-v1-20260804` on branch `exp/fm-mcvrp-local`.

## 2026-08-04 latest — literature positioning (user request: contribution evaluation)

- `LITERATURE_POSITIONING.md` written: 7-axis definition of benchmark-v1, per-work
  two-direction delta tables across 5 shelves (neural OP/TOP, VRP foundation models,
  TD/arc neural routing, drive-by-sensing OR, adjacent paradigms), 20+ works.
- Sweep = SUMMARIES.md (batches A+B verbatim) + Notion 文献管理 DB (2 pages queried;
  key adds: Han et al. 2024 TR-B drive-by-sensing coverage; Chen/Qin/Sun 2024 coordinated
  CV monitoring routing; Zhu et al. 2014; Guo&Qian 2024; O'Keeffe 2019 PNAS; OP surveys)
  + 5 web searches (new finds: DeCoST ICLR'26 arXiv:2603.06260; SED2AM TKDD'25
  arXiv:2503.04085; neural CARP line; TD-AOP OR heuristic).
- Verdict: NO identical work; nearest neighbours (TOP-Former / FM-MCVRP / Han'24) each
  miss >=2 of the 7 axes. Contribution = bridge between the application shelf (right
  problem, no learning) and the neural shelf (right method, wrong problem) + alpha
  knife-edge finding + value-level zero-shot & response-curve protocol. Threats logged
  (uniform-w degeneracy, toy scale, gap optics, DeCoST-style prior-art drift).

## 2026-08-05 — deck v2 (user's 6 review comments)

All six addressed; deck now 21 slides (`build_deck_final.py` + `render_eqs.py`):
1. NEW slide "How Bv is set": B_v = min(max(ceil(rho*taumin), taumin), H-t0), 3-step
   algorithm, why ratio-not-absolute, worked example, enters MILP+input+mask.
2. NEW slide "Objective, before vs now": both objectives as rendered equations + a
   4-row what-changed table (control/constraint/normaliser/response).
3. Rigorous math now TWO slides ("Why alpha is a switch, proof I/II"): setup f_alpha,
   cell-accounting Lemma (0<=K<=C, detour bound), collapse Theorem (K=C => f =
   (a1-a2)C/N => step function), Prop A robustness bound C* + a2(C*-K0)/(a1-a2),
   Prop B detour inequality => budget saturation; empirics inline (K/C median 0.999,
   K=C in 84-93%). Equations rendered via matplotlib mathtext (results/eq/*.png).
4. NEW literature slides: 10x8 setting-comparison matrix (axes x works, OURS row) +
   "Neighbours vs ours" takeaway (closest 3, honesty box, C1-C3, threats).
5. Pipeline split into Training (offline; mechanism spelled out: CE teacher forcing,
   selection-by-generation, budget enters twice) and Generation (online; AR loop,
   mask box, 6-9ms) — both as NATIVE shapes.
6. Architecture = 3 slides (overview / encoder token construction / decoder one step),
   all NATIVE rounded boxes + glued ELBOW connectors with arrowheads — fully editable
   in PowerPoint (user can drag; connectors follow).
Verified via LibreOffice PDF render of all 21 slides (subtitles single-line, no logo
overlaps, no clipped equations). run_pipeline report stage now renders equations too.

## 2026-08-05 later — TD-Dijkstra slide (user follow-up on Bv)

- User confirmed the Bv math; asked for (i) plain-language description, (ii) explicit
  acknowledgment that earliest arrival is a PREREQUISITE computed before Bv, (iii) a
  presentation of the time-dependent Dijkstra itself. ("10遍 Dijkstra" in the comment =
  speech-to-text of "TD Dijkstra".)
- Deck now 22 slides: NEW slide 9 "Step 0: earliest arrival" placed BEFORE "How Bv is
  set" — pseudocode panel (native monospace codebox, editable) of
  BiInstance.earliest_arrival, FIFO-correctness bullet, cost bullet, and a "Where it
  runs" box: (1) budget assignment V runs/case (~41 000 across the farm, counted from
  the shards), (2) decoder mask min_finish memoised variant, (3) horizon calibration.
- "How Bv is set" slide gained a plain-words intro line and Step 2 now points back to
  the Step-0 slide. codebox() helper added to build_deck_final.py.

## 2026-08-05 latest — YIL-125 r1 (PPT presentation discussion, round 1)

User questions on the network slide answered + deck now 24 slides:
- Numbers on the 4x4 figure = DIRECTED LINK ids 1-80 (E 1-20 / W 21-40 / S 41-60
  / N 61-80), not vehicle anything; they are also the encoder token ids AND
  base(i)=min(id, rev id) feeds c(i,t) — slide-4 caption now says all of this.
- The 8x8 "earliest arrival" heatmap verified BY RECOMPUTATION to be the
  (t0=0, delta=0) slice (G1G2=2, G7G3=159, G5G1=141 all match). Caption fixed.
  Pipeline itself was always time-correct: budgets_from_slack -> min_travel_time
  at each vehicle's own t0v; decoder mask min_finish at current decode time;
  horizon calibrated at delta=1, t0=5.
- NEW `build_anim.py` (added to run_pipeline report stage):
  results/figA_td_travel.gif — 33-frame animation, t0 sweeps 0..160 step 5
  (constants T0_MAX/T0_STEP at top), left = links coloured by entry cost
  c(i,t0), right = 8x8 duration matrix, '*' = arrival past H; 1.4s/0.26s/2s
  frame timing; plays in PowerPoint slideshow, PDF shows frame 1 (=t0=0).
  results/figA_delta_day.png — day seed 7 (42/80 congested), delta on the
  network + increment matrix (+0..+19) vs delta=0 at t0=0.
  Gotchas hit: PillowWriter wrote bogus uniform durations (assemble GIF via
  PIL save with a duration list instead); fig.canvas.buffer_rgba() is a LIVE
  view — .copy() per frame or all frames = last state.
- New slides 5 "Time-dependence" + 6 "Day-to-day: δ" (subtitles MUST be short:
  placeholder wraps ~20+ chars and the figure covers line 2; bottom bullet
  blocks at x=2.05 to clear the CART logo — same convention as the objective
  slide). Verified via PDF render pages 4/5/6/7/11/24.

## 2026-08-05 latest — YIL-125 r2 (periodic link cost, figures only)

User: add a modulo to the first cost term so link cost is bounded for every
t0; animation step 5 -> 1; figures only, NO deck rebuild (deck untouched).
- `build_anim_periodic.py` (standalone, NOT in run_pipeline): BiInstance
  subclasses ModInstance (first term ((base+t) % 96)//4, as asked, sawtooth)
  and TriInstance (fold of period 192, FIFO-safe); exact non-FIFO earliest
  arrival via time-expanded (link, entry-time) Dijkstra with early break.
- Outputs: figB_current_step1.gif (161 fr), figB_mod96_step1.gif (96 fr, one
  seamless period), figB_tri192_step1.gif (192 fr), figB_cost_profiles.png.
- FACTS established (all printed by the script's checks):
  * sawtooth BREAKS FIFO: base=1 link, enter t=94 -> exit 118 vs enter
    t=95 -> exit 96; single-label TD-Dijkstra then WRONG on 18.1% of
    (OD, t0) cells, overestimating up to 32 steps -> adopting sawtooth means
    replacing earliest_arrival / min_finish / Bv machinery (or accepting
    inexpressible wait-at-wrap incentives). Triangle: pointwise <= current,
    slope >= -1, FIFO holds, TD==exact verified.
  * bounded costs shrink far ODs at t0=0 (wrap arrives mid-trip):
    G7->G3 159 -> 67 (mod) / 101 (tri); G1->G5 106 -> 45 / 85. Both variants
    == current cost at t=0 per LINK (base <= 60 < 96); trip-level equality
    only for arrivals <= 36. Durations bounded: mod <= 84, tri <= 112.
  * adoption = recalibrate H + refarm labels + retrain (cheap now); decision
    parked with user; bigrid.py NOT touched (subclass wrappers only).

## 2026-08-05 latest — YIL-125 r3: MOD-96 COST ADOPTED (user decision "取mod就行")

Environment cost law is now c(i,t) = ((base(i)+t) mod 96)//4 + 1 + delta_i.
This round changed ONLY the deck pages that define the environment (user:
"只需要改动的ppt页面"); labels/model/H/results slides are STILL the pre-mod
benchmark — the Step-0 slide carries that transition note explicitly.
- build_anim.py REWRITTEN for mod-96 deck figures (report stage unchanged):
  figA_network_mod.png (slide 4: id/direction network + exact mod heatmap),
  figA_td_travel_mod.gif (slide 5: full period t0 0..95 step 1, seamless),
  figA_delta_day_mod.png (slide 6: DIVERGING increments — see fact below).
  Old figA files remain on disk (pre-mod history), no longer rebuilt.
- Deck pages changed: 3 (formula), 4 (figure+caption: base = congestion
  PHASE now, "E/W structurally faster" is FALSE under mod — equal range,
  phase-shifted), 5 (mod GIF + cycle numbers), 6 (delta effects), 11 (FIFO
  bullet -> exact (link, entry-time) search + pre-mod-results marker).
- FACTS (from build_anim.py checks): durations bounded <= 84 every t0;
  G1->G2 cycles 2..43, G7->G3 cycles 34..84; t0=0 G7->G3 = 67.
  Would-be H under mod (delta=1, t0=5, slack 1.6): 135 (was 338).
  SAWTOOTH SURPRISE: on the seed-7 day increments are -9..+7 and 4/56 ODs
  get FASTER under congestion (+1 delays push a later link past its wrap
  into the cheap zone) — real property of the adopted cost, shown on slide 6.
- NEXT (needs user go in YIL-113 or here): swap bigrid machinery to the
  exact search (propose bigrid.py diff first per repo rules!), recalibrate
  H (~135), refarm labels, retrain 3 seeds, refresh results slides.

## 2026-08-06 — YIL-125 r4: FULL MOD-96 RE-RUN COMPLETE (user go: "可以开工")

Everything re-derived under the adopted cost; see REPORT.md 2026-08-06
section for the numbers table. Mechanics for future sessions:
- `modenv.py` = the environment now (ModInstance + exact min_finish +
  calibrate_horizon -> H=135). budget_datagen/train + sweeps import it;
  `neural_route/` still untouched.
- Paths: labels `data_mod/` (untracked, like `data/`), model/eval/curve
  `results_mod/`, sweeps/results at `results_*_mod.csv` + `results_mod.csv`.
  Pre-mod files byte-identical, tag benchmark-v1-20260804 still valid.
- MAX_LEN 84 -> 128 (farm max seq 88). Params still 1.04 M.
- Farm: 10 780 labels, 33 min/15 workers, 2.08 s mean, 32 cap hits (0.3 %,
  incumbents kept). Train ~4 min/seed x 3. Eval: 100 % feasible, rel gaps
  12.7/16.1/16.7/15.1/18.0 %, 8-14 ms/case; curve near-exact at rho=1.
- Deck fully refreshed (24 slides) and consistent end-to-end with mod-96;
  figS1/figS2 in-figure annotations now data-driven (they were baked-in
  pre-mod literals — check them whenever data changes).
- Delivered to YIL-125: final pptx attached to the r4 comment.

## 2026-08-06 later — YIL-125 r5: MOD-24 SIMPLIFICATION + full re-run v3

User dropped the //4: c = (base+t) mod 24 + 1 + delta (equivalent amplitude,
4x faster clock; see REPORT.md r5 section for all numbers). H=128.
- modenv.PERIOD=24 is THE single source; build_anim now imports ModInstance
  from modenv (no duplicate cost definitions anywhere).
- Benchmark v3 paths: data_mod24/ (untracked) + results_mod24/ +
  results_*_mod24.csv. v2 (mod-96) and v1 (pre-mod) both preserved.
- Slide-5 animation redesigned for clarity (24-frame cycle, plain titles,
  bigger annotations) — user asked for a clearer version + plain-language
  explanation (delivered in the r5 comment).
- Phase folding note: under mod-24, E/W vs N/S no longer split cleanly at
  t=0 (base mod 24); slide-4 wording updated accordingly.

## Next step on resume (in priority order)

1. Multi-sample / non-greedy decoding (free accuracy, no retraining) — FM-MCVRP's NS trick.
2. Widen training rho range (e.g. anchors up to 5) to repair L4b extrapolation.
3. Data-volume slope now that labelling is ~30x cheaper (1k/2k/4k/8k).
4. w_i heterogeneous utility, when the user wants "which cells" to become a real decision.

Env: `source ~/anaconda3/etc/profile.d/conda.sh && conda activate torchnn`. Branch
`exp/fm-mcvrp-local`. Nothing outside this directory is written; `neural_route/` untouched.
