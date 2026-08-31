# Data policy

This repository tracks **code, simulation settings, and case-study configuration**.
Raw SUMO simulation output is **not** tracked: it is regenerable, and it accounted
for ~436 MB across 59 files, which made the repository slow to clone for no benefit.

## What is tracked

| Kind | Examples | Tracked |
|---|---|---|
| Source code | `src/**`, `analysis/*.py`, notebooks | yes |
| Network / demand definitions | `*.net.xml`, `*.sumocfg`, `*.add.xml`, `*.taz.xml`, `*.od`, `*.odtrips.xml`, `od.rou.xml` | yes |
| CTM configuration | `sumo_cfg/**/CTMcfg/*.csv`, `demand.csv`, `linkdirction_5x5.csv` | yes |
| Calibration artefacts | `result/ctmResult/CTMcali*.json`, `CTMcell_index.json`, `edge_data.xml`, `lane_data.xml` | yes |
| **Aggregated** results | `result/**/overall*.xml`, `result/5x5net/flextable/*.json` | yes |
| **Raw** per-vehicle / per-step output | `summary*.xml`, `tripinfo*.xml`, `detector_out.xml` | no |
| Large run logs | `result/ctmResult/logs/**` | no (already ignored) |

## How to get the raw output back

Two options:

1. **Re-run the simulation.** The tracked `.sumocfg` files under
   `sumo_cfg/*/simcfg/` (5x5 net) and `sumo_cfg/toy_net/*.sumocfg` (toy net)
   reproduce every case; SUMO writes `summary*.xml` / `tripinfo*.xml` itself.
2. **Cloud copy.** _TODO: link to be added by the author._ The archive keeps the
   same directory layout as this repository, so it can be unpacked over a clone.

The files removed from tracking were **not deleted from anyone's working copy** —
they were removed with `git rm --cached` only, and history was **not** rewritten,
so every blob below is still reachable at commit `2ba8b9d` and can be restored with:

```bash
git checkout 2ba8b9d -- <path>
```

## Manifest of untracked raw output

59 files, 436.4 MB, as of commit `2ba8b9d`.

