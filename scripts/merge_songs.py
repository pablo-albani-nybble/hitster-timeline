"""
Merge global songs (canciones.json) with Argentine songs (canciones_ar.json).
Deduplicates by title+artist (case-insensitive), assigns unique IDs, adds region field.
Output: data/songs_final.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
GLOBAL_FILE = ROOT / "canciones.json"
AR_FILE = ROOT / "data" / "canciones_ar.json"
OUTPUT_FILE = ROOT / "data" / "songs_final.json"


def normalize_key(title: str, artist: str) -> str:
    """Create a dedup key from title + artist."""
    return f"{title.strip().lower()}|{artist.strip().lower()}"


def main():
    # Load global songs
    with open(GLOBAL_FILE, "r", encoding="utf-8") as f:
        global_songs = json.load(f)
    print(f"Loaded {len(global_songs)} global songs")

    # Load Argentine songs
    with open(AR_FILE, "r", encoding="utf-8") as f:
        ar_songs = json.load(f)
    print(f"Loaded {len(ar_songs)} Argentine songs")

    # Tag regions
    for song in global_songs:
        song["region"] = song.get("region", "global")
    for song in ar_songs:
        song["region"] = "ar"

    # Deduplicate: global songs first, then add AR songs not already present
    seen = set()
    merged = []

    for song in global_songs:
        key = normalize_key(song["title"], song["artist"])
        if key not in seen:
            seen.add(key)
            merged.append(song)

    dupes = 0
    for song in ar_songs:
        key = normalize_key(song["title"], song["artist"])
        if key not in seen:
            seen.add(key)
            merged.append(song)
        else:
            dupes += 1

    # Sort by year, then title
    merged.sort(key=lambda s: (s["year"], s["title"]))

    # Assign sequential IDs after sort
    for i, song in enumerate(merged, start=1):
        song["id"] = i

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\nMerged: {len(merged)} unique songs ({dupes} duplicates removed)")
    print(f"Saved to {OUTPUT_FILE}")

    # Stats
    regions = {}
    for s in merged:
        r = s["region"]
        regions[r] = regions.get(r, 0) + 1
    for r, count in sorted(regions.items()):
        print(f"  {r}: {count} songs")


if __name__ == "__main__":
    main()
