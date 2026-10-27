# Source data of the Sioux Falls network (YIL-231)

Copied unchanged from the TNTP repository `bstabler/TransportationNetworks`, folder `SiouxFalls`,
commit `d1639b4ef218` (2025-06-19):

| File | Content | Used for |
|---|---|---|
| `SiouxFalls_node.tntp` | node coordinates, lon/lat (added to TNTP in 2019) | node positions |
| `SiouxFalls_net.tntp` | 76 directed links (topology) | link list |
| `SiouxFalls_trips.tntp` | 24-zone OD table | demand calibration (reference only) |
| `SiouxFalls_flow.tntp` | best-known equilibrium link flows | target link-flow pattern of the demand calibration |

The free-flow times and the `length` column of `SiouxFalls_net.tntp` are not used (author's decision, 2026-10-27):
link lengths come from the lon/lat geometry, see `src/sf/build_net.py`.

The TNTP data carry no open-source licence; the README of the repository asks that they be used for research and
that the source be cited. Network data originally from LeBlanc, Morlok & Pierskalla (1975), Transportation Research
9(5), 309–318, doi:10.1016/0041-1647(75)90030-1.
