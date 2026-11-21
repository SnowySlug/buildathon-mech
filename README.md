# Snowy Assault v5

Offensive/resource-snowball experiment for Mech Royale. It uses the best v1
ground map/pathfinding code without rooftop behavior or the v2 stronger-retreat
policy. Gameplay improvement requires official practice scoring.

The hypothesis is that the coordinated practice house bots rarely eliminate
each other, so survival alone is insufficient: favorable early eliminations
must turn into cube, damage, health and upgrade advantages.

Behavior:

- Seek nearby secondary weapons and remember previously seen stationary loot.
  Prefer lightning, including swaps that preserve the gun.
- Commit to collecting nearby dropped cubes; approach isolated farm targets
  rather than destroying them at range and abandoning their rewards.
- Focus finishable pursuers. Against a small group, orbit around34m with
  lightning or76m with only the gun. Increase distance when surrounded.
- Fire compatible gun and lightning shots together; retain lightning firing
  energy instead of spending it all on boost during an in-range duel.
- Prioritize offensive upgrades. Healing is an explicit disengagement mode;
  taking damage interrupts it and restores defense.
- Zone urgency overrides resource collection and combat positioning.

The idealized weapon arithmetic in `weapon_model.py` is NOT a match simulator.
With perfect hits on one unarmored1400HP target, default gun-only kill time is
11.76–12.24s depending on empty-mag reload event ordering; gun+lightning reaches
it at3.50s using45lightningenergy. Two cubes plus one15%gun-damage upgrade reaches
it at2.75s in that same idealization. Continuous boosting plus15arcshots during
3.5s would cost104.5energy, exceeding the initial100: conserving duel energy is
therefore an explicit policy. Real aim, cover, armor, movement, multiple enemies,
loot access and damage timing are excluded from that model.

Risks: closing distance can expose the mech to several coordinated shooters;
loot pursuit can waste time or reveal position; NPC farming is not placement
reward by itself; stationary loot may be taken by another mech; lightning drains
energy and benefits from range/chain geometry. The final has competing-team
free-for-all opponents, not the practice squad. No strength claim is inferred
from conformance or ideal weapon arithmetic.

Validation:10 tests pass, including focus selection, simultaneous gun+lightning,
duel energy conservation, damage interrupting healing and safe secondary swaps.
The official recorded checker passed300/300 observations with0late/stale/bad
actions,ready1152ms,p9914.4ms,max24.0ms in the1CPU/512MB offline read-only Linux
sandbox. Results depend on machine load and do not measure placement.

Publish these seven files at repository root: Dockerfile,.dockerignore,bot.py,
navigation.py,mechfight.py,README.md,LICENSE. No arena data or package installs
are required in the image; the scorer mounts /arena.

MIT licensed. The wrapper derives from the organizer kit with fail-fast
initialization. Our bot/navigation/strategy code was built with AI assistance
during the event. Official protocol/map/checker:
https://www.joinbuilders.org/buildathon/tracks/builders .
