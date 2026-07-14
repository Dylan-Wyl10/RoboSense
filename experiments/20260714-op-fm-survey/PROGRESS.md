# Survey task — neural OP/TOP + VRP foundation models (issue YIL-113)

Requested by yilin on 2026-07-14 (comment 799f9775 on YIL-113).

## Goal (3 deliverables)
1. **Batch A (5 neural OP/TOP papers)** → per-paper slide in the **slide-3 style** of `notes_discussion.pptx`
   (framing → GAP → **Method** bullets). Focus: gap + methodology details.
   Papers (Zotero "neural top/op"; backup arXiv): 1803.08475, 2010.16011, 2311.18662, 2303.01963, 2601.11010.
2. **Transfer-feasibility analysis** — how much do batch-A methods transfer to our local
   `route_cart_tsc` problem (team-orienteering-type: selective, max sensing utility, per-vehicle budget,
   fixed road network; MILP/Gurobi ground truth). THIS analysis is mine (needs local repo knowledge).
3. **Batch B (4 FM papers, in order)** → 1–2 slide **feature** summary each:
   RouteFinder (2406.15007), FM-MCVRP (2403.00026), GOAL (2406.15079), UniCO (openreview yEwakMNIex).

## Format reference
- Template PPT downloaded: `/tmp/yil113_ppt/notes_discussion.pptx` (attachment 019f5f0b-f788-7d1d-880b-13518202db59).
- **Slide 3 = "Routing Foundation(LR) / LR1"** = the MTPOMO summary. Structure to mirror:
  framing (what NCO is) → gap ("current NCO builds one model per problem") → **Method** bullets
  (attribute composition C+X(O/B/L/TW), unified representation, single-time encoder, reward = -distance).
  Slide 4 = LR1 companion with architecture figure.

## Delegation (reading done by literature-reviewer agent 78eec1e5-bcaa-4086-aed8-fa1b19ed14b2)
- **YIL-114** (c489b0aa-b4b0-45ae-be53-a8eaba52efcf) — batch A reads (gap + methodology). status: todo/assigned.
- **YIL-115** (5584bfeb-1251-452b-937c-e9399c70d42b) — batch B reads (features). status: todo/assigned.
- Reviewer will @mention ML_Optimize_Research_Agent (9f0db3b1-...) on each sub-issue when done.

## Status
- [x] Parsed task, extracted slide-3 format, downloaded template PPT.
- [x] Delegated both reading batches to literature-reviewer (YIL-114, YIL-115).
- [x] Posted plan/ack to yilin on YIL-113.
- [x] Received BOTH reviewer readings — YIL-114 (batch A, accepted 07-14) + YIL-115 (batch B, accepted 07-14).
- [x] Captured both deliveries out of comments → `SUMMARIES.md`.
- [x] Built the deck: `op_fm_survey_slides.pptx` (13 slides) via `build_slides.py`; verified by PDF/PNG render.
- [x] Wrote transfer-feasibility analysis → `TRANSFER_ANALYSIS.md`; `REPORT.md` done.
- [x] Committed on branch `exp/op-fm-survey`.
- [x] Delivered deck to YIL-113 (comment + op_fm_survey_slides.pptx attached, 07-14); reply-accepted on YIL-114/YIL-115; both sub-issues → done. **Task complete; YIL-113 in_review awaiting yilin.**

## Corrections folded in (verified)
1. RouteFinder venue = **TMLR 09/2025**, not ICML 2025 (my intake error).
2. Batch-A #5 DTOP-SC = **NOT neural** (OR/ALNS + scenario sampling) → OR baseline; #2 POMO does **not** solve OP/TOP.

## Deck build recipe (so a future session doesn't re-derive it)
- Template (slide-3 = "LR1"/MTPOMO style): `/tmp/yil113_ppt/notes_discussion.pptx` (attachment 019f5f0b on YIL-113).
- `build_slides.py` clones slide 3 (deep-copy shapes) and swaps text. Header (ph idx 11) = white banner title, keep ≤~24 chars;
  subtitle (ph idx 10) = big bullet, keep short like "LR1"; body = content textbox 'TextBox 4', font Amasis MT Pro, 15/14 pt.
- python-pptx installed into `torchnn`. Render check: `soffice --headless --convert-to pdf` + `pdftoppm`.

## Revisions (post-delivery, on request)
- **rev1 (07-14):** yilin — abbreviations hard to remember → added each paper's **full title** (bold, un-bulleted) atop the
  9 per-paper slides via a `TITLES` map + `make_title()` in build_slides.py; titles verbatim from YIL-114/115 reads.
  Re-rendered (A3/A4 densest, no overflow), re-attached to YIL-113. Overview slides (Agenda/Synthesis/Transfer) keep tags.

## Next step on resume
DONE + delivered (deck attached to YIL-113 on 07-14, transfer verdict = iterate; rev1 title-labels added). Nothing pending
unless yilin asks for edits — if so, iterate on `build_slides.py` and re-render, then re-attach. Possible follow-on the user floated: a RouteFinder
(ai4co/routefinder) code-run spike — NOT requested yet, only a feasibility question; scope it only on explicit ask.

## Open items for the human (non-blocking)
- Literature DB has **two duplicate UniCO pages** (all-caps …971d… + normal …a6e6…) → manual merge.
- Confirm deliverable shape (standalone .pptx, my assumption) vs. paste-into notes_discussion.pptx.
