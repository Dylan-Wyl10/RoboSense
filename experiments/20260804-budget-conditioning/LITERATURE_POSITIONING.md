# Literature positioning — where benchmark-v1 stands (2026-08-04)

Question asked (YIL-113): compared with the literature we have read (Notion DB) and any
new literature findable now — (1) is any existing work identical to ours? (2) do we push
beyond each of them, and where? This is the contribution-evaluation record.

Sources: `20260714-op-fm-survey/SUMMARIES.md` (verbatim capture of the full-text reviews
behind the Notion pages, batches A+B), the Notion 文献管理 DB (queried 2026-08-04; the
monitoring/drive-by-sensing shelf), and 5 fresh web sweeps (neural arc routing, TD
orienteering, drive-by sensing, crowdsensing DRL, SED2AM/DeCoST). Paper facts below are
from those sources; every "our delta" line is our mapping.

## 0. What exactly is being positioned

Benchmark-v1 = the frozen method: multi-vehicle **selective** routing on a **fixed
bidirectional road network at arc/segment level** (walks, revisits legal, no U-turn),
**time-dependent** travel costs c(i,t), objective = **space–time coverage union**
(overlap counts once) net of travel cost, each vehicle carrying **its own (o, d, t₀, B)**
(open gate-to-gate trips, staggered departures, hard per-vehicle deadline t₀+B);
solved by **supervised learning on exact MILP labels** with per-vehicle **attribute
conditioning** and a **budget-deadline feasibility mask** (time-dependent Dijkstra);
evaluated by attribute-level zero-shot layers + a solver-tracked **budget response curve**.

Seven axes used throughout:
A1 selective / max-utility (not visit-all) · A2 per-vehicle heterogeneous (o,d,t₀,B) ·
A3 arc-level fixed network · A4 time-dependent travel · A5 space–time union coverage ·
A6 SL from exact MILP + conditioning + hard budget mask · A7 value-level zero-shot +
response-curve evaluation.

## 1. Answer 1 — is anything identical?

**No.** No surveyed or newly-found work occupies the same point; every nearest neighbour
misses at least two of A1–A7, most miss three or more. The three closest, and exactly
what they miss:

- **TOP-Former** (T-ITS 2025) — closest *neural* selective-team work. Has A1, team,
  per-vehicle budget *masking*, centralized decoding. Misses: A2 (single shared depot,
  homogeneous budget T, synchronized start), A3 (Euclidean nodes, not arcs), A4 (static),
  A5 (static node prizes; a node is simply masked once taken), A6 (RL, no labels, no
  budget conditioning), A7.
- **FM-MCVRP** (MIT 2024) — closest *recipe*. Has fixed-graph instances-as-subsets,
  LLM-style SL, joint multi-route token sequence, cross-instance aggregation. Misses:
  A1 (visit-all min-cost CVRP), A2 (no per-vehicle budgets/ODs), A4, A5, and uses
  deliberately sub-optimal labels where we use exact ones; no conditioning axis (A7).
- **Han et al. 2024, TR-B** (drive-by sensing coverage) — closest *problem*. Has
  space–time sensing utility, budget, real networks (A3/A5-adjacent, Chengdu case).
  Misses: any learning (pure optimization, per-instance solve; decisions are fleet
  composition / sensor allocation / trip-level routing, not an amortized learned router)
  — i.e. misses A6/A7 entirely, and per-vehicle OD-duty conditioning as we frame it.

## 2. Answer 2 — per-work deltas (both directions)

Legend: "shared" = what genuinely overlaps; "we add" = our push beyond that work;
"they hold" = what they have that we do not (honesty column — these bound our claims).

### Shelf 1 — neural selective routing (OP/TOP family)

