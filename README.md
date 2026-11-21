# Snowy Hybrid v6

An offensive Mech Royale experiment derived from Snowy Assault v5. V5 received
4.00 official practice placement points. V6 has no measured gameplay score yet.

The hypothesis is that a lightning/gun hybrid should use its range upgrades,
align both weapons with one compatible aim, and preserve energy for arc shots.
The official protocol gives lightning45m range, a30-degree yaw cone,3energy
per shot and a0.25s cooldown; weapon stats include applied upgrades.

Changes from V5:

- Use90% of current lightning range, capped4m inside its boundary, rather than
  keeping a fixed34m orbit after range upgrades. With54m range this gives48.6m,
  beyond a default45m enemy arc. With depleted energy use gun standoff unless
  finishing a weak enemy.
- Lead the gun while firing lightning. The arc checks the current target yaw
  independently, allowing both weapons against transverse moving targets.
- Preserve arc energy while approaching resources as well as during a duel.
- Count nearby tracked enemies as crossfire threats when their incoming line
  of sight is clear or unknown. Known occluded enemies do not force the90m
  crowd-retreat distance merely because the protocol tracks them behind cover.
- Apply soft CPU deadlines to legacy navigation and geometric checks. Budget
  exhaustion produces unknown line of sight: it authorizes neither firing nor
  claims of safe cover. A* returns its best partial route. The map/path/ray
  algorithms otherwise remain those of V5. Collect cyclic garbage during
  initialization, leaving acyclic runtime data to reference counting.

Validation:17 local tests pass. The official recorded checker passed300
observations:299timely,1late, no stale/wrong-tick/bad actions; p9928.6ms,
max77.5ms. The checker and bot share the same one-CPU container. Direct bot
computation on those300 recorded observations reached3.29ms CPU/3.29ms wall.
A separate32-ground-pose test with15 tracked enemies reached26.88ms CPU,
26.91ms wall and24.7MiB peak RSS after bounding work (previously152ms CPU).
These are conformance and latency measurements, not reactive gameplay tests.

Risks: wider orbit can reduce arc uptime; enemy upgrades are not fully visible;
an occluded enemy can emerge quickly; budget exhaustion can miss a firing or
movement opportunity. The legacy geometry remains approximate. Final opponents
are competing bots rather than the coordinated practice house squad. Only an
official evaluation can establish whether V6 improves placement.

Publish these seven files at repository root: Dockerfile,.dockerignore,bot.py,
navigation.py,mechfight.py,README.md,LICENSE. No package installs or arena data
are required in the image; the scorer mounts /arena. Runtime is unprivileged,
offline, read-only Linux/amd64 with1CPU,512MiB RAM and64MiB temporary space.

MIT licensed. The protocol wrapper derives from the organizer kit with
fail-fast initialization. Bot/navigation code was built with AI assistance
during the event. Official protocol/map/checker:
https://www.joinbuilders.org/buildathon/tracks/builders .
