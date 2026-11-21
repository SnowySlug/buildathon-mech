# Mech Royale — Snowy Survivor

Placement-focused standard-library Python bot. It uses the published terrain and
prism map for bounded A* navigation, plans toward the next zone, avoids visible
threats and projectiles, seeks safe nearby loot, picks survival upgrades, and
leads projectile shots while checking actual torso alignment and line of sight.
Laser, mortar, lightning, reload and upgrade actions use the live configuration.

This is a ready-to-score entry, not a proven improvement over the starter.
The official check replays recorded observations and cannot measure gameplay.

From the main workspace on Windows:

```powershell
& ./.venv/Scripts/python.exe tracks/mech/check_entry.py
& ./.venv/Scripts/python.exe -m unittest discover -s tracks/mech/tests -v
```

The helper runs the official checker **inside** the restricted Linux container.
Running it on Windows with `--map-dir /arena` converts the hello path to
`C:\arena`; a Linux bot then cannot load that map. The upstream wrapper catches
initialization errors and can otherwise pass as an idle bot. Our wrapper exits
on initialization failure, and the helper checks the actual bot name and stderr.

Runtime files: Dockerfile, bot.py, navigation.py, mechfight.py. The arena is
mounted at /arena by the match; it is not embedded in the image. The pinned
official Python3.13 base requires no extra dependency downloads.

## Sources and disclosure

Official kit and rules: https://www.joinbuilders.org/buildathon/tracks/builders

`official/mechfight-kit/` is the organizer-provided starter, schema, recorded
checker and map. `mechfight.py` derives from the official Python wrapper, with
fail-fast initialization added. Navigation and decision logic were written with
AI assistance during the event. The source is MIT licensed; upstream material
retains its original terms.

Submission rules verified: own-team public GitHub repository with root Dockerfile,
at most20MB; linux/amd64; build under10minutes; runtime1CPU/512MB, no network,
read-only except64MB /tmp, uid65534;50ms decisions. Four submissions/hour.
Practice48matches against15 coordinated house bots. Final qualifying/final
matches use competing teams, so practice strength does not prove final strength.
