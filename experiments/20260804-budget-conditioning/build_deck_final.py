"""THE deck (frozen version, 2026-08-04) — one consolidated document.

Replaces the earlier two decks. Everything describes the CURRENT benchmark:
budget-constrained fleet sensing-coverage routing on the fixed 4x4 bidirectional
network, with per-vehicle (o, d, t0, B) conditioning. No prior-round results and
no cross-version comparisons appear anywhere.

Built from the user's template, so master / theme / banner are preserved.
"""

import copy
import json
import os

from pptx import Presentation
from pptx.util import Emu, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = f"{HERE}/ppt/template.pptx"
OUT = f"{HERE}/ppt/sensing_routing_method_and_results.pptx"
R = f"{HERE}/results"
EMU_IN = 914400

AGG = json.load(open(f"{R}/agg_3seed.json"))
CURVE = json.load(open(f"{R}/curve.json"))


def P(k, dec=1):
    return f"{100*AGG[k]['rel_gap_mean']:.{dec}f} % ± {100*AGG[k]['rel_gap_std']:.1f}"


def clone(prs, src):
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    for shp in src.shapes:
        new.shapes._spTree.append(copy.deepcopy(shp._element))
    return new


def set_ph(slide, idx, text):
    for sh in slide.shapes:
        if sh.is_placeholder and sh.placeholder_format.idx == idx:
            p = sh.text_frame.paragraphs[0]
            if p.runs:
                p.runs[0].text = text
                for r in p.runs[1:]:
                    r._r.getparent().remove(r._r)
            else:
                p.text = text
            return sh
    return None


def bullets(slide, x, y, w, lines, size=14):
    tb = slide.shapes.add_textbox(Emu(int(x * EMU_IN)), Emu(int(y * EMU_IN)),
                                  Emu(int(w * EMU_IN)), Emu(EMU_IN))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (lvl, txt, bold) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = ("• " if lvl == 0 else "   – ") + txt if lvl >= 0 else txt
        p.font.size = Pt(size if lvl <= 0 else size - 1.5)
        p.font.bold = bold
    return tb


def pic(slide, path, w, y, caption=None, cap_size=12.5):
    """Centre a figure horizontally; optional caption underneath."""
    x = (13.333 - w) / 2
    slide.shapes.add_picture(path, Emu(int(x * EMU_IN)), Emu(int(y * EMU_IN)),
                             width=Emu(int(w * EMU_IN)))
    if caption:
        from PIL import Image
        iw, ih = Image.open(path).size
        bullets(slide, 0.7, y + w * ih / iw + 0.10, 11.9, caption, size=cap_size)


prs = Presentation(TPL)
n0 = len(prs.slides)
S = list(prs.slides)
TITLE, AGENDA, CONTENT = S[0], S[1], S[3]

# ------------------------------------------------------------------ 1 title
s = clone(prs, TITLE)
set_ph(s, 0, "Yilin Wang    August 2026")
set_ph(s, 11, "Learning to Route for Sensing Coverage")
set_ph(s, 10, "A neural amortised solver for budget-constrained fleet routing "
              "— method and results")

# ------------------------------------------------------------------ 2 agenda
s = clone(prs, AGENDA)
set_ph(s, 10, "202608")
set_ph(s, 11, "Agenda")
bullets(s, 1.2, 2.0, 10.8, [
    (0, "The problem and the network", False),
    (0, "Change (a) — the Gurobi objective: what it is now, and why it changed", True),
    (0, "Change (b) — the neural network: what was redesigned, and why", True),
    (0, "Pipeline: offline label farm  →  supervised training  →  millisecond inference", False),
    (0, "Evaluation design and results (3 seeds, 2 300 held-out cases)", False),
], size=17)

# ------------------------------------------------------------------ 3 problem
s = clone(prs, CONTENT)
set_ph(s, 11, "The problem")
set_ph(s, 10, "Definition")
bullets(s, 0.7, 1.6, 11.9, [
    (0, "One case (an 'operating day'): congestion δ ∈ {0,1}⁸⁰ per directed link · "
        "V vehicles · per-vehicle task (origin gate o, destination gate d, departure t₀, budget B)", False),
    (0, "Vehicles run SIMULTANEOUSLY on one timeline. Entering link i at time t occupies "
        "space–time cells (i, t … t+c−1), with travel time c(i,t) = (base(i)+t)//4 + 1 + δᵢ", False),
    (0, "Objective — maximise sensing coverage, pay for travel, respect each vehicle's budget:", True),
    (-1, "        min  [ α₁·Σ cost  −  α₂·Σ y(i,τ) ] / Σᵥ Bᵥ        "
         "s.t.  vehicle v reaches dᵥ by t₀ᵥ + Bᵥ", True),
    (1, "coverage = |union of occupied (link, time) cells| — overlap counts once", False),
    (1, "Bᵥ = the vehicle's shift length / remaining energy;  α = 0.3 / 0.7", False),
    (0, "Taxonomy: budget-constrained, selective, max-utility fleet routing = "
        "TEAM-ORIENTEERING type — not a visit-all min-cost CVRP", True),
    (0, "Gurobi solves it exactly (multi-commodity time-expanded flow) and is the source of "
        "training labels AND the benchmark; the learned model replaces per-case solving at deployment", False),
])