| Path | Size (MB) | Blob |
|---|---:|---|
| `result/5x5net/sumolog_pr2/summary0.xml` | 6.1 | `f8dc9b9a4c84` |
| `result/5x5net/sumolog_pr2/summary1.xml` | 6.1 | `0ca9505b5447` |
| `result/5x5net/sumolog_pr2/summary10.xml` | 6.1 | `203a25a9d7ad` |
| `result/5x5net/sumolog_pr2/summary2.xml` | 6.1 | `cb576a79dc8c` |
| `result/5x5net/sumolog_pr2/summary5.xml` | 6.1 | `3036aae73f0f` |
| `result/5x5net/sumolog_pr2/summary_benchmark.xml` | 6.1 | `5c6026b7272f` |
| `result/5x5net/sumolog_pr2/tripinfo0.xml` | 1.4 | `75d958b7dcdf` |
| `result/5x5net/sumolog_pr2/tripinfo1.xml` | 1.4 | `fc6766d9e83e` |
| `result/5x5net/sumolog_pr2/tripinfo10.xml` | 1.4 | `d7befaa2d12b` |
| `result/5x5net/sumolog_pr2/tripinfo2.xml` | 1.4 | `98e38f590f8c` |
| `result/5x5net/sumolog_pr2/tripinfo5.xml` | 1.4 | `6c189110acc9` |
| `result/5x5net/sumolog_pr2/tripinfo_benchmark.xml` | 1.4 | `df823e2c9d40` |
| `result/5x5net/sumolog_pr5/summary0.xml` | 10.9 | `72dfe9aa4950` |
| `result/5x5net/sumolog_pr5/summary1.xml` | 10.9 | `7f05eb15ec71` |
| `result/5x5net/sumolog_pr5/summary10.xml` | 10.9 | `d7a2d7529e48` |
| `result/5x5net/sumolog_pr5/summary2.xml` | 10.9 | `b11d5a971058` |
| `result/5x5net/sumolog_pr5/summary5.xml` | 10.9 | `901c8ebded4f` |
| `result/5x5net/sumolog_pr5/summary_benchmark.xml` | 10.9 | `cffd41d8e3c0` |
| `result/5x5net/sumolog_pr5/tripinfo0.xml` | 2.7 | `dc7b15a72d0d` |
| `result/5x5net/sumolog_pr5/tripinfo1.xml` | 2.7 | `367fe598eee9` |
| `result/5x5net/sumolog_pr5/tripinfo10.xml` | 2.4 | `941286913e38` |
| `result/5x5net/sumolog_pr5/tripinfo2.xml` | 2.6 | `3137b89f0572` |
| `result/5x5net/sumolog_pr5/tripinfo5.xml` | 2.6 | `74df63617873` |
| `result/5x5net/sumolog_pr5/tripinfo_benchmark.xml` | 2.5 | `49ea9ca1fa24` |
| `result/ctmResult/detector_out.xml` | 2.9 | `24f6f9a77b8f` |
| `result/toynet/sumolog_pr2/summary0.xml` | 15.7 | `f38843fb9683` |
| `result/toynet/sumolog_pr2/summary100.xml` | 15.9 | `eb5b2559eff9` |
| `result/toynet/sumolog_pr2/summary1000.xml` | 15.2 | `409cf71be283` |
| `result/toynet/sumolog_pr2/summary2000.xml` | 15.5 | `4c289ce0aa44` |
| `result/toynet/sumolog_pr2/summary300.xml` | 15.5 | `b4ec28cee4c0` |
| `result/toynet/sumolog_pr2/summary500.xml` | 15.5 | `a8401c3f98be` |
| `result/toynet/sumolog_pr2/summary_benchmark.xml` | 14.9 | `c32a8afe165d` |
| `result/toynet/sumolog_pr2/tripinfo0.xml` | 3.5 | `5fd885b4bf8d` |
| `result/toynet/sumolog_pr2/tripinfo100.xml` | 3.5 | `c621c11ac728` |
| `result/toynet/sumolog_pr2/tripinfo1000.xml` | 3.5 | `dc931199c74b` |
| `result/toynet/sumolog_pr2/tripinfo2000.xml` | 3.5 | `4ea63d9cf6b8` |
| `result/toynet/sumolog_pr2/tripinfo300.xml` | 3.5 | `8d9f42871cb1` |
| `result/toynet/sumolog_pr2/tripinfo500.xml` | 3.5 | `07b38d47ea0f` |
| `result/toynet/sumolog_pr2/tripinfo_benchmark.xml` | 3.5 | `b863abffb0a0` |
| `result/toynet/sumolog_pr2old/summary.xml` | 17.8 | `c37de112dc39` |
| `result/toynet/sumolog_pr2old/summary0.xml` | 13.6 | `be424ddd9592` |
| `result/toynet/sumolog_pr2old/summary100.xml` | 13.4 | `20fcccff64a2` |
| `result/toynet/sumolog_pr2old/summary1000.xml` | 13.4 | `b1afe8e3c8a4` |
| `result/toynet/sumolog_pr2old/summary2000.xml` | 13.4 | `ba26cfcb7e48` |
| `result/toynet/sumolog_pr2old/summary300.xml` | 13.4 | `1271bf4bbfb2` |
| `result/toynet/sumolog_pr2old/summary500.xml` | 13.4 | `34d7ed414c1c` |
| `result/toynet/sumolog_pr2old/summary_benchmark.xml` | 13.6 | `28cfbed438c2` |
| `result/toynet/sumolog_pr2old/tripinfo.xml` | 3.5 | `0d4b3b046012` |
| `result/toynet/sumolog_pr2old/tripinfo0.xml` | 3.5 | `0172ee18e4dd` |
| `result/toynet/sumolog_pr2old/tripinfo100.xml` | 3.5 | `b397ac3f11d6` |
| `result/toynet/sumolog_pr2old/tripinfo1000.xml` | 3.5 | `c3df41d9508b` |
| `result/toynet/sumolog_pr2old/tripinfo2000.xml` | 3.5 | `48289d7e14d2` |
| `result/toynet/sumolog_pr2old/tripinfo300.xml` | 3.5 | `c3c50f7ba71e` |
| `result/toynet/sumolog_pr2old/tripinfo500.xml` | 3.5 | `168acd524ef9` |
| `result/toynet/sumolog_pr2old/tripinfo_benchmark.xml` | 3.5 | `44d76c463a11` |
| `sumo_cfg/5x5net/summary_benchmark.xml` | 13.6 | `28cfbed438c2` |
| `sumo_cfg/5x5net/tripinfo_benchmark.xml` | 3.5 | `44d76c463a11` |
| `sumo_cfg/toy_net/summary_benchmark.xml` | 13.6 | `28cfbed438c2` |
| `sumo_cfg/toy_net/tripinfo_benchmark.xml` | 3.5 | `44d76c463a11` |

