"""
Generate top 5 Argentine Spanish-language songs per year (1970-2026).
Uses Claude API to generate song lists, then youtube-search-python for videoIds.
Saves checkpoint every 50 songs. Can resume from last checkpoint.
"""
import json
import time
from pathlib import Path

from anthropic import Anthropic
from youtubesearchpython import VideosSearch
from tqdm import tqdm

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "canciones_ar.json"
CHECKPOINT_FILE = Path(__file__).parent.parent / "data" / "canciones_ar_checkpoint.json"
START_YEAR = 1970
END_YEAR = 2026
SONGS_PER_YEAR = 5


def generate_song_list() -> list[dict]:
    """Use Claude API to generate Argentine song lists by decade chunks."""
    client = Anthropic()
    all_songs = []

    # Process in decade chunks to stay within context limits
    decade_ranges = []
    for start in range(START_YEAR, END_YEAR + 1, 10):
        end = min(start + 9, END_YEAR)
        decade_ranges.append((start, end))

    for start, end in tqdm(decade_ranges, desc="Generating song lists"):
        prompt = f"""Generate a JSON array of the top {SONGS_PER_YEAR} most popular/iconic songs
PER YEAR in Argentina from {start} to {end}.

STRICT RULES:
- ONLY songs in Spanish language
- ONLY Argentine artists or bands
- Include folk, rock nacional, tango, cumbia, pop, trap/urban as appropriate per era
- No international artists, even if popular in Argentina

Return ONLY a valid JSON array with this schema, no other text:
[{{"title": "string", "artist": "string", "year": number}}]

Return {SONGS_PER_YEAR} songs for EACH year from {start} to {end} inclusive."""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text
        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
        songs = json.loads(text.strip())
        all_songs.extend(songs)
        time.sleep(1)  # Rate limiting

    return all_songs


def find_video_id(title: str, artist: str) -> str | None:
    """Search YouTube for a song and return the first videoId."""
    query = f"{title} {artist} official"
    try:
        search = VideosSearch(query, limit=1)
        results = search.result()
        if results["result"]:
            return results["result"][0]["id"]
    except Exception as e:
        print(f"  YouTube search failed for '{title}' by {artist}: {e}")
    return None


def load_checkpoint() -> list[dict]:
    """Load songs from checkpoint file if it exists."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_checkpoint(songs: list[dict]) -> None:
    """Save current progress to checkpoint file."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)


def main():
    # Step 1: Generate or load song list
    checkpoint = load_checkpoint()
    if checkpoint:
        print(f"Resuming from checkpoint: {len(checkpoint)} songs loaded")
        songs_without_ids = [s for s in checkpoint if not s.get("videoId")]
        if songs_without_ids:
            all_songs = checkpoint
        else:
            print("All songs already have videoIds. Saving final output.")
            save_final(checkpoint)
            return
    else:
        print("Generating Argentine song lists via Claude API...")
        raw_songs = generate_song_list()
        all_songs = raw_songs
        save_checkpoint(all_songs)
        print(f"Generated {len(all_songs)} songs. Checkpoint saved.")

    # Step 2: Find YouTube videoIds for songs missing them
    missing = [s for s in all_songs if not s.get("videoId")]
    print(f"\nSearching YouTube videoIds for {len(missing)} songs...")

    for i, song in enumerate(tqdm(missing, desc="Finding videoIds")):
        video_id = find_video_id(song["title"], song["artist"])
        song["videoId"] = video_id
        if video_id is None:
            print(f"  NOT FOUND: {song['title']} - {song['artist']}")

        # Checkpoint every 50 songs
        if (i + 1) % 50 == 0:
            save_checkpoint(all_songs)

        time.sleep(1)  # Rate limiting

    save_checkpoint(all_songs)
    save_final(all_songs)


def save_final(songs: list[dict]) -> None:
    """Save final output, filtering out songs without videoIds."""
    valid = [s for s in songs if s.get("videoId")]
    failed = [s for s in songs if not s.get("videoId")]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(valid, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(valid)} songs saved to {OUTPUT_FILE}")
    if failed:
        print(f"WARNING: {len(failed)} songs without videoId (skipped):")
        for s in failed:
            print(f"  - {s['title']} by {s['artist']} ({s['year']})")


if __name__ == "__main__":
    main()