# ------------------------------------------------------------------ 4 network
s = clone(prs, CONTENT)
set_ph(s, 11, "The problem")
set_ph(s, 10, "Network & instances")
pic(s, f"{R}/fig0_network.png", 9.4, 1.5, [
    (0, "Fixed bidirectional 4×4: 80 directed links, no U-turns · 8 gates (4 corners + 4 edge "
        "midpoints) · all 56 ordered OD pairs feasible (heatmap) · horizon H = 338", False),
    (0, "The network and the OD set are FIXED; what varies per case is δ, V, and each vehicle's "
        "(o, d, t₀, B)", True),
])

# ------------------------------------------------------------------ 5 change (a) why
s = clone(prs, CONTENT)
set_ph(s, 11, "Change (a) — objective")
set_ph(s, 10, "Why the weight had to go")
bullets(s, 0.7, 1.55, 11.9, [
    (0, "The previous objective controlled the cost/coverage trade-off with the weight α₂ and "
        "capped every vehicle at the global horizon H:   min [ α₁·Σcost − α₂·Σy ] / (V·H)", False),
    (0, "Both terms were correctly normalised — verified in (0,1] before α, max exactly 1.000 across "
        "the whole label set. Scaling was NOT the problem", False),
    (0, "The problem is structural. One extra step through a fresh cell costs ΔC = 1 and buys "
        "ΔK ≤ 1, so the two terms are marginally 1:1 coupled:", True),
    (-1, "        Δobj = (α₁ − α₂) / (V·H)        →  the sign flips at α₂/α₁ = 1, "
         "independent of any normaliser", True),
    (0, "α₂ > α₁ ⇒ EVERY detour is profitable ⇒ the optimum roams until the horizon stops it. "
        "α₂ < α₁ ⇒ no detour is ever bought (coverage survives only as a tie-break)", False),
    (0, "So the quantity that actually limited coverage was the HORIZON, not α. "
        "α selected one of two regimes; it could not set a position between them", True),
    (0, "That matters for learning: conditioning a neural solver on α would teach it a switch, "
        "not a continuous semantics", False),
], size=14)

# ------------------------------------------------------------------ 6 change (a) evidence
s = clone(prs, CONTENT)
set_ph(s, 11, "Change (a) — objective")
set_ph(s, 10, "Switch vs dial — measured")
pic(s, f"{R}/figS1_knob_vs_switch.png", 11.6, 1.5, [
    (0, "One fixed instance, one MILP, one solver, MIPGap 0.5 %. LEFT: 13 values of α₂ with the budget "
        "fixed at H → 2 distinct solutions (α₂ = 0.10–0.48 identical link-for-link). "
        "RIGHT: α frozen at 0.3/0.7, per-vehicle budget swept → 10 distinct, monotone solutions", False),
])

# ------------------------------------------------------------------ 7 change (a) the fix
s = clone(prs, CONTENT)
set_ph(s, 11, "Change (a) — objective")
set_ph(s, 10, "The per-vehicle budget")
bullets(s, 0.7, 1.6, 11.9, [
    (0, "The control moves from a preference weight to a PHYSICAL constraint: each vehicle carries "
        "its own budget Bᵥ (shift length / remaining energy) and a hard deadline t₀ᵥ + Bᵥ", True),
    (0, "Parameterised as a SLACK RATIO:  Bᵥ = ⌈ρᵥ · τᵐⁱⁿ(oᵥ, dᵥ, t₀ᵥ)⌉, where τᵐⁱⁿ is the earliest "
        "possible arrival. An absolute budget is not comparable across ODs — vacuous for near pairs, "
        "infeasible for far ones; ρ is comparable, and ρ is what the model is conditioned on", False),
    (0, "Normaliser V·H → Σᵥ Bᵥ, the fleet's actually available driving time. The chain "
        "cov ≤ cost ≤ Σᵥ Bᵥ still holds, so both terms remain in (0,1] before α", False),
    (0, "MILP changes: commodity key (o,d,t₀) → (o,d,t₀,B); the time-expanded DAG is pruned at "
        "min(H, t₀+B); the coverage grid stays on [0,H). Every solve asserts flow-decomposed "
        "objective ≡ Gurobi ObjVal and re-validates each deadline", False),
    (0, "Verified: at Bᵥ ≥ H the budget MILP returns the full-horizon solution link-for-link — "
        "a strict generalisation, not a different problem", True),
    (0, "Side effect worth having: tight budgets prune the DAG, so labelling runs ~30× faster "
        "(0.90 s mean per case) — which is what makes the label set below affordable", False),
], size=13.5)

