# Snowy Economy v9

An isolated upgrade-policy experiment on Assault v5, whose official practice
score is 4.00 placement points. V9 gameplay strength is unmeasured. V5 combat
ranges, target scoring, weapon preference, loot policy and movement strategy
are retained; this version does not include V8 burst behavior.

Upgrade changes:

- Prefer Lightning efficiency while holding Lightning. Each stack adds 10%
  damage and reduces shot energy by 35%, improving damage per energy by 69.23%.
- Prefer the first drum magazine over range or gun damage when its sustained
  throughput gain exceeds 15%. Recompute using current gun stats; subsequent
  drums can lose priority to a 15% gun damage upgrade.
- Give low-HP repair nanites their emergency preference during explicit healing
  mode. Continuous combat prevents regeneration from starting.
- Deprioritize pending weapon-specific choices for weapons no longer held.

Published-stat arithmetic, before cubes/armor:

| Lightning efficiency stacks | Energy/shot | Damage/shot | Shots per full 100 energy |
| --- | ---: | ---: | ---: |
| 0 | 3 | 60 | 33 |
| 1 | 1.95 | 66 | 51 |
| 2 | 1.2675 | 72.6 | 78 |

The first drum changes 12 rounds / 2.4 s reload into 20 rounds / 1.92 s reload:
ideal sustained gun DPS rises approximately 29.6–31.0% across two reload-order
bounds. The second drum's marginal gain is approximately 13.2–14.0%, below a
15% damage upgrade. Actual stats drive this comparison.

Two collected cubes grant 8% max HP and damage before the cap (1512 max HP from
1400), plus the first upgrade offer. Three and six cubes unlock the second and
third offers. Cubes also increase physical size; more HP does not imply that
collection is always safe. The model never assumes max-HP or max-energy upgrades
immediately refill current values.

An ideal three-target sequence includes perfect hits on three stationary,
unarmored 1400 HP targets and immediate target switching. With ideal energy
recovery after spending pauses, the third kill occurs at 15.61–16.08 s with no
efficiency and 11.25–11.50 s with one efficiency stack. It excludes incoming
damage, movement, misses, cover, cubes, opportunity cost and actual decision
timing. A separate no-energy-recovery bound is also recorded. These are
arithmetic comparisons, not a match simulator or placement prediction.

Validation: 14 tests pass. The official recorded checker passed 300/300
observations with zero late, malformed, stale or wrong-tick actions; p99
15.2 ms, maximum 18.4 ms. Direct recorded computation reached 18.22 ms CPU/wall.
A 64-case public-map stress test with 15 tracked enemies reached 10.61 ms
CPU/wall and 24.6 MiB peak RSS. The V5 geometric algorithms include previously
tested soft work limits; unknown clearance permits neither shooting nor claims
of cover. Startup collects garbage before acyclic runtime processing.

Risks: actual fights may favor immediate first-kill damage, range or defensive
upgrades; random offers can limit policy impact; Lightning may be unavailable.
Runtime guards can truncate planning. Only official evaluation can establish
whether this policy improves placement.

Publish seven files at repository root: Dockerfile, .dockerignore, bot.py,
navigation.py, mechfight.py, README.md, LICENSE. Standard library only; the
scorer mounts arena data. MIT licensed. The wrapper derives from the organizer
kit with fail-fast startup; our code was built with AI assistance during the
event. Official rules and starter: https://www.joinbuilders.org/buildathon/tracks/builders .
