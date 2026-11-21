# Snowy Artillery v7

An independent mortar-counter-brawler hypothesis derived from Assault v5
(official practice placement4.00). Artillery v7 gameplay strength is unmeasured.

Official rules make mortar a lightning counter: a direct hit deals200 damage
plus160 splash, with energy drain up to45 and knockback. It costs no firing
energy and can strike beyond lightning's45m default range. The hypothesis is
that these effects and splash against a coordinated squad outweigh slower shell
travel and aiming risk.

Behavior changes:

- Prefer mortar pickups, retaining the gun; orbit approximately92m away instead
  of v5's58m mortar standoff. Prioritize mortar cooldown and splash upgrades.
- Solve a constant-velocity ballistic interception quartic numerically using
  the published speed, gravity, muzzle height and actual upgraded weapon stats.
  Target the lower body to retain a ground-splash opportunity on a near miss.
- Test short chords along the curved shell flight. A tracked enemy behind low
  cover remains a mortar candidate when the shell trajectory is clear. Direct
  gunfire requires a clear direct ray. Unknown clearance never authorizes fire.
- Allow aiming shortly before mortar cooldown ends and use a conservative
  fraction of splash radius for firing tolerance.
- Preserve v5 behavior without a mortar. Retain its ground navigation with soft
  CPU work limits and conservative handling of unknown geometry. No roof policy
  or v6 wider Lightning orbit is included.

Validation:11 tests cover analytic stationary/moving ballistic intersections,
unreachable/pitch-limited shots, low-wall arcs, unknown clearance, blocked gunfire,
mortar standoff, upgrades and safe weapon swaps. Official recorded checker:
300/300timely,0late/stale/bad/wrong-tick actions, p9912.0ms,max35.0ms. Direct
recorded300-observation computation reached13.06ms CPU/wall. A separate public
map32-ground-pose/15-foe stress test reached10.88ms CPU/wall and24.6MiB peak RSS.
These measurements validate protocol and latency, not responsive gameplay.

Limitations: constant-velocity prediction misses turns and collisions; the
low/earliest arc cannot clear every building; geometric chord/map tests remain
approximate. The protocol does not specify a separate mortar spawn-height
offset, so this bot uses the documented upgraded muzzle height. Gun and mortar
often need different pitch, limiting simultaneous fire. Wider standoff can
delay cube pickup. The final free-for-all differs from the practice squad.
Only official scoring can establish whether this experiment improves placement.

Publish eight files at repository root: Dockerfile,.dockerignore,bot.py,
navigation.py,ballistics.py,mechfight.py,README.md,LICENSE. Standard library only;
no package installation or arena data in the image. Scorer supplies /arena.

MIT licensed. Wrapper derives from the organizer kit with fail-fast startup;
our bot/navigation/ballistics code was built with AI assistance during the event.
Official rules and starter kit:
https://www.joinbuilders.org/buildathon/tracks/builders .