# ------------------------------------------------------------------ 8 pipeline
s = clone(prs, CONTENT)
set_ph(s, 11, "Method")
set_ph(s, 10, "Pipeline")
pic(s, f"{R}/figM1_pipeline.png", 10.5, 1.55, [
    (0, "Gurobi is the only source of solutions and the only benchmark; it runs OFFLINE. "
        "At deployment the model emits a full fleet plan in 6–9 ms with no solver call", False),
])

# ------------------------------------------------------------------ 9 change (b) figure
s = clone(prs, CONTENT)
set_ph(s, 11, "Change (b) — model")
set_ph(s, 10, "Architecture")
pic(s, f"{R}/figM2_architecture.png", 9.3, 1.48, [
    (0, "Encoder runs once per case; the decoder writes the WHOLE fleet as one token sequence, so "
        "later vehicles attend to the routes already committed by earlier ones", False),
])

# ------------------------------------------------------------------ 10 change (b) rationale
s = clone(prs, CONTENT)
set_ph(s, 11, "Change (b) — model")
set_ph(s, 10, "What changed, and why")
bullets(s, 0.7, 1.55, 11.9, [
    (0, "Starting point: the network and the OD set are fixed, so the original model could bake the "
        "instance into its weights — one configuration, one trained model", False),
    (0, "① Instance attributes moved OUT of the weights and INTO the input.", True),
    (1, "task token = Emb_o(o) + Emb_d(d) + Proj(t₀) + Proj([ρᵥ, Bᵥ/H]) — one token per vehicle, "
        "V tokens appended to the 80 link tokens", False),
    (1, "Why: a single model then serves every OD pair, fleet size, departure time and budget, and "
        "the encoder can reason about the fleet jointly. This is the attribute-conditioning recipe "
        "the routing foundation models use (RouteFinder / MTPOMO); our budget plays the role their "
        "capacity plays", False),
    (0, "② The feasibility mask threshold became the vehicle's OWN deadline.", True),
    (1, "logits[illegal] = −∞ before softmax, with illegal = {not a successor / U-turn, cannot reach "
        "own destination within t₀+B (time-dependent Dijkstra query), SEP not adjacent to own gate}", False),
    (1, "Why this is the important one: the budget gets a HARD mechanical channel into decoding "
        "instead of only a soft preference implied by the labels. Feasibility is therefore enforced, "
        "not learned — and a budget value never seen in training still produces a feasible route", False),
    (0, "The mask has no parameters: rules guarantee feasibility, the network only ranks legal moves", False),
], size=13),

# ------------------------------------------------------------------ 11 training
s = clone(prs, CONTENT)
set_ph(s, 11, "Method")
set_ph(s, 10, "Label farm & training")
bullets(s, 0.7, 1.6, 11.9, [
    (0, "Label farm (parallel, resumable):  δ ~ iid{0,1}⁸⁰ · V ∈ {2,3,4,6} · ODs stratified by "
        "difficulty tercile with 4 pairs held out · t₀ ∈ {0..5} · per-vehicle ρ", False),
    (1, "ρ anchors seen in training: {1.0, 1.5, 2.0, 3.0}. HELD OUT: {1.25, 1.75} and {4.0}", False),
    (1, "65 % of fleets heterogeneous (each vehicle its own ρ), 35 % homogeneous", False),
    (0, "10 780 labels · 0 errors · 0 solves hit the 60 s cap · 0.90 s mean · ~17 min on 15 workers", True),
    (1, "8 000 train · 800 same-distribution test · 400 OD zero-shot · 400 fleet extrapolation · "
        "400 + 300 unseen-budget · 60 instances × 8 ρ for the response curve", False),
    (0, "Training: teacher forcing, next-link cross-entropy (PAD ignored), AdamW, batch 32, "
        "60 epochs. No solver and no generation inside the training loop", True),
    (0, "Model selection is NOT on cross-entropy: every epoch runs masked-greedy decoding on a "
        "validation slice and keeps the checkpoint with the best true objective gap", True),
    (0, "1.04 M parameters · ~4 min per seed on one RTX 3090 · 3 seeds", False),
], size=13.5)

