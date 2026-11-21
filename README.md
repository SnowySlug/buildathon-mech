# Snowy Tactics G4

Controlled Mech Royale candidate based on the v1 ground strategy. This variant
changes ray-query correctness and gun reload timing; gameplay improvement is
unmeasured until official practice scoring.

Geometry changes: exact supercover traversal of32m spatial bins catches short
corner crossings missed by fixed24m sampling. Prism queries clip to the vertical
base/top interval before checking polygon occupancy, including vertical rays
whose XY never crosses an edge. Polygon holes remain passable. Terrain sampling
is unchanged; this is not a full replica of game collision physics.

Reload changes: refill a partial magazine while genuinely disengaged or behind
known solid cover, avoid a discretionary reload merely because an active target
is farther than100m, and treat unknown geometry as insufficient proof of cover.
Live weapon magazine/reload/range values are used.

Runtime files at repository root: Dockerfile,.dockerignore,bot.py,navigation.py,
mechfight.py,README.md,LICENSE. No dependencies beyond the pinned Python3.13 base.
The scorer mounts the published map at /arena.

Local validation:12 tests pass, including analytic negative/corner spatial bins,
holes, vertical slab crossings in both directions, and reload-state regressions.
The official recorded checker passed300/300 observations,0late/stale/bad lines,
p9916.7ms,max29.0ms,ready634ms in the1CPU/512MB offline read-only Linux sandbox.
Recorded observations do not react to actions; these are protocol/latency checks,
not a gameplay score. Results depend on machine load.

MIT licensed. Official wrapper derives from the organizer starter and fails on
initialization errors. Bot/navigation/tactics code was developed with AI
assistance during the event. Official protocol, checker and map:
https://www.joinbuilders.org/buildathon/tracks/builders .
