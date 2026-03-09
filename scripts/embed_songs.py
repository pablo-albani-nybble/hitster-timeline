"""
Reads songs_full.json and songs_light.json and generates a single JS file
with both datasets to embed into index.html.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
FULL_FILE = ROOT / "data" / "songs_full.json"
LIGHT_FILE = ROOT / "data" / "songs_light.json"
OUTPUT_FILE = ROOT / "data" / "songs_embedded.js"

full = json.load(open(FULL_FILE, "r", encoding="utf-8"))
light = json.load(open(LIGHT_FILE, "r", encoding="utf-8"))

compact = json.dumps
opts = {"ensure_ascii": False, "separators": (",", ":")}

js = (
    f"const SONGS_FULL = {compact(full, **opts)};\n"
    f"const SONGS_LIGHT = {compact(light, **opts)};\n"
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(js)

print(f"Generated {OUTPUT_FILE}")
print(f"  Full:  {len(full)} songs ({len(compact(full, **opts))} bytes)")
print(f"  Light: {len(light)} songs ({len(compact(light, **opts))} bytes)")
print(f"  Total: {len(js)} bytes")
print("Paste this into index.html replacing the SONGS_FULL and SONGS_LIGHT placeholders.")
