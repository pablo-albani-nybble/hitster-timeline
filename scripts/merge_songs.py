"""
Merge global songs with Argentine songs. Produces two outputs:
  - data/songs_full.json  (canciones.json + AR)
  - data/songs_light.json (canciones-light.json + AR)

Normalizes Spanish keys (titulo/artista/anio) to English (title/artist/year).
Deduplicates by title+artist (case-insensitive), assigns unique IDs, adds region field.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
FULL_FILE = ROOT / "canciones.json"
LIGHT_FILE = ROOT / "canciones-light.json"
AR_FILE = ROOT / "data" / "canciones_ar.json"


def normalize_key(title: str, artist: str) -> str:
    """Create a dedup key from title + artist."""
    return f"{title.strip().lower()}|{artist.strip().lower()}"


def normalize_song(song: dict) -> dict:
    """Normalize Spanish keys to English keys."""
    return {
        "title": song.get("title") or song.get("titulo", ""),
        "artist": song.get("artist") or song.get("artista", ""),
        "year": song.get("year") or song.get("anio", 0),
        "videoId": song.get("videoId", ""),
        "region": song.get("region", "global"),
    }


def merge(global_songs: list[dict], ar_songs: list[dict]) -> list[dict]:
    """Merge global + AR songs, deduplicate, sort, assign IDs."""
    seen = set()
    merged = []

    for song in global_songs:
        norm = normalize_song(song)
        norm["region"] = "global"
        key = normalize_key(norm["title"], norm["artist"])
        if key not in seen:
            seen.add(key)
            merged.append(norm)

    dupes = 0
    for song in ar_songs:
        norm = normalize_song(song)
        norm["region"] = "ar"
        key = normalize_key(norm["title"], norm["artist"])
        if key not in seen:
            seen.add(key)
            merged.append(norm)
        else:
            dupes += 1

    # Sort by year, then title
    merged.sort(key=lambda s: (s["year"], s["title"]))

    # Assign sequential IDs
    for i, song in enumerate(merged, start=1):
        song["id"] = i

    return merged, dupes


def load_json(path: Path) -> list[dict]:
    """Load a JSON file, return empty list if not found."""
    if not path.exists():
        print(f"  (not found: {path.name}, skipping)")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} songs from {path.name}")
    return data


def save_json(data: list[dict], path: Path) -> None:
    """Save data to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    # Load Argentine songs (optional - may not exist yet)
    print("Loading Argentine songs...")
    ar_songs = load_json(AR_FILE)

    # Process FULL version
    print("\n--- FULL version ---")
    full_global = load_json(FULL_FILE)
    full_merged, full_dupes = merge(full_global, ar_songs)
    output_full = ROOT / "data" / "songs_full.json"
    save_json(full_merged, output_full)
    print(f"  Result: {len(full_merged)} songs ({full_dupes} duplicates removed)")
    print(f"  Saved to {output_full}")

    # Process LIGHT version
    print("\n--- LIGHT version ---")
    light_global = load_json(LIGHT_FILE)
    light_merged, light_dupes = merge(light_global, ar_songs)
    output_light = ROOT / "data" / "songs_light.json"
    save_json(light_merged, output_light)
    print(f"  Result: {len(light_merged)} songs ({light_dupes} duplicates removed)")
    print(f"  Saved to {output_light}")

    # Stats
    print("\n--- Summary ---")
    for label, data in [("Full", full_merged), ("Light", light_merged)]:
        regions = {}
        for s in data:
            r = s["region"]
            regions[r] = regions.get(r, 0) + 1
        region_str = ", ".join(f"{r}: {c}" for r, c in sorted(regions.items()))
        print(f"  {label}: {len(data)} songs ({region_str})")


if __name__ == "__main__":
    main()
