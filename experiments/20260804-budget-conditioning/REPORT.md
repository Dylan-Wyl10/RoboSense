# Budget conditioning (option (a)) — replacing the α weight with a per-vehicle budget

**Issue:** YIL-113 · **Branch:** `exp/fm-mcvrp-local` · **Date:** 2026-08-04
**Scope:** adapt to our instances (not a paper reproduction) — the literature anchor is
attribute conditioning as used by RouteFinder / MTPOMO, applied to a budget attribute.
**Verdict: ADOPT.** Budget conditioning replaces α as the controllable parameter, the
model learns a continuous budget semantics, and the whole pipeline is cheaper to run.

---

## 1. Why this was done

The 2026-08-03 analysis established that in

```
min ( α₁·Σcost − α₂·Σ y[i,τ] ) / (V·H)
```

the two terms are marginally 1:1 coupled (one extra step buys at most one fresh cell),
so `Δobj = (α₁ − α₂)/(V·H)`. The sign flips at `α₂/α₁ = 1` **independently of the
normalizer** — confirmed separately that both terms already lie in (0,1] before α, with
max exactly 1.000 across all 6100 old labels. α is therefore a **regime switch**, not a
dial, and the real limit on coverage is the horizon `H`.

The user's decision (2026-08-04): pursue **(a) per-vehicle budget only**; defer
**(b) heterogeneous cell utility wᵢ** — stay in the "any cell is as good as any other"
regime for now.

## 2. What was implemented

| File (all NEW; `neural_route/` untouched) | Role |
|---|---|
| `budget_milp.py` | per-vehicle-budget MILP + `budgets_from_slack` + `objective_budget` |
| `budget_datagen.py` | parallel Gurobi label farm with ρ sampling, 7 modes |
| `budget_train.py` | budget-conditioned model, training, 5-layer eval, response curve |
| `aggregate.py` | 3-seed aggregation → `results.csv`, `results/agg_3seed.json` |
| `sweep_alpha.py` / `sweep_budget.py` | the two controlled sweeps on one fixed instance |
| `build_figs.py` / `build_method_figs.py` | result figures / method figures |
| `build_deck_final.py` | the consolidated deck (15 slides, self-contained) |
| `run_farm.sh` / `run_pipeline.sh` | resumable farm; end-to-end pipeline |

**Formulation.** Vehicle *v* gets budget `Bᵥ` and a hard deadline `t0ᵥ + Bᵥ`. Objective
unchanged; normalizer `V·H → Σᵥ Bᵥ`, which preserves the required bound
(`cov ≤ cost ≤ Σᵥ Bᵥ`, so both terms stay in (0,1] before α). Commodity key
`(o,d,t0) → (o,d,t0,B)`; the time-expanded DAG is pruned at `min(H, t0+B)`; the
coverage grid stays on `[0,H)`.

**Slack-ratio parameterization.** `Bᵥ = ⌈ρᵥ · τᵐⁱⁿ(oᵥ,dᵥ,t0ᵥ)⌉`. An absolute budget is
not comparable across ODs (vacuous for near pairs, infeasible for far ones); ρ is, and ρ
is what the model is conditioned on.

**Model deltas (two lines of substance).**
1. Task token `Emb_o + Emb_d + Proj(t0)` → `+ Proj([ρᵥ, Bᵥ/H])` (+0.3 k params).
2. Decoder mask threshold `min_finish(j,t,d) ≤ H` → `≤ t0ᵥ + Bᵥ`.

The second is why budgets generalize: the budget has a **hard mechanical channel** into
decoding, not only a soft preference implied by labels. An unseen budget still yields a
feasible route by construction.

**Not implemented (deliberate):** heterogeneous wᵢ (deferred by the user); multi-sample /
non-greedy decoding; data-volume slope; the 5×5 real network.

## 3. Verification before scaling

- **Reduction check.** At `Bᵥ ≥ H` the budget MILP returns the previous full-horizon
  solution **link-for-link** (cost 999 / cov 999 / lengths [10,12,10]). It is a strict
  generalization, not a different problem.
- **Decomposition check.** Every solve asserts flow-decomposed objective == Gurobi's
  `ObjVal` to 1e-6 and re-validates every per-vehicle deadline (`objective_budget`).
