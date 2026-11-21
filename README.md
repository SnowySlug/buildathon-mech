# Snowy Breaker v8

A focused Lightning burst experiment derived from Assault v5, whose official
practice score is 4.00 placement points. V8 gameplay strength is unmeasured.

V5 switches to a 90 m combat distance whenever three enemies are within 145 m.
That disables its default 45 m Lightning. Its local movement scoring also
penalizes approaching every enemy, opposing the desired combat distance. A
cluster directly ahead can offer chain damage while fitting inside front armor;
it is different from being surrounded.

V8 starts a four-second focused burst when it has sufficient HP and energy,
the target is within 110 m, and nearby threats fit conservatively inside the
target-facing front arc. With three or more nearby enemies, at least two must
be within the target's Lightning chain range. During that burst it aims for
26 m, reduces contradictory generic proximity repulsion, and permits the
committed approach despite enemy Lightning. Walls, zone and projectile checks
remain active. It keeps focus, conserves in-range firing energy and avoids
periodic discretionary jumps. Critical health, depleted energy, target loss,
expiry or unsafe geometry cancels the commitment. The usual V5 behavior remains
available outside a qualified burst. Upgrade priorities are unchanged.

The published default arc does 60 damage every 0.25 s for 3 energy. Two full
chain jumps can add 42 and 29.4 damage, giving an ideal maximum of 525.6 total
arc DPS across three targets, before cubes and armor. Gun plus Lightning needs
3.5 s and 45 arc energy for one perfect-hit unarmored 1400 HP kill in the
existing ideal model. Two dropped cubes add 8% max HP and damage before the cap
and can unlock upgrades. These arithmetic bounds exclude misses, movement,
incoming damage, armor and cover; they do not predict placement.

Validation:

- 15 tests pass, including clustered versus surrounded/spread squads, energy
  reserves, continued spending during a burst, focus, cancellation, combined
  weapons and safe pickup swaps.
- The official recorded checker passed 300/300 observations with zero late,
  stale, wrong-tick or malformed actions; p99 11.6 ms, maximum 24.2 ms.
- Direct recorded-observation computation: maximum 16.01 ms CPU, 16.30 ms wall.
- A 64-case public-map stress test with 15 tracked enemies in ring and forward
  cluster layouts: maximum 8.97 ms CPU, 10.76 ms wall, 24.6 MiB peak RSS.
- A separate 12-second horizontal opportunity probe holds three enemy HP and
  positions fixed on an empty floor. V5 spends zero seconds in arc range and
  produces zero arc trigger opportunities. V8 spends 8.15 seconds in range and
  produces 31 opportunities, reaching 28.88 m separation. The frozen enemies
  never attack, move or die; vertical movement, cover, misses and armor are
  excluded. This demonstrates the intended policy change, not a combat win.

The V5 ground algorithms include soft CPU work limits. Unknown ray clearance
never authorizes fire or establishes cover. Approximate map geometry and
constant-velocity gun lead remain limitations. Committing at short range can
lose a damage race, especially against multiple Lightning carriers or mortars;
chain hits depend on actual target ordering. Official evaluation is required.

Publish seven files at repository root: Dockerfile, .dockerignore, bot.py,
navigation.py, mechfight.py, README.md, LICENSE. Standard library only; arena
data are mounted by the scorer. MIT licensed. The wrapper derives from the
organizer kit with fail-fast initialization; our code was built with AI
assistance during the event. Official rules and kit:
https://www.joinbuilders.org/buildathon/tracks/builders .
