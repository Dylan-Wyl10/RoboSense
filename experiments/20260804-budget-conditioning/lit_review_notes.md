# Literature slides — full explanations, references, and edit-ready text
(YIL-125 r6, 2026-08-06. Companion to `ppt/lit_review_explained.pptx`.
The main deck is untouched; everything below is copy-paste material.)

## 1. What the table cells mean (legend)

- **✓ (green check)** — the work HAS the column's property, in the full sense
  defined below.
- **— (grey dash)** — the work does NOT have it.
- **grey text in a cell** — the work has only a PARTIAL / weaker form, and the
  text names which one (e.g. "budget only, homogeneous").
- **[n] before a work** — entry n in the reference list (§4).

## 2. What each column asks (suggested full header + one-sentence meaning)

| current header | suggested header | meaning (full sentence) |
|---|---|---|
| selective (not visit-all) | selective: choose what to cover | May the fleet DECIDE which parts of the network to visit, maximising collected utility under a budget (orienteering/profits family)? Dash = visit-ALL at min cost (CVRP/CARP family) — a different problem. |
| per-vehicle (o,d,t₀,B) | per-vehicle duties (o, d, t₀, B) | Does EACH vehicle carry its own origin gate, destination gate, departure time AND budget? Partial forms: TOP-Former = one shared budget value, same depot; Lee & Ahn = own start + remaining fuel, no OD duties; VRP foundation models = distance-limit/open-route attributes (visit-all cousins of B and o≠d). |
| arc-level fixed network | arc-level, ONE fixed road network | Is routing over the LINKS of one fixed network (revisits allowed, same graph every instance) rather than freshly sampled points in the plane? Partial: FM-MCVRP fixes the graph but routes node visits; SED2AM has real road times but node-based delivery. |
| time-dep. travel | time-dependent travel times | Does link travel time depend on WHEN you enter — c(i,t) — so the best route changes with the clock? |
| space–time coverage | space–time coverage objective | Is the reward a UNION of (link, time) cells — where AND when you sensed — re-sensing a cell counts once, same link at two times counts twice? |
| learned amortised | learned amortised solver | Is there a trained neural policy giving solutions in milliseconds at deployment (amortising per-instance optimisation)? |
| budget 0-shot | unseen budget VALUES (zero-shot) | Is the model TESTED on budget values absent from all training labels (continuous interpolation AND extrapolation), verified against an exact solver? "variant-level, not values" = zero-shot only to unseen COMBINATIONS of binary attributes. |

## 3. Row-by-row: original label → suggested label + one-line description

