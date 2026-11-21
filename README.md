# Snowy Escape v2

Separate survival experiment after the first official v1 score of2.69.
No claim of improvement until the official 48-match evaluation.

Changes: route cost avoids the nearest five observed threats; stronger local
retreat and boost at180m; intentionally waiting no longer triggers stuck/jet
recovery; target persistence; compatible arm-gun fire while laser charges;
prefer laser/lightning rather than mortar; reduced noisy crate farming and
isolated-drone farming outside its default aggro range.

Conformance uses the same official kit and exact1CPU/512MB sandbox:

```powershell
& ./.venv/Scripts/python.exe tracks/mech/versions/escape/check_entry.py
```

MIT License. Official wrapper derives from the organizer kit with initialization
failure made fatal. Bot/navigation code was built with AI assistance during the
event. Map/schema/checker source: https://www.joinbuilders.org/buildathon/tracks/builders .
The published repository must have these runtime files at its root: Dockerfile,
bot.py, navigation.py, mechfight.py, plus this README and LICENSE. No arena data
is required in the image; the scorer mounts /arena.