# ------------------------------------------------------------------ 12 eval design
s = clone(prs, CONTENT)
set_ph(s, 11, "Evaluation")
set_ph(s, 10, "Design")
bullets(s, 0.7, 1.65, 11.9, [
    (0, "Five layers, 2 300 cases, none of them seen in training:", True),
    (1, "L1 same-distribution — 800 fresh cases (trained ODs, new δ / task mixes)", False),
    (1, "L2 OD ZERO-SHOT — 400 cases on 4 OD pairs never trained (G1→G5, G6→G2, G4→G8, G7→G3)", False),
    (1, "L3 fleet extrapolation — 400 cases with V ∈ {5, 8}, trained on {2,3,4,6}", False),
    (1, "L4a UNSEEN budget, interpolation — 400 cases at ρ ∈ {1.25, 1.75}", False),
    (1, "L4b UNSEEN budget, extrapolation — 300 cases at ρ = 4.0, beyond the trained range", False),
    (0, "Plus a RESPONSE CURVE: 60 fixed instances re-solved at every ρ by both Gurobi and the "
        "model — the test of whether the budget was learned as a continuous quantity or as a "
        "handful of memorised settings", True),
    (0, "Metrics: feasibility rate · objective gap vs Gurobi (absolute and relative) · fraction "
        "matching or beating Gurobi · inference time · per-case CSV. 3 seeds, mean ± std", False),
    (0, "Tuning used a validation slice of the training shard only; every number below comes from "
        "held-out shards", False),
], size=13.5)

# ------------------------------------------------------------------ 13 results table
s = clone(prs, CONTENT)
set_ph(s, 11, "Results")
set_ph(s, 10, "Five-layer exam")
pic(s, f"{R}/figS3_layers.png", 9.4, 1.5, [
    (0, f"3 seeds × 60 epochs · 2 300 held-out cases, 100 % feasible in every layer · 6–9 ms per case "
        f"· {AGG['L1_same']['match_mean']:.0f}/800 of L1 match or beat Gurobi", False),
    (0, "Unseen budgets (L4a, orange) cost about as much accuracy as an unseen fleet size — the "
        "budget generalises like the other conditioned attributes, not worse", True),
])

# ------------------------------------------------------------------ 14 results curve
s = clone(prs, CONTENT)
set_ph(s, 11, "Results")
set_ph(s, 10, "Budget response curve")
pic(s, f"{R}/figS2_response_curve.png", 9.0, 1.5, [
    (0, f"The monotone budget response is reproduced across the whole range, including at "
        f"ρ = 1.25 / 1.75 / 4.0 — values absent from every training label. At ρ = 1 the budget forces "
        f"the min-time route and the model is EXACTLY optimal (60/60); the undershoot grows with "
        f"slack (ρ = 4: {CURVE[-1]['model_cov']:.0f} vs {CURVE[-1]['gurobi_cov']:.0f} cells), "
        f"which is the limit of greedy decoding", True),
])

# ------------------------------------------------------------------ 15 summary
s = clone(prs, CONTENT)
set_ph(s, 11, "Summary")
set_ph(s, 10, "Where this stands")
bullets(s, 0.7, 1.7, 11.9, [
    (0, "One recipe, verified end to end: Gurobi labels offline → 1.04 M-parameter Transformer → "
        "guaranteed-feasible millisecond inference, conditioned on each vehicle's own budget", True),
    (0, "The control variable is now physical (shift length / energy), continuous, and demonstrably "
        "generalises to budgets never trained on", False),
    (0, "Verification chain at every step: MILP ≡ flow decomposition ≡ simulator · budget MILP ≡ the "
        "full-horizon MILP at B ≥ H · per-case CSVs against Gurobi on every held-out layer", False),
    (0, "Known and deliberately open: with uniform cell utility, overlap = 0 in ~92 % of optimal "
        "solutions, so coverage ≈ cost. The budget controls HOW MUCH to roam; making WHICH cells a "
        "real decision needs heterogeneous utility wᵢ — the next modelling step, not a fix", False),
    (0, "Next levers, in order: multi-sample (non-greedy) decoding · wider ρ range for extrapolation "
        "· data-volume slope · heterogeneous wᵢ · then the 5×5 real network", True),
], size=14)

xml = prs.slides._sldIdLst
for sld in list(xml)[:n0]:
    xml.remove(sld)
prs.save(OUT)
print(f"saved {OUT} with {len(prs.slides)} slides")
