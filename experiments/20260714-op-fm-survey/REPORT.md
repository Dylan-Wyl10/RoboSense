# REPORT — VRP FM & neural OP/TOP literature survey (YIL-113)

**Scope:** literature survey → slide deck + transfer analysis (not a method reproduction).
Turn a literature-reviewer's full-text reads of 9 papers into a discussion deck mirroring the
slide-3 ("LR1"/MTPOMO) style of `notes_discussion.pptx`, plus a transfer-feasibility analysis to
our robotaxi sensing-routing (team-orienteering) problem.

## What was produced
- **`op_fm_survey_slides.pptx`** — 13 slides, built by `build_slides.py` (clones template slide 3 →
  swaps text, so header/subtitle/body formatting match exactly). Verified by rendering to PDF/PNG.
  - Agenda (1)
  - Part A — Neural OP/TOP (5): A1 Kool AM · A2 POMO⚠ · A3 TOP-Former★ · A4 UAS-MSTOP · A5 DTOP-SC⚠(OR)
  - Part B — VRP/CO foundation models (4): LR2 RouteFinder · LR3 FM-MCVRP★ · LR4 GOAL · LR5 UniCO
  - LR6 synthesis — three unification philosophies (+ FM-MCVRP orthogonal)
  - Transfer (2): OP/TOP → us, foundation models → us
- **`SUMMARIES.md`** — the reviewer's per-paper facts, captured out of the issue comments (numbers verbatim).
- **`TRANSFER_ANALYSIS.md`** — our mapping of each method to route_cart_tsc (kept separate from paper fact).
- **`build_slides.py`** — reproducible deck builder (python-pptx).

## Setup deltas / decisions
- Reviewer read source = **full-text arXiv PDFs** (the local Zotero "neural top/op" collection didn't exist).
- Deck built as a **standalone** .pptx (does NOT modify the human's `notes_discussion.pptx`); shares its master/
  layout, so slides can be pasted into that deck if wanted.
- Body font reduced to 15/14 pt (from slide-3's ~18) so the denser survey slides clear the footer.

## Corrections folded in (both verified, both stand)
1. **RouteFinder venue = TMLR 09/2025**, not ICML 2025 (my intake error). Fixed on the RouteFinder slide + summaries.
2. Batch-A **#5 DTOP-SC (2601.11010) is NOT neural** — pure OR (rolling-horizon ALNS + scenario sampling);
   reclassified as an OR/anticipatory-dispatch baseline. **#2 POMO does not solve OP/TOP** (only TSP/CVRP/KP);
   kept as reusable training tricks, flagged ⚠ on its slide.

## Verdict / next step
- **Deliverable complete** for YIL-113's slide + transfer request. Verdict of the transfer analysis (feasibility
  spike): **iterate** — prototype an **FM-MCVRP-style SL recipe on our MILP/Gurobi solutions** with a
  **TOP-Former/MSTOP-style decoder + per-vehicle budget masking**; MILP/Gurobi stays ground-truth & baseline.
- Open item for the human: the literature DB has **two duplicate UniCO pages** — needs a manual merge.