- **Controlled sweeps, one fixed instance (V=3, seed 7), MIPGap 0.5%:**

| control | values swept | distinct solutions | behaviour |
|---|---|---|---|
| α₂ (budget = H) | 13 (0.10 → 0.90) | **2** | 172 cells for α₂ ≤ 0.48, 999 for α₂ ≥ 0.52 — step |
| ρ (α = 0.3/0.7) | 10 (1.0 → 6.0) | **10** | 172 → 200 → 231 → 287 → 314 → 407 → 450 → 497 → 626 → 999 — smooth, monotone |

## 4. Label farm

10 780 labels, **0 errors, 0 hit the 60 s cap** (previous farm: 5.1 % capped, so its
V=8 references were loose). Mean solve **0.90 s** vs 26 s before — tight budgets prune
the DAG, so the farm got ~30× cheaper. ~17 min wall-clock on 15 workers.

`train 8000 · test 800 · zeroshot 400 · vextrap 400 · rhointerp 400 · rhoextrap 300 ·
curve 60 instances × 8 ρ`. Trained ρ anchors {1.0, 1.5, 2.0, 3.0}; **held out** {1.25,
1.75} (interpolation) and {4.0} (extrapolation). 65 % of fleets heterogeneous (per-vehicle
ρ), 35 % homogeneous.

## 5. Results — 3 seeds × 60 epochs, 1.04 M params, ~4 min/seed on one RTX 3090

| layer | n | feasible | mean gap | rel. gap (mean ± std) | match-or-beat |
|---|---|---|---|---|---|
| L1 same-distribution | 800 | **800/800** | 0.0336 ± 0.0012 | **9.2 % ± 0.3** | 274 / 800 |
| L2 OD zero-shot | 400 | **400/400** | 0.0857 ± 0.0026 | 24.0 % ± 0.7 | 60 / 400 |
| L3 fleet extrap. V∈{5,8} | 400 | **400/400** | 0.0548 ± 0.0026 | 15.2 % ± 0.7 | 52 / 400 |
| **L4a UNSEEN budget (interp)** | 400 | **400/400** | 0.0602 ± 0.0001 | 16.7 % ± 0.0 | 31 / 400 |
| **L4b UNSEEN budget (extrap ρ=4)** | 300 | **300/300** | 0.1064 ± 0.0014 | 27.8 % ± 0.4 | 0 / 300 |

2 300 unseen cases, **100 % feasible everywhere**, 6–9 ms per case.

**Response curve** (60 fixed instances re-solved at every ρ, `results/curve.json`):
mean coverage tracks Gurobi's monotone ramp across the whole range, including at the
three ρ values that appear in no training label. At ρ = 1 the budget forces the
min-time route and the model is **exactly optimal, 60/60, gap 0.0**; the undershoot
grows with slack (ρ = 4: 514 vs 708 cells).

## 6. Gap analysis / honest caveats

- **L4b is the weakest layer, as expected.** ρ = 4 sits outside the trained range
  [1, 3]; interpolation (L4a, 16.7 %) is much healthier than extrapolation (27.8 %).
  Cheapest fix: widen the training ρ range — not a modelling change.
- **The undershoot is a decoding limit, not a feasibility one.** Greedy decoding commits
  early; multi-sample decoding is the untried lever and costs no training.
- **The degeneracy from the previous round is unchanged and known:** with uniform utility,
  overlap = 0 in ~92 % of labels, so coverage ≈ cost. The budget controls *how much* to
  roam; *which* cells to prefer would need wᵢ. Deferred by decision, not by oversight.
- Single machine, single GPU; no cross-network transfer claim is made.

## 7. Verdict and next step

**ADOPT.** The controllable parameter is now physical (shift length / energy), continuous,
verified to generalize to unseen values, and it moves the benchmark into the
Orienteering / Team-Orienteering family that the routing foundation-model literature
actually transfers to. Labelling also got ~30× cheaper, which unblocks scale.

Next, in order: (1) multi-sample decoding — free accuracy at inference; (2) widen the ρ
range to repair L4b; (3) data-volume slope on the now-cheap farm; (4) then wᵢ, when the
user wants "which cells" to become a real decision.
