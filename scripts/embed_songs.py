"""
Reads songs_final.json and generates a JS const to paste into index.html.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
SONGS_FILE = ROOT / "data" / "songs_final.json"
OUTPUT_FILE = ROOT / "data" / "songs_embedded.js"

with open(SONGS_FILE, "r", encoding="utf-8") as f:
    songs = json.load(f)

# Generate compact JS
js = "const SONGS = " + json.dumps(songs, ensure_ascii=False, separators=(",", ":")) + ";"

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(js)

print(f"Generated {OUTPUT_FILE} ({len(songs)} songs, {len(js)} bytes)")
print("Paste this into index.html replacing the SONGS placeholder.")