| Work | Shared | We add | They hold |
|---|---|---|---|
| Kool AM (ICLR'19, OP) | selectivity; the mask kernel ("visit only if you can still finish in budget") — our mask is its TD-network generalization | team; per-vehicle (o,d,t₀,B); arcs+revisits; TD travel; coverage union; SL on exact labels; conditioning+curve | canonical benchmark scale (n=20–100); RL needs no labels; community adoption |
| POMO (NeurIPS'20) | training tricks only (not a selective solver) | everything problem-side | multi-start symmetry + augmentation (we use neither yet) |
| TOP-Former (T-ITS'25) | team + per-vehicle budget masking + centralized decode | heterogeneous o≠d/t₀/B per vehicle; arcs; TD; union reward; SL+exact labels; budget as *conditioned input* with verified continuous response | n=100 nodes scale; 0.22 ms GPU; RL (no label farm needed) |
| UAS-MSTOP ('23) | heterogeneity precedent (per-vehicle start + remaining fuel) | our heterogeneity is (o,d,t₀,B) with OD *duties*; arcs; TD; union reward; SL; conditioning eval | mid-mission re-planning; data-efficient training baseline |
| DeCoST (ICLR'26, OPTW+variable profits) | learning for a richer OP variant (continuous time vars) | team; arcs; TD travel (they have time *windows*, not TD costs); coverage union; budget conditioning | discrete–continuous decoupling machinery; up to 500 nodes |

### Shelf 2 — VRP/CO foundation models

| Work | Shared | We add | They hold |
|---|---|---|---|
| MTPOMO (the issue's founding paper) | attribute composition; zero-shot *evaluation spirit* | their zero-shot = unseen **combinations** of binary attributes; ours = unseen **continuous values** of one physical attribute, verified against the exact solver (response curve). Plus A1/A3/A4/A5 (they are visit-all CVRP family) | 16+ variant breadth; cross-problem generality |
| MVMoE (ICML'24) | same family, MoE capacity | same deltas as MTPOMO | parameter-scaling recipe |
| RouteFinder (TMLR'25) | attribute conditioning in a deep encoder — our Proj([ρ,B/H]) is literally their recipe applied to a budget; their L (distance-limit) and O (open route) attributes are the visit-all cousins of our B and o≠d | selective coverage objective; TD network; exact-label SL; value-level conditioning eval | 48 variants; EAL adapters; modern encoder stack; scale |
| GOAL (ICLR'25) | imitation/SL training paradigm; OP among its 8 tasks | team selective coverage on TD arcs; budget conditioning; exact labels | cross-task generalist backbone + few-shot adaptation |
| UniCO (ICLR'25) | — (reduction philosophy incompatible: coverage union + TD resists a static cost-matrix TSP) | n/a | reduction elegance for matrix-TSP-reducible problems |
| FM-MCVRP (2024) | fixed graph + SL + joint sequence + "beats its labels" phenomenon (we see 274/800 match-or-beat) | selective/team/budget/TD/coverage (A1–A5); exact labels; conditioning+curve (A6–A7) | 10 001-node real city; 206 M params; curriculum + NS decoding (our next lever) |

### Shelf 3 — time-dependent / arc-level neural routing

| Work | Shared | We add | They hold |
|---|---|---|---|
| SED2AM (TKDD'25, multi-trip TD-VRP) | TD travel times + working-hours cap on real road data — nearest on A4 | selectivity + coverage union (they are visit-all delivery); per-vehicle OD duties; budget as conditioned dial (theirs is a fixed constraint); SL+exact labels | two real Canadian city datasets; larger scale; DRL |
| Neural CARP line (policy-gradient CARP '19; DaAM '26; traversal-attention solver '25) | arc-level routing with NN — nearest on A3 | selectivity (CARP is visit-all required-edges min-cost); budgets; TD; coverage; conditioning | undirected/real CARP benchmarks; capacity handling |

### Shelf 4 — the application literature (drive-by sensing / mobile sensor routing; OR, no learning)

| Work | Shared | We add | They hold |
|---|---|---|---|
| Han et al. '24 (TR-B) | space–time sensing utility + budget + routing — nearest problem statement in print | the *learning* half entirely: amortized per-instance neural solver, feasibility-guaranteed decoding, ms inference; per-vehicle OD-duty conditioning | joint fleet-composition + sensor-allocation design; Chengdu real case; TR-B-grade realism |
| Chen/Qin/Sun '24 (coordinated CV monitoring routing) | routing CVs for network coverage while maintaining service quality — the same tension as our cost-vs-coverage | learned amortization; per-vehicle budget conditioning; exact-label benchmark protocol | city-wide scale; service-quality modelling |
| Zhu et al. '14 (mobile traffic sensor routing) | the OR ancestor: sensor routing as VRP-variant for info coverage | learned solver; TD; per-vehicle budgets; exactness protocol | dynamic-system framing |
| Guo & Qian '24 (ridesourcing drive-by rerouting) | segment-level sensing coverage objective | full route construction (theirs = trip-based rerouting of existing trips); learning | column-generation scalability; ridesourcing realism |
| O'Keeffe '19 (PNAS) | motivation (taxi sensing power; diminishing returns ⇒ routing matters) | any optimization at all (they quantify, not optimize) | empirical 9-city evidence |
| OP surveys (Vansteenwegen '11; Gunawan '16) | they *list* mobile sensor routing as an OP application — confirms our taxonomy | a concrete learned solver for that application | canonical variant taxonomy |
| OR arc orienteering (OARP B&C; TD-AOP "Scenic Routes") | arc-level selective with budget exists in OR; even TD-AOP exists (heuristic, single vehicle) | team version; learning; conditioning | exact/approximation guarantees |
| DTOP-SC ('26, ALNS) | selective, per-vehicle, dynamic | learning/amortization | online arrivals; anticipatory scenario sampling |

### Shelf 5 — adjacent paradigms (different question, not competitors)

- **Predict-and-Search / ML-for-MILP**: accelerates a solver that still runs per
  instance; we *replace* per-instance solving. Complementary (their tricks could speed
  our label farm).
- **DRL vehicular crowdsensing** (DRL-MTVCS INFOCOM'20 etc.): step-wise POMDP *control*
  of dedicated agents on grids — no OD duties, no solver-anchored optimality protocol,
  no amortized one-shot fleet plan.

## 3. The synthesized claim (and what it is NOT)

The landscape has two shelves that do not touch: the **application shelf** (drive-by
sensing OR: right problem — space-time coverage, budgets, real networks — no learning)
and the **neural routing shelf** (right method — amortized constructive solvers — wrong
problem: node-based, static, visit-all or homogeneous-budget selective). **Our
contribution is the bridge**, plus two things neither shelf has:

1. **Problem-class first** (C1): to our knowledge the first learned amortized solver for
   budget-constrained team sensing-coverage routing at arc level with time-dependent
   costs — the OP-application the surveys have pointed at since 2011, done with the
   modern neural toolkit, benchmarked against exact MILP with 100 % feasibility.
2. **Formulation finding** (C2): the α knife-edge analysis. Structurally an instance of
   the classic weighted-sum scalarization pitfall, but with an exact characterization for
   coverage routing (marginal 1:1 coupling ⇒ switch at α₂/α₁=1, normalization-invariant)
   and a constructive fix — replace the preference weight with a physical per-vehicle
   budget. No neural-routing paper in our set analyzes whether its objective weights are
   *learnable dials* at all.
3. **Evaluation protocol** (C3): value-level zero-shot (unseen continuous budgets,
   interpolation AND extrapolation) plus the solver-tracked response curve — extends
   MTPOMO/RouteFinder-style variant-level zero-shot to continuous physical attributes.

**Not claimed (and the table's "they hold" column is why):** scale (80 links vs their
100–10 001 nodes / real cities), cross-network transfer, RL-free-of-labels economy,
online/dynamic operation. Every ingredient of our network is borrowed (mask kernel =
Kool; conditioning = RouteFinder/MTPOMO; fixed-graph SL + joint sequence = FM-MCVRP;
centralized team decode = TOP-Former) — the novelty is the conjunction and the two
methodological items above, not any single architectural piece.

## 4. Threats to these claims (pre-referee list)

- **Uniform-utility degeneracy**: overlap = 0 in ~92 % of labels ⇒ today the benchmark
  under-exercises "which cells" selection; a referee can say it approximates
  budget-constrained longest-walk. Heterogeneous wᵢ (deferred by decision) is the fix
  and should land before any submission that leans on C1.
- **Toy scale / single network**: 4×4, 80 links, no transfer claim. C1 survives as
  "benchmark + recipe"; an application paper needs the 5×5 real network.
- **Gap optics**: 9–28 % relative gaps look large next to sub-3 % neural-VRP numbers;
  needs explicit framing (different problem class, |obj| normalizer, greedy-only decode).
- **Prior-art risk**: closest-miss works keep appearing (DeCoST is ICLR'26); re-run the
  sweep before submission. Specific watch items: any *neural TD-AOP* or *learned
  drive-by-sensing router* would compress C1.

## 5. Pointers

Web-found (this sweep): DeCoST arXiv:2603.06260 · SED2AM arXiv:2503.04085 · neural CARP
(DaAM, S0952197626009772; OpenReview 7ug4oSmN7l; IEEE 8790295) · TD-AOP "Scenic Routes
Now" (SemanticScholar 43ee4deb) · drive-by sensing survey arXiv:2302.00622 · OP survey
arXiv:2512.16865. Notion DB (文献管理): Han et al. 2024 (10.1016/j.trb.2024.103066) ·
Chen/Qin/Sun 2024 (coordinated CV monitoring) · Zhu et al. 2014 (mobile sensor routing)
· Guo & Qian 2024 (ridesourcing drive-by) · O'Keeffe et al. 2019 (PNAS) · Vansteenwegen
2011 / Gunawan 2016 (OP surveys). Batch A/B facts: `20260714-op-fm-survey/SUMMARIES.md`.
