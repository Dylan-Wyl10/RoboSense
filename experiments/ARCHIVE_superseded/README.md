# Superseded artifacts (moved here 2026-08-04)

Nothing here is current. The live version is
`experiments/20260804-budget-conditioning/` — see its README.

| file | why it is here |
|---|---|
| `method_deck_v1.pptx` | first methodology deck (12 slides, pre-budget objective) — merged into the consolidated deck |
| `method_deck_v2.pptx` | v1 + a budget appendix (18 slides) — an intermediate step, also merged in |
| `build_deck_v2.py` | builder for the above |
| `ext1_checkpoints/bigrid_model_seed0.pt` | pre-budget model, 60 ep |
| `ext1_checkpoints/bigrid_model_seed0_ep300.pt` | pre-budget model, 300 ep (longer training gave no gain) |
| `ext1_checkpoints/model_3x3_seed0.pt`, `model_4x4_seed0.pt` | early toy-grid models |

These were **moved, not deleted**, because checkpoints and decks are not reproducible from
git alone. Safe to delete once you are sure you will not want them:

```bash
rm -rf ~/Research/Route_TSC_CART/experiments/ARCHIVE_superseded    # frees ~16 MB
```

Still live and NOT archived: `experiments/20260716-fm-mcvrp-local/` keeps its label set,
per-case CSVs and the figures the consolidated deck still uses (the network diagram was
copied into the current directory, so that dependency is gone too).
