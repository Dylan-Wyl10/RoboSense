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

## Next step on resume (in priority order)

1. Multi-sample / non-greedy decoding (free accuracy, no retraining) — FM-MCVRP's NS trick.
2. Widen training rho range (e.g. anchors up to 5) to repair L4b extrapolation.
3. Data-volume slope now that labelling is ~30x cheaper (1k/2k/4k/8k).
4. w_i heterogeneous utility, when the user wants "which cells" to become a real decision.

Env: `source ~/anaconda3/etc/profile.d/conda.sh && conda activate torchnn`. Branch
`exp/fm-mcvrp-local`. Nothing outside this directory is written; `neural_route/` untouched.
