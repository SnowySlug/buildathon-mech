# Snowy Provision v10

An opening-loadout experiment on Breaker v8 (official practice score 4.02).
V10 gameplay strength is unmeasured. V8 combat, burst and upgrade policies remain
the fallback after the short opening phase.

Verified restrictions in the earlier policy: with a pursuer tracked, the
weighted resource threshold limits Lightning pickup pursuit to under 100 m,
mortar to 64.3 m and laser to 52.9 m. With no enemies, a retreat fallback accepts
any safe secondary under 110 m. Both paths reject loot outside the next circle,
even early in the first 60-second hold. A tracked enemy takes priority over
NPC/crate farming. The firing policy ignores all NPCs within 48 m.

V10 changes:

- For the first 65 seconds, while healthy and without a secondary, prioritize
  observed/remembered ground weapons within 175 m. Prefer nearby Lightning but
  accept a closer useful alternative. Bounded boost reserves energy for combat.
- Allow loot within the current zone when a straight-line walking/escape-time
  estimate plus margin fits the next shrink deadline. Check enemy clearance at
  the destination; abandon this phase for immediate or finishable threats,
  crowding, healing, poor health or zone urgency.
- When no useful weapon is known and player threats are distant, approach a
  nearby ground crate or NPC and give that farm target firing priority. Resume
  player defense against immediate/finishable enemies.
- Permit firing at nearby NPCs, including the previously excluded 0–48 m band.

The official default gun ideally destroys a 300 HP crate in seven shots over
1.44 seconds, or a 350 HP NPC in eight shots over 1.68 seconds, before aiming,
travel and reload costs. Crates drop one cube and have 50% weapon-drop chance;
NPCs drop two cubes. Two cubes give 8% max HP/damage before the cap and unlock
the first upgrade. These are arithmetic opportunities, not guaranteed outcomes.

Validation: 25 tests pass. The official recorded checker passed 300/300
observations with zero late, stale, wrong-tick or malformed actions; p99 8.3 ms,
maximum 16.4 ms. Direct computation on those observations reached 2.43 ms CPU
and wall. A 96-case public-map stress test combines 64 crowded combat cases and
32 gun-only opening cases containing up to 40 pickups, 36 crates and 12 NPCs:
maximum 19.75 ms CPU, 19.79 ms wall, 24.9 MiB peak RSS.

A synthetic grid of three weapon kinds at 60/90/120/150/170 m measures goal
arbitration. With one stationary pursuer 130 m opposite the loot, V8 selects
three of fifteen pickup goals and V10 selects fifteen. Without a pursuer,
the counts are six and fifteen. The grid assumes reachable ground pickups and
clear rays; it excludes actual navigation, interception, damage, pickup/equip
success and opponents responding. It does not measure acquisition frequency
or predict score. The small official V8 improvement does not establish whether
loadout scarcity, rare burst eligibility or combat tradeoffs caused the result.

Risks: detours can consume critical time, routes can exceed straight-line
estimates, remembered loot can be taken, farming reveals position and can turn
rear armor toward distant attackers. Secondary equip delay also limits immediate
benefit. Static geometry remains approximate and CPU work guards can truncate
planning. Reactive official matches are required to measure strength.

Publish seven files at repository root: Dockerfile, .dockerignore, bot.py,
navigation.py, mechfight.py, README.md, LICENSE. Standard library only; the scorer
mounts arena data. MIT licensed. The wrapper derives from the organizer kit with
fail-fast initialization; our code was built with AI assistance during the event.
Official rules and starter: https://www.joinbuilders.org/buildathon/tracks/builders .