| original row | suggested row label | one-line description |
|---|---|---|
| Kool AM '19 (OP) | [1] Kool et al. 2019 (neural Orienteering) | Founding attention model for learned routing; introduced the budget-feasibility mask (single-vehicle OP) that our decoder generalises. |
| TOP-Former '25 (TOP) | [2] TOP-Former 2025 (neural Team Orienteering) | Centralised transformer decoding a whole team; closest neural relative — but shared depot, one homogeneous budget, Euclidean points, static prizes. |
| UAS-MSTOP '23 | [3] Lee & Ahn 2023 (multi-start TOP for UAS) | Team-orienteering re-planning with heterogeneous current positions + remaining fuel; the heterogeneity precedent. |
| MTPOMO / MVMoE / RouteFinder | [4][5][6] MTPOMO · MVMoE · RouteFinder (multi-task VRP) | The multi-task VRP "foundation model" family: one net for 16–48 visit-all variants via attribute composition; our Proj([ρ, B/H]) is their conditioning recipe applied to a physical budget. |
| GOAL '25 (incl. OP task) | [7] GOAL 2025 (generalist CO agent; OP task) | One imitation-trained backbone across many combinatorial problems (OP among them); breadth, not our setting. |
| FM-MCVRP '24 (fixed graph SL) | [8] FM-MCVRP 2024 (fixed-graph supervised CVRP) | Supervised LLM-style training on ONE fixed city graph; the closest TRAINING RECIPE (fixed graph + supervised labels + joint fleet sequence). |
| SED2AM '25 (TD-VRP) | [9] SED2AM 2025 (time-dependent delivery VRP) | Deep RL for multi-trip delivery with time-dependent travel times from real road data; closest on TIME DEPENDENCE (visit-all). |
| Neural CARP '19–'26 | [10] Neural CARP 2019–2026 (arc routing) | Line of neural solvers for capacitated ARC routing (service on road edges); closest on ARC-LEVEL routing (visit-all, static costs). |
| Drive-by sensing OR (Han'24, Chen'24, Zhu'14) | [11][12][13] Drive-by-sensing OR (Han · Chen · Zhu) | The application shelf: our problem statement (sensing coverage, budgets, real networks), solved per instance with NO learned solver — the gap we fill. |
| OURS (benchmark v1) | OURS (benchmark v3) | Budget-conditioned supervised solver for selective space–time sensing coverage on a fixed time-dependent road network with per-vehicle duties; evaluated value-level zero-shot. |

Also in the current matrix cells:
- "budget only, homog." → "budget only, homogeneous"
- "start + fuel" → "start + fuel only"
- "L / O attrs" → "dist-limit/open: visit-all twins"
- "variant-level" → "variant-level, not values"
- "part" → "partial"
- "fixed graph, nodes" → "fixed graph, node visits"
- "road data" → "real road times"

## 4. References (verified 2026-08-06 against arXiv / publisher pages)

1. W. Kool, H. van Hoof, M. Welling. *Attention, Learn to Solve Routing
   Problems!* ICLR 2019. arXiv:1803.08475
2. D. Fuertes, C. R. del-Blanco, F. Jaureguizar, N. García. *TOP-Former: A
   Multi-Agent Transformer Approach for the Team Orienteering Problem.* IEEE
   Trans. on Intelligent Transportation Systems, 2025. arXiv:2311.18662
3. D. H. Lee, J. Ahn. *Multi-Start Team Orienteering Problem for UAS Mission
   Re-Planning with Data-Efficient Deep Reinforcement Learning.* Applied
   Intelligence, 2024. arXiv:2303.01963
4. F. Liu, X. Lin, Q. Zhang, X. Tong, M. Yuan. *Multi-Task Learning for
   Routing Problem with Cross-Problem Zero-Shot Generalization.* ACM SIGKDD
   2024. arXiv:2402.16891  ("MTPOMO")
5. J. Zhou, Z. Cao, Y. Wu, W. Song, Y. Ma, J. Zhang, C. Xu. *MVMoE:
   Multi-Task Vehicle Routing Solver with Mixture-of-Experts.* ICML 2024.
   arXiv:2405.01029
6. F. Berto et al. *RouteFinder: Towards Foundation Models for Vehicle
   Routing Problems.* TMLR, 2025. arXiv:2406.15007
7. D. Drakulic, S. Michel, J.-M. Andreoli. *GOAL: A Generalist Combinatorial
   Optimization Agent Learner.* ICLR 2025. arXiv:2406.15079
8. S. J. K. Chin, A. Srivastava, M. Winkenbach. *Learning to Deliver: a
   Foundation Model for the Montreal Capacitated Vehicle Routing Problem.*
   MIT, 2024. arXiv:2403.00026  ("FM-MCVRP")
9. A. Mozhdehi, Y. Wang, S. Sun, X. Wang. *SED2AM: Solving Multi-Trip
   Time-Dependent Vehicle Routing Problem Using Deep Reinforcement Learning.*
   ACM TKDD, 2025. arXiv:2503.04085
10. Neural CARP line, anchors: *Learning to Solve Capacitated Arc Routing
    Problems by Policy Gradient* (IEEE CEC 2019, doi:10.1109/CEC.2019.8790295)
    · *A Neural Solver With Traversal-Based Feature Representation and
    Adjacent Attention for CARP* (IEEE, 2025) · *Direction-Aware Deep Policy
    Learning for Efficient Capacitated Arc Routing* (Eng. Appl. AI, 2026)
11. K. Han, W. Ji, Y. M. Nie, Z. Li, S. Liu. *Exploring the Sensing Power of
    Mixed Vehicle Fleets.* Transportation Research Part B 190:103066, 2024.
    doi:10.1016/j.trb.2024.103066 (arXiv:2311.15237)
12. X. Chen, G. Qin, J. Sun. *Coordinated Routing Policy for Connected
    Vehicles to Monitor City-Wide Traffic.* 2024. **[venue to confirm — from
    our Notion notes]**
13. Zhu et al. *Mobile Traffic Sensor Routing in Dynamic Transportation
    Systems.* 2014. **[venue to confirm — IEEE ITS-family journal]**

Also tracked in the threats bullet (takeaway slide): DeCoST, ICLR 2026,
arXiv:2603.06260 — learning for Orienteering with time windows and variable
profits.

## 5. Notes on the takeaway slide ("Neighbours vs ours") — abbreviation fixes

- "TOP-Former (closest neural)" → add "[2]"; "FM-MCVRP (closest recipe)" →
  add "[8]"; "Han et al. '24 TR-B (closest problem)" → add "[11]".
- "RL" → "reinforcement learning (no solver labels needed)";
  "SL" → "supervised learning on solver labels".
- "OURS (benchmark v1)" on the matrix is stale either way — current deck is
  benchmark v3 (mod-24, H = 128).
