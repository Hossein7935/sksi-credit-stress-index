"""Print the latest published reading. Use `python -m sksi.update` to refresh."""

import json
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "data" / "latest.json"
if not path.exists():
    raise SystemExit("data/latest.json fehlt. Erst `python -m sksi.update` ausführen.")
latest = json.loads(path.read_text())
print(f"{latest['date']}  SKSI {latest['score']:.1f}  {latest['regime']}  quorum={str(latest['quorum']).lower()}")
print(latest["summary"])
for key, comp in latest["components"].items():
    print(f"  {key:5} {comp['value']:8.3f}  z {comp['z']:+6.2f}  {comp['state']}")
