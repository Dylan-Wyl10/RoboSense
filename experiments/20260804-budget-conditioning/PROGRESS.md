# 20260804-budget-conditioning — option (a): per-vehicle budget B as the real dial

Context: YIL-113 thread. 2026-08-03 analysis showed alpha is a BINARY regime switch
(min-time vs horizon-saturated roaming), not a dial, because cost and coverage are
marginally 1:1 coupled. Proposed replacement dial = per-vehicle budget B_v.
User asked (2026-08-04) for the detailed idea. This dir holds the feasibility spike.

## Done (2026-08-04)

- `budget_milp.py` — per-vehicle-budget variant of the bigrid MILP. NEW FILE; does not
  touch `neural_route/` (imports it). Deltas vs `neural_route/bigrid_milp.py`:
  * commodity key (o,d,t0) -> (o,d,t0,B); time-expanded DAG pruned at min(H, t0+B_v)
  * normalizer V*H -> sum_v B_v (keeps both terms in (0,1]: cov <= cost <= sum B)
  * coverage grid stays on [0,H) so cells are comparable across budgets
  * `budgets_from_slack`: B_v = ceil(rho * tau_min_v), floored at tau_min, capped at H-t0
    -> rho (slack ratio) is the OD-comparable, model-conditionable scalar
  * `objective_budget` re-verifies per-vehicle deadlines; MILP obj asserted == decomposed obj
- `sweep_budget.py` + `results_sweep.csv` — fixed V=3 instance (seed 7), alpha FROZEN at
  0.3/0.7, rho swept 1.0 -> 99.

## Key results

1. **B is a continuous dial** (alpha was not). rho 1.0 -> 99 on the same instance:
   cost 172, 181, 200, 231, 287, 314, 407, 450, 497, 626, 999; route lengths
   [2,6,2] -> [10,12,10]. Smooth monotone ramp, no plateau/jump. (Contrast alpha sweep:
   170 -> 170 -> 843 -> 1001 -> 1001 -> 1001.)
2. **Reduction check**: at rho=99 (B >= H) the budget MILP returns EXACTLY the original
   full-horizon MILP solution (cost 999, cov 999, lens [10,12,10]). Objective differs only
   by the normalizer (sum B = 1000 vs V*H = 1014).
3. **Solve cost is LOWER, not higher**: 0.2-1.4 s for rho <= 6 vs 3.0 s at rho=99 —
   tight budgets prune the time-expanded DAG. Extending the farm with B is cheaper per label
   than the current farm.
4. **NEGATIVE / degeneracy finding (matters for the paper)**: overlap = cost - cov is ZERO
   in the sweep at every rho, and across the existing 6100 labels: train 92.2% zero-overlap
   (mean 1.18), test 90.0%, zeroshot 93.3%; only vextrap V=8 has real contention
   (44.3% zero, mean 52.7). cov/cost mean 0.999 at V<=6.
   => with uniform cell utility, coverage is currently a near-restatement of cost, so the
   objective degenerates to "burn the whole budget on a feasible path". B controls HOW MUCH
   (real dial), but there is little WHICH-cells selection pressure to learn.
   => this is the evidence-backed argument for pairing (a) with (b) heterogeneous w_i.

## Honest caveats

- Normalizing by sum_v B_v makes obj values across different rho not directly comparable as a
  difficulty measure (obj wobbles -0.400 .. -0.358 non-monotonically) because discreteness
  prevents exactly saturating B. Within an instance sum B is a constant -> argmin unaffected.
- Budget labels are NOT comparable in objective value with the existing 6100 labels
  (different denominator). Routes/instances remain valid; a re-solve is needed for a joint set.

## Next step (blocked on user's direction)

If green-lit: (1) extend `bigrid_datagen` sampler with rho ~ U[1.0, 3.0] per vehicle
(+ a homogeneous-fleet fraction); (2) task token gains B/rho features (mirror of t0_proj);
(3) decoder mask `min_finish(j,t,d) <= inst.horizon` -> `<= t0_v + B_v` (hard feasibility,
so unseen budgets stay feasible by construction); (4) new eval layer L4 = unseen rho
interpolation + extrapolation, reported as a coverage-vs-rho response curve (model vs Gurobi).
