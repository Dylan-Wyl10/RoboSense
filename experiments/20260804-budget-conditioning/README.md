# FROZEN BENCHMARK — budget-conditioned sensing-coverage routing (2026-08-04)

This directory is the **single current version** of the method: MILP, label farm, model,
evaluation, figures and deck. Everything older is superseded — see
`experiments/ARCHIVE_superseded/`.

**The deck:** `ppt/sensing_routing_method_and_results.pptx` (15 slides). It is the only
deck to present; it covers the method as it stands now, the two changes that got it here
(objective, model), and the current results. Nothing in it refers to earlier versions.

## Run it

```bash
source ~/anaconda3/etc/profile.d/conda.sh && conda activate torchnn
./run_pipeline.sh            # farm -> train (3 seeds) -> eval -> curve -> figures -> deck
./run_pipeline.sh farm       # labels only (resumable; safe to interrupt)
./run_pipeline.sh train      # training only
./run_pipeline.sh eval       # 3-seed five-layer eval + response curve
./run_pipeline.sh report     # figures + deck
```

Every stage is idempotent. Nothing outside this directory is written, and
`neural_route/` (the shared environment / MILP code) is imported, never modified.

## Layout

| path | what |
|---|---|
| `budget_milp.py` | per-vehicle-budget MILP: deadline t₀+B, commodity key (o,d,t₀,B), normaliser Σ Bᵥ, `budgets_from_slack`, `objective_budget` |
| `budget_datagen.py` | parallel Gurobi label farm, 7 modes, resumable |
| `budget_train.py` | budget-conditioned model, training, five-layer eval, response curve |
| `aggregate.py` | 3-seed aggregation → `results.csv`, `results/agg_3seed.json` |
| `sweep_alpha.py` / `sweep_budget.py` | the two controlled sweeps on one fixed instance |
| `build_figs.py` | figS1 switch-vs-dial · figS2 response curve · figS3 five-layer exam |
| `build_method_figs.py` | figM1 pipeline · figM2 architecture |
| `build_deck_final.py` | the deck (self-contained: uses `ppt/template.pptx` + `results/*.png`) |
| `run_farm.sh` / `run_pipeline.sh` | farm driver / end-to-end pipeline |
| `REPORT.md` / `PROGRESS.md` | full write-up / session state |
| `data/` | 10 780 Gurobi labels (7 shards, gitignored) |
| `results/` | checkpoints (gitignored), per-case CSVs, JSON summaries, figures |

## The frozen numbers

3 seeds × 60 epochs, 1.04 M parameters, 2 300 held-out cases, **100 % feasible in every
layer**, 6–9 ms per case.

| layer | n | rel. gap vs Gurobi |
|---|---|---|
| L1 same-distribution | 800 | 9.2 % ± 0.3  (274/800 match or beat Gurobi) |
| L2 OD zero-shot | 400 | 24.0 % ± 0.7 |
| L3 fleet extrapolation V∈{5,8} | 400 | 15.2 % ± 0.7 |
| L4a unseen budget, interpolation | 400 | 16.7 % ± 0.0 |
| L4b unseen budget, extrapolation | 300 | 27.8 % ± 0.4 |

Label farm: 10 780 labels, 0 errors, 0 solves hit the 60 s cap, 0.90 s mean per solve.

Git tag for this state: **`benchmark-v1-20260804`** on branch `exp/fm-mcvrp-local`.
