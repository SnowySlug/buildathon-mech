# Snowy Trigger v11

A gun-trigger experiment on Breaker v8 (official practice placement score 4.02).
V11 gameplay strength is unmeasured. Opening, navigation, targets, burst policy
and upgrade selection remain those of V8.

The old gun gate compares the last observed actual torso aim with the newly
computed intercept. For a continuously transverse target, the observation-to-
command angular shift is approximately relative speed times 0.1 s divided by
range. The target tolerance is approximately 0.8 times its radius divided by
range. With default radius 2.5 m, the old gate can therefore reject tracking
above about 20 m/s relative transverse speed even when torso rotation is fast
enough. Two actors walking oppositely at 11.7 m/s can exceed that threshold.

V11 retains the old authorization and additionally allows gun triggering when
the torso can align after one 0.05 s physics tick toward the actual commanded
aim. It uses current upgraded yaw/pitch slew rates and pitch limits, including
shortest-path yaw wrapping. The extension applies during gun/Lightning aiming;
laser release and mortar aiming retain their old actual-aim checks. Existing
range and line-of-sight requirements remain. Unknown clearance does not
authorize firing.

The protocol documents 10 Hz decisions, actions held over two 20 Hz physics
ticks, actual-aim shots and bounded torso slew. It does not specify whether
firing occurs before or after slew inside each physics tick. The test therefore
evaluates both assumptions rather than claiming an engine ordering.

A 10-second actuator probe uses two opposite circular actors with legal walking
speeds of 11.7 m/s each, separated by 100 m, and continuously recomputes ideal
intercept. V8 requests the gun on 2 of 200 physics ticks; V11 requests it on
200. Angularly aligned requested ticks increase from 2 to 101 under fire-before-
slew, or from 2 to 200 under slew-before-fire. Slow relative motion is unchanged.
The probe also covers 50/180 m separation and faster instantaneous movement.
It excludes cooldown, reload, energy, spread, obstacles, damage and actual
projectile hits. These are trigger/angular opportunities, not bullets, hits,
DPS or placement. The fast-movement case does not model sustained boost energy.

Validation: 22 tests pass. The official recorded checker passes 300/300
observations with zero late, stale, wrong-tick or malformed actions; p99
12.8 ms, maximum 38.0 ms. Direct recorded computation reaches 3.52 ms CPU/wall.
A 64-case public-map stress test with 15 tracked enemies reaches 9.88 ms
CPU/wall and 24.7 MiB peak RSS in the one-CPU/512 MiB offline sandbox.

Risks: initial slew shots can waste ammunition if firing precedes rotation;
future target movement and existing constant-velocity lead remain approximate.
Lightning-centered aim can still conflict with the gun's lead at high target
speed. More successful hits can delay damage-based healing. Only reactive
official evaluation can establish whether this change improves placement.

Publish seven files at repository root: Dockerfile, .dockerignore, bot.py,
navigation.py, mechfight.py, README.md, LICENSE. Standard library only; scorer
mounts arena data. MIT licensed. The wrapper derives from the organizer kit
with fail-fast initialization; our code was built with AI assistance during the
event. Official protocol: https://www.joinbuilders.org/buildathon/tracks/builders .
