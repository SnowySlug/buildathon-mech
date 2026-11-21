# Snowy Perch v3

Mech Royale strategy experiment: acquire a reachable rooftop in the next safe
zone, regenerate behind its edge, and peek toward targets when healthy.
Gameplay strength must be measured by official practice matches; conformance
and local flight tests do not produce a placement score.

The published prism/terrain map supplies roof support and cover geometry.
The bot navigates to a clear launch point outside the roof, climbs vertically
outside eaves, transfers above the edge, and lands before walking on the roof.
Its jet budget uses live drain, acceleration and speed values plus transfer and
reserve margins. It abandons unsafe/late plans and returns to ground behavior.
On a roof it preserves energy, avoids unsupported edges, holds fire to regenerate
below90%HP when a genuinely concealed point exists, and seeks a reachable
downward firing angle while healthy or unable to conceal itself.

Ground behavior uses the v1 movement/combat thresholds. It retains tested fixes
for intentional waiting being mistaken for a wall collision and compatible gun
fire during laser charging. It does not include v2's stronger ground retreat,
180m boost policy, or drone farming. Laser charging is disabled during transfers
because the published rules halve movement while charging.

Runtime files at repository root:

- Dockerfile and .dockerignore
- bot.py, navigation.py, roof.py, mechfight.py
- README.md and LICENSE

No map or third-party packages are embedded in the image. The scorer mounts the
published map at /arena. The pinned Python3.13 image targets linux/amd64.

From the development workspace:

```powershell
& ./.venv/Scripts/python.exe -m unittest discover -s tracks/mech/versions/perch/tests -v
& ./.venv/Scripts/python.exe tracks/mech/versions/perch/check_entry.py
```

Validation:13 tests pass, including roof/courtyard geometry, published-map launch
plans, live energy budgets and bounded20Hz vertical-control tests for6/14/25m
roofs. The latter approximate documented acceleration and gravity; they omit
enemyAI, combat and the full game collision engine. The official recorded checker
answered300/300 observations within50ms in the1CPU/512MB Linux sandbox; p9912.7ms,
max15.2ms,ready669ms in the final run. A separate public-map stress test forced
15 attackers around each of74 roofs: worst34.30ms wall/34.26ms CPU after fixing
an initial143.54ms outlier. These are latency measurements, not gameplay scores.
Soft geometry-work budgets return unknown LOS when exhausted: unknown cover is
treated as exposed and never authorizes shooting. Targeting receives a separate
work slice after movement. Results remain machine-dependent.

MIT licensed. The protocol wrapper derives from the official starter and was
changed to fail on initialization errors. Bot/navigation/roof code was built
with AI assistance during the event. Official kit and rulebook:
https://www.joinbuilders.org/buildathon/tracks/builders .
