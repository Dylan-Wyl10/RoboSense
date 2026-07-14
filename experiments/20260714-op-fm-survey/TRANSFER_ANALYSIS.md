# Transfer-feasibility analysis — neural OP/TOP & VRP foundation models → route_cart_tsc

Author: ML_Optimize_Research_Agent (YIL-113). This is *our mapping*, kept separate from paper fact
(paper fact lives in [SUMMARIES.md](./SUMMARIES.md)). Reading discipline: paper claims are reported as-is;
everything below the "our problem" line is my mapping and is flagged as such.

## Our problem (route_cart_tsc), in one paragraph
A robotaxi fleet under **per-vehicle budget** (shift time / energy) **selects and sequences road SEGMENTS**
of a **fixed road network** to **maximize sensing utility**. Taxonomically this is a
**team-orienteering / VRP-with-profits** problem (selective coverage, max-utility, budget-constrained) —
**not** a CVRP variant (visit-all, min-cost). The MILP/Gurobi pipeline is ground truth and the baseline to beat.

Three structural features drive every mapping below:
- **Selective + max-utility** (subset selection, not visit-all) → need budget masks + subset-selection decoding, not capacity masks.
- **Per-vehicle budget** (multi-vehicle team) → per-vehicle return-feasibility feasibility handling.
- **Fixed road network + arc/segment-level utility, potentially time-varying** → the delta from all surveyed node-based work.

---

## A. Neural OP/TOP → us (Batch A)

| Paper | Transfer verdict | What maps directly | What does NOT map / delta |
|---|---|---|---|
| **A3 TOP-Former** ★ | **High — closest template** | Learned centralized multi-vehicle TOP: pick+sequence, max reward, **per-vehicle return-to-depot budget masking**; simultaneous multi-agent decoding | single shared depot; homogeneous budget T; **static** node reward; node-based (not arcs); O(n²) scaling |
| **A4 UAS-MSTOP** | **High if we re-plan mid-shift** | Heterogeneous starts + remaining energy; **re-encode graph per vehicle**; data-efficient instance-aug baseline | node-based synthetic; "data-efficient" = training-speed, not solution-quality, innovation |
| **A1 Kool AM** | **Medium — reusable kernel** | The feasibility **kernel** every learned OP/TOP inherits: **depot-as-terminal action + "visit only if you can still return within budget" masking** | single-vehicle OP only; no team/per-vehicle budget |
| **A2 POMO** | **Low as a method; parts reusable** | Training/inference parts: shared-baseline REINFORCE, ×8 augmentation | **does not solve OP/TOP**; multi-start symmetry **breaks** for max-prize subset selection (different starts → different subsets) |
| **A5 DTOP-SC** | **Baseline, not neural** | Structurally very close (selective, per-vehicle budget, multi-vehicle, +TW/OD); **scenario-sampling anticipation** if utility is revealed over time | pure OR/ALNS (no learning); "dynamic" = deterministic online arrivals |

**Synthesis for A:** the most reusable learned recipe is a **TOP-Former/MSTOP-style decoder with per-vehicle
return-feasibility budget masking** (the Kool-AM kernel generalized to a team). POMO contributes only training
tricks. DTOP-SC is the strong non-learning baseline (and the anticipatory design if sensing utility is time-revealed).

**The shared gap = our claim.** All five are node-based, static-reward, mostly-homogeneous-budget. Our problem is
**arc/segment-level on a real fixed network with time-varying sensing utility and per-vehicle budgets**. Concretely
the adaptations are: (1) solution representation over **arcs/segments**, not nodes; (2) **budget masks** (residual
shift time/energy + return feasibility) instead of capacity masks; (3) a **subset-selection** decoder (choose which
segments to sense); (4) optionally **time-dependence** of both travel and utility.

---

## B. VRP/CO foundation models → us (Batch B)

- **B2 FM-MCVRP — most directly transferable (closest to our setting).** Our daily instances **are** subsets of one
  **fixed road network**, exactly the FM-MCVRP premise (all instances = subgraphs of one fixed graph). The recipe maps
  almost directly onto our stated direction: **supervised learning on historical MILP/Gurobi solutions over our fixed
  network**, sequence-model decoding (nucleus sampling), curriculum over instance size. Its headline — **SL can beat
  its (sub-optimal) training labels** by aggregating across many instances — is the strongest argument that training
  a fast solver on our Gurobi solutions could match or exceed per-instance Gurobi under a time budget.
  *Delta:* FM-MCVRP is still visit-all min-cost CVRP; we must swap in a **selective/max-utility** objective with
  **budget masking + subset-selection** decoding (the OP/TOP feasibility kernel from Batch A).

- **B1 RouteFinder / B3 GOAL — adapter-style fine-tuning path.** If we start from a pretrained multi-task solver and
  **adapt** (RouteFinder **EAL** zero-padded projections; GOAL input/output adapters), we inherit a strong backbone.
  **Standing caution (from our project mandate):** most multi-task VRP FMs unify **visit-all min-cost** variants;
  selective/profit problems (OP/PCTSP) appear only as small transfer targets. So transfer is **not** out-of-the-box —
  it needs a changed **solution representation** (subset selection) and **feasibility handling** (budget masks, not
  capacity masks). RouteFinder's attribute-composition env would need a new "selective/prize" attribute + budget
  constraint that these releases do not ship.

- **B4 UniCO — least direct.** Reducing our **arc-level, selective, time-varying sensing** problem to a matrix-encoded
  general TSP is not natural (selective coverage ≠ a single Hamiltonian tour; time-varying utility resists a static
  cost matrix). Keep as a conceptual alternative, not a near-term path.

---

## Bottom line (recommendation)
The most promising synthesis for route_cart_tsc: **FM-MCVRP-style supervised learning on our MILP/Gurobi solutions over
the fixed road network**, using a **TOP-Former/MSTOP-style decoder with per-vehicle return-feasibility budget masking**
(the generalized Kool-AM kernel) and **subset-selection** decoding for the selective sensing objective. RouteFinder/GOAL
adapters are a viable pretrain-then-adapt alternative but require selective-objective + budget-mask changes first. UniCO
is out of scope. Gurobi/MILP stays as ground-truth labels and the baseline to beat; DTOP-SC's scenario-sampling is the
anticipatory OR baseline if sensing utility is revealed over time.

*Feasibility spike, not a full reproduction — verdict on which single method to prototype first: **A3 TOP-Former decoder + B2 FM-MCVRP SL recipe**, iterate.*
