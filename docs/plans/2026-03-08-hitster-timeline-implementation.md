# Hitster Timeline - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a single-file interactive musical board game web app where two teams compete by guessing songs and placing them in a timeline.

**Architecture:** Single `index.html` with embedded CSS, JS, and song data. Screens as `<section>` elements toggled via JS. YouTube IFrame API for audio, Web Audio API for SFX. Python scripts generate the song database from Claude API + YouTube search.

**Tech Stack:** HTML5, CSS3 (custom properties, animations), Vanilla JS (ES6+), YouTube IFrame API, Web Audio API, Python 3 (anthropic, youtubesearchpython, tqdm)

**Design doc:** `docs/plans/2026-03-08-hitster-timeline-design.md`

---

## Phase 1: Song Data Pipeline

### Task 1: Generate Argentine songs script

**Files:**
- Create: `scripts/generate_ar_songs.py`
- Create: `scripts/requirements.txt`

**Step 1: Create requirements.txt**

```
anthropic
youtube-search-python
tqdm
```

**Step 2: Write the generation script**

```python
"""
Generate top 5 Argentine Spanish-language songs per year (1970-2026).
Uses Claude API to generate song lists, then youtube-search-python for videoIds.
Saves checkpoint every 50 songs. Can resume from last checkpoint.
"""
import json
import os
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
        songs_with_ids = [s for s in checkpoint if s.get("videoId") is not None]
        songs_without_ids = [s for s in checkpoint if s.get("videoId") is None]
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
    missing = [s for s in all_songs if "videoId" not in s]
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
```

**Step 3: Install dependencies and run**

```bash
cd scripts
pip install -r requirements.txt
cd ..
python scripts/generate_ar_songs.py
```

Expected: `data/canciones_ar.json` created with ~285 songs.

**Step 4: Commit**

```bash
git add scripts/ data/canciones_ar.json
git commit -m "feat(data): add Argentine songs generation script"
```

---

### Task 2: Merge songs script

**Files:**
- Create: `scripts/merge_songs.py`
- Input: `canciones.json` (pre-existing, root), `data/canciones_ar.json` (from Task 1)
- Output: `data/songs_final.json`

**Step 1: Write the merge script**

```python
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

    # Assign sequential IDs
    for i, song in enumerate(merged, start=1):
        song["id"] = i

    # Sort by year for readability
    merged.sort(key=lambda s: (s["year"], s["title"]))

    # Re-assign IDs after sort
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
```

**Step 2: Run**

```bash
python scripts/merge_songs.py
```

Expected: `data/songs_final.json` with deduplicated, ID'd, region-tagged songs.

**Step 3: Commit**

```bash
git add scripts/merge_songs.py data/songs_final.json
git commit -m "feat(data): add song merge script with deduplication"
```

---

## Phase 2: HTML Foundation

### Task 3: HTML structure + CSS dark theme + screen navigation

**Files:**
- Create: `index.html`

This is the biggest task. It creates the full HTML skeleton with all 8 screens, complete CSS dark theme, and the screen navigation system.

**Step 1: Create index.html with full HTML + CSS + screen nav JS**

The file structure inside `index.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hitster Timeline</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
    <style>
        /* === CSS VARIABLES === */
        :root {
            --bg-primary: #0a0a0f;
            --bg-card: #1a1a2e;
            --bg-surface: #16213e;
            --accent-blue: #4361ee;
            --accent-purple: #7209b7;
            --accent-gold: #f4a261;
            --text-primary: #edf2f4;
            --text-muted: #8d99ae;
            --success: #06d6a0;
            --danger: #ef476f;
            --radius: 12px;
            --transition: 300ms ease;
        }

        /* === RESET & BASE === */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow: hidden;
        }

        /* === SCREEN SYSTEM === */
        .screen {
            display: none;
            position: absolute;
            inset: 0;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            opacity: 0;
            transition: opacity var(--transition);
        }
        .screen.active {
            display: flex;
            opacity: 1;
        }

        /* === BUTTONS === */
        .btn {
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            padding: 1rem 2rem;
            min-height: 60px;
            border: none;
            border-radius: var(--radius);
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            color: var(--text-primary);
        }
        .btn:hover {
            transform: scale(1.05);
        }
        .btn-primary { background: var(--accent-blue); }
        .btn-primary:hover { box-shadow: 0 0 20px rgba(67, 97, 238, 0.4); }
        .btn-purple { background: var(--accent-purple); }
        .btn-purple:hover { box-shadow: 0 0 20px rgba(114, 9, 183, 0.4); }
        .btn-success { background: var(--success); color: #0a0a0f; }
        .btn-danger { background: var(--danger); }
        .btn-gold { background: var(--accent-gold); color: #0a0a0f; }

        /* Shimmer effect for reveal buttons */
        .btn-reveal {
            background: linear-gradient(110deg, var(--accent-gold) 0%, #e76f51 25%, var(--accent-gold) 50%, #e76f51 75%, var(--accent-gold) 100%);
            background-size: 200% 100%;
            animation: shimmer 2s linear infinite;
            color: #0a0a0f;
            font-size: 1.3rem;
        }
        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        /* === TYPOGRAPHY === */
        h1 { font-size: 2.5rem; font-weight: 700; }
        h2 { font-size: 1.8rem; font-weight: 600; }
        .year-text { font-family: 'Space Grotesk', sans-serif; font-weight: 700; }

        /* === INPUTS === */
        .input {
            font-family: 'Inter', sans-serif;
            font-size: 1.2rem;
            padding: 0.8rem 1.2rem;
            background: var(--bg-surface);
            border: 2px solid var(--bg-card);
            border-radius: var(--radius);
            color: var(--text-primary);
            outline: none;
            transition: border-color var(--transition);
            width: 100%;
            max-width: 400px;
        }
        .input:focus { border-color: var(--accent-blue); }

        /* === SETUP SCREEN === */
        #screen-setup {
            gap: 2rem;
        }
        .setup-logo { font-size: 3.5rem; font-weight: 700; letter-spacing: -2px; }
        .setup-logo span { color: var(--accent-gold); }
        .setup-teams {
            display: flex;
            gap: 3rem;
            align-items: flex-start;
        }
        .setup-team {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.8rem;
        }
        .setup-team-label {
            font-size: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        .team-a-color { color: var(--accent-blue); }
        .team-b-color { color: var(--accent-purple); }

        /* === BOARD SCREEN === */
        #screen-board {
            justify-content: space-between;
            padding: 1.5rem 2rem;
        }
        .board-team-section {
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }
        .board-team-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            width: 100%;
            justify-content: center;
        }
        .board-team-name { font-size: 1.4rem; font-weight: 700; }
        .board-chips {
            display: flex;
            align-items: center;
            gap: 0.3rem;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.2rem;
            color: var(--accent-gold);
        }
        .timeline {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            justify-content: center;
            padding: 0.5rem;
            min-height: 70px;
        }
        .timeline-card {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
            padding: 0.6rem 1.2rem;
            background: var(--bg-card);
            border-radius: var(--radius);
            border: 2px solid;
            backdrop-filter: blur(10px);
        }
        .timeline-card.team-a { border-color: var(--accent-blue); }
        .timeline-card.team-b { border-color: var(--accent-purple); }
        .timeline-card.new-card {
            animation: slideIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        @keyframes slideIn {
            0% { transform: translateY(-30px) scale(0.8); opacity: 0; }
            100% { transform: translateY(0) scale(1); opacity: 1; }
        }
        .board-center {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }
        .turn-indicator {
            font-size: 1.2rem;
            font-weight: 600;
            padding: 0.5rem 1.5rem;
            border-radius: 50px;
        }
        .turn-a { background: rgba(67, 97, 238, 0.2); color: var(--accent-blue); }
        .turn-b { background: rgba(114, 9, 183, 0.2); color: var(--accent-purple); }
        .active-team-section {
            box-shadow: 0 0 30px rgba(67, 97, 238, 0.15);
            border-radius: var(--radius);
            padding: 1rem;
        }

        /* === PLAYING SCREEN (MODAL) === */
        #screen-playing {
            background: rgba(10, 10, 15, 0.97);
            z-index: 100;
            gap: 2rem;
        }
        .vinyl-container {
            position: relative;
            width: 250px;
            height: 250px;
        }
        .vinyl {
            width: 250px;
            height: 250px;
            border-radius: 50%;
            background: radial-gradient(circle at 50% 50%,
                #111 0%, #111 15%,
                #222 15%, #222 16%,
                #111 16%, #111 30%,
                #1a1a1a 30%, #1a1a1a 31%,
                #111 31%, #111 45%,
                #1a1a1a 45%, #1a1a1a 46%,
                #111 46%, #111 60%,
                #222 60%, #222 61%,
                #111 61%, #111 80%,
                #333 80%, #333 100%
            );
            box-shadow: 0 0 40px rgba(0,0,0,0.5);
            animation: spin 2s linear infinite;
        }
        .vinyl.paused { animation-play-state: paused; }
        .vinyl-label {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: var(--accent-gold);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        @keyframes spin {
            100% { transform: rotate(360deg); }
        }
        .countdown {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 4rem;
            font-weight: 700;
        }
        .countdown-ring {
            position: absolute;
            inset: -10px;
            border-radius: 50%;
            border: 4px solid transparent;
            border-top-color: var(--accent-gold);
            animation: none; /* controlled via JS */
        }

        /* === GUESS SCREEN === */
        #screen-guess {
            gap: 2rem;
        }
        .song-info {
            text-align: center;
            opacity: 0;
            transition: opacity 0.5s ease;
        }
        .song-info.visible { opacity: 1; }
        .song-title { font-size: 2rem; font-weight: 700; color: var(--accent-gold); }
        .song-artist { font-size: 1.5rem; color: var(--text-muted); margin-top: 0.3rem; }
        .guess-buttons {
            display: flex;
            gap: 1.5rem;
        }

        /* === PLACE SCREEN === */
        #screen-place {
            gap: 1.5rem;
        }
        .range-buttons {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            width: 100%;
            max-width: 500px;
        }

        /* === CHALLENGE SCREEN === */
        #screen-challenge {
            gap: 2rem;
        }
        .challenge-info {
            text-align: center;
            color: var(--text-muted);
            font-size: 1.1rem;
        }

        /* === REVEAL SCREEN === */
        #screen-reveal {
            gap: 2rem;
        }
        .reveal-year {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 8rem;
            font-weight: 700;
            color: var(--accent-gold);
            opacity: 0;
            transform: scale(0.5);
            transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .reveal-year.visible {
            opacity: 1;
            transform: scale(1);
        }
        .reveal-result {
            font-size: 1.5rem;
            font-weight: 600;
            text-align: center;
        }

        /* === VICTORY SCREEN === */
        #screen-victory {
            gap: 2rem;
            z-index: 200;
        }
        .victory-title {
            font-size: 3rem;
            font-weight: 700;
            text-align: center;
        }
        .confetti-container {
            position: fixed;
            inset: 0;
            pointer-events: none;
            overflow: hidden;
            z-index: 199;
        }
        .confetti {
            position: absolute;
            width: 10px;
            height: 10px;
            top: -10px;
            animation: confettiFall 3s ease-in forwards;
        }
        @keyframes confettiFall {
            0% { transform: translateY(0) rotate(0deg); opacity: 1; }
            100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
        }

        /* === HIDDEN YOUTUBE PLAYER === */
        #youtube-player {
            position: fixed;
            top: -9999px;
            left: -9999px;
            width: 1px;
            height: 1px;
            opacity: 0;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <!-- SETUP SCREEN -->
    <section id="screen-setup" class="screen active">
        <div class="setup-logo">Hitster <span>Timeline</span></div>
        <p style="color: var(--text-muted); font-size: 1.1rem;">Adivina la cancion. Ubica el ano. Gana la partida.</p>
        <div class="setup-teams">
            <div class="setup-team">
                <span class="setup-team-label team-a-color">Equipo A</span>
                <input type="text" class="input" id="team-a-name" placeholder="Nombre del equipo..." style="border-color: var(--accent-blue);">
            </div>
            <div class="setup-team">
                <span class="setup-team-label team-b-color">Equipo B</span>
                <input type="text" class="input" id="team-b-name" placeholder="Nombre del equipo..." style="border-color: var(--accent-purple);">
            </div>
        </div>
        <button class="btn btn-primary" onclick="startGame()" style="font-size: 1.3rem; padding: 1.2rem 3rem;">Comenzar Juego</button>
    </section>

    <!-- BOARD SCREEN -->
    <section id="screen-board" class="screen">
        <div class="board-team-section" id="board-team-a">
            <div class="board-team-header">
                <span class="board-team-name team-a-color" id="board-name-a">Equipo A</span>
                <span class="board-chips" id="board-chips-a">&#11044; 0</span>
            </div>
            <div class="timeline" id="timeline-a"></div>
        </div>
        <div class="board-center">
            <div class="turn-indicator" id="turn-indicator">Turno: Equipo A</div>
            <button class="btn btn-reveal" id="btn-play-song" onclick="playSong()" style="font-size: 1.5rem; padding: 1.5rem 3rem;">
                &#127925; Reproducir Cancion
            </button>
            <div style="color: var(--text-muted); font-size: 0.9rem;" id="song-counter">
                Canciones restantes: --
            </div>
        </div>
        <div class="board-team-section" id="board-team-b">
            <div class="board-team-header">
                <span class="board-team-name team-b-color" id="board-name-b">Equipo B</span>
                <span class="board-chips" id="board-chips-b">&#11044; 0</span>
            </div>
            <div class="timeline" id="timeline-b"></div>
        </div>
    </section>

    <!-- PLAYING SCREEN -->
    <section id="screen-playing" class="screen">
        <h2>Escuchen...</h2>
        <div class="vinyl-container">
            <div class="vinyl" id="vinyl"></div>
            <div class="vinyl-label">&#127926;</div>
        </div>
        <div class="countdown year-text" id="countdown">60</div>
        <button class="btn btn-gold" onclick="stopEarly()">&#9209; Ya la tenemos</button>
    </section>

    <!-- GUESS SCREEN -->
    <section id="screen-guess" class="screen">
        <h2>Adivinar Cancion y Artista</h2>
        <button class="btn btn-reveal" id="btn-reveal-song" onclick="revealSong()">Revelar Cancion / Artista</button>
        <div class="song-info" id="song-info">
            <div class="song-title" id="song-title"></div>
            <div class="song-artist" id="song-artist"></div>
        </div>
        <div class="guess-buttons" id="guess-buttons" style="display: none;">
            <button class="btn btn-success" onclick="guessResult(true)">&#9989; Acertaron! (+1 Ficha)</button>
            <button class="btn btn-danger" onclick="guessResult(false)">&#10060; Fallaron</button>
        </div>
    </section>

    <!-- PLACE SCREEN -->
    <section id="screen-place" class="screen">
        <h2 id="place-title">Ubicar en la Linea de Tiempo</h2>
        <p style="color: var(--text-muted);">Donde va esta cancion?</p>
        <div class="timeline" id="place-timeline"></div>
        <div class="range-buttons" id="range-buttons"></div>
    </section>

    <!-- CHALLENGE SCREEN -->
    <section id="screen-challenge" class="screen">
        <h2 id="challenge-title">Desafio!</h2>
        <p class="challenge-info" id="challenge-info"></p>
        <p style="color: var(--text-muted);" id="challenge-chosen-range"></p>
        <div class="range-buttons" id="challenge-range-buttons"></div>
        <button class="btn btn-primary" onclick="skipChallenge()">Sin Desafio &rarr;</button>
    </section>

    <!-- REVEAL SCREEN -->
    <section id="screen-reveal" class="screen">
        <h2>El ano de la cancion es...</h2>
        <div class="reveal-year year-text" id="reveal-year"></div>
        <button class="btn btn-reveal" id="btn-reveal-year" onclick="revealYear()">Revelar Ano</button>
        <div class="reveal-result" id="reveal-result" style="display: none;"></div>
        <button class="btn btn-primary" id="btn-next-turn" onclick="nextTurn()" style="display: none;">Siguiente Turno &rarr;</button>
    </section>

    <!-- VICTORY SCREEN -->
    <section id="screen-victory" class="screen">
        <div class="confetti-container" id="confetti-container"></div>
        <div class="victory-title" id="victory-title"></div>
        <button class="btn btn-gold" onclick="resetGame()" style="font-size: 1.3rem;">Jugar de Nuevo</button>
    </section>

    <!-- HIDDEN YOUTUBE PLAYER -->
    <div id="youtube-player"></div>

    <script>
    /* === SONG DATA (embedded from songs_final.json) === */
    const SONGS = []; // PLACEHOLDER: paste songs_final.json content here

    /* === GAME STATE === */
    let state = {
        teams: {
            a: { name: "Equipo A", timeline: [], chips: 0 },
            b: { name: "Equipo B", timeline: [], chips: 0 }
        },
        currentTurn: "a",
        usedSongIds: new Set(),
        currentSong: null,
        phase: "setup",
        winner: null,
        selectedRange: null,    // range chosen by active team
        challengerRange: null,  // range chosen by challenger
        isChallenge: false
    };

    /* === SCREEN NAVIGATION === */
    function showScreen(screenId) {
        document.querySelectorAll(".screen").forEach(s => {
            s.classList.remove("active");
        });
        const target = document.getElementById(`screen-${screenId}`);
        // Small delay for transition effect
        requestAnimationFrame(() => {
            target.classList.add("active");
        });
        state.phase = screenId;
    }

    /* === HELPER: Random year between min and max === */
    function randomYear(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    /* === HELPER: Get opponent team key === */
    function opponent(teamKey) {
        return teamKey === "a" ? "b" : "a";
    }

    /* === SETUP === */
    function startGame() {
        const nameA = document.getElementById("team-a-name").value.trim() || "Equipo A";
        const nameB = document.getElementById("team-b-name").value.trim() || "Equipo B";

        state.teams.a.name = nameA;
        state.teams.b.name = nameB;

        // Generate 2 random starting years per team
        state.teams.a.timeline = [randomYear(1900, 2024), randomYear(1900, 2024)].sort((a, b) => a - b);
        state.teams.b.timeline = [randomYear(1900, 2024), randomYear(1900, 2024)].sort((a, b) => a - b);

        state.teams.a.chips = 0;
        state.teams.b.chips = 0;
        state.currentTurn = "a";
        state.usedSongIds = new Set();
        state.winner = null;

        updateBoard();
        showScreen("board");
        sfx.vinylScratch();
    }

    /* === BOARD RENDERING === */
    function updateBoard() {
        const team = state.currentTurn;

        // Team names
        document.getElementById("board-name-a").textContent = state.teams.a.name;
        document.getElementById("board-name-b").textContent = state.teams.b.name;

        // Chips
        document.getElementById("board-chips-a").innerHTML = `&#9679; ${state.teams.a.chips}`;
        document.getElementById("board-chips-b").innerHTML = `&#9679; ${state.teams.b.chips}`;

        // Timelines
        renderTimeline("timeline-a", state.teams.a.timeline, "team-a");
        renderTimeline("timeline-b", state.teams.b.timeline, "team-b");

        // Turn indicator
        const indicator = document.getElementById("turn-indicator");
        indicator.textContent = `Turno: ${state.teams[team].name}`;
        indicator.className = `turn-indicator turn-${team}`;

        // Highlight active team section
        document.getElementById("board-team-a").classList.toggle("active-team-section", team === "a");
        document.getElementById("board-team-b").classList.toggle("active-team-section", team === "b");

        // Song counter
        document.getElementById("song-counter").textContent =
            `Canciones restantes: ${SONGS.length - state.usedSongIds.size}`;
    }

    function renderTimeline(containerId, years, teamClass) {
        const container = document.getElementById(containerId);
        container.innerHTML = years
            .map(y => `<div class="timeline-card ${teamClass}"><span class="year-text">${y}</span></div>`)
            .join("");
    }

    /* === SONG SELECTION & PLAYBACK === */
    let ytPlayer = null;
    let countdownInterval = null;
    let countdownValue = 60;

    // YouTube IFrame API setup
    function onYouTubeIframeAPIReady() {
        ytPlayer = new YT.Player("youtube-player", {
            height: "1",
            width: "1",
            playerVars: {
                autoplay: 0,
                controls: 0,
                disablekb: 1,
                fs: 0,
                modestbranding: 1,
            },
            events: {
                onReady: () => console.log("YouTube player ready"),
            }
        });
    }

    function pickRandomSong() {
        const available = SONGS.filter(s => !state.usedSongIds.has(s.id));
        if (available.length === 0) return null;
        const song = available[Math.floor(Math.random() * available.length)];
        state.usedSongIds.add(song.id);
        return song;
    }

    function playSong() {
        const song = pickRandomSong();
        if (!song) {
            alert("No quedan mas canciones!");
            return;
        }
        state.currentSong = song;
        state.selectedRange = null;
        state.challengerRange = null;
        state.isChallenge = false;

        // Load and play YouTube video
        if (ytPlayer && ytPlayer.loadVideoById) {
            ytPlayer.loadVideoById(song.videoId);
        }

        // Start countdown
        countdownValue = 60;
        document.getElementById("countdown").textContent = countdownValue;
        document.getElementById("vinyl").classList.remove("paused");

        showScreen("playing");
        sfx.vinylScratch();

        countdownInterval = setInterval(() => {
            countdownValue--;
            document.getElementById("countdown").textContent = countdownValue;
            if (countdownValue <= 10) sfx.tick();
            if (countdownValue <= 0) {
                stopPlayback();
            }
        }, 1000);
    }

    function stopPlayback() {
        clearInterval(countdownInterval);
        if (ytPlayer && ytPlayer.pauseVideo) ytPlayer.pauseVideo();
        document.getElementById("vinyl").classList.add("paused");
        sfx.buzzer();
        showScreen("guess");
        // Reset guess screen
        document.getElementById("song-info").classList.remove("visible");
        document.getElementById("guess-buttons").style.display = "none";
        document.getElementById("btn-reveal-song").style.display = "";
    }

    function stopEarly() {
        stopPlayback();
    }

    /* === GUESS PHASE === */
    function revealSong() {
        document.getElementById("song-title").textContent = state.currentSong.title;
        document.getElementById("song-artist").textContent = state.currentSong.artist;
        document.getElementById("song-info").classList.add("visible");
        document.getElementById("guess-buttons").style.display = "flex";
        document.getElementById("btn-reveal-song").style.display = "none";
    }

    function guessResult(correct) {
        if (correct) {
            state.teams[state.currentTurn].chips++;
            sfx.correct();
        } else {
            sfx.wrong();
        }
        showPlaceScreen();
    }

    /* === PLACE PHASE === */
    function showPlaceScreen() {
        const team = state.teams[state.currentTurn];
        const timeline = team.timeline;

        // Show current timeline
        const teamClass = state.currentTurn === "a" ? "team-a" : "team-b";
        const placeTimeline = document.getElementById("place-timeline");
        placeTimeline.innerHTML = timeline
            .map(y => `<div class="timeline-card ${teamClass}"><span class="year-text">${y}</span></div>`)
            .join("");

        document.getElementById("place-title").textContent =
            `${team.name}: Ubicar en la Linea de Tiempo`;

        // Generate range buttons
        const ranges = generateRanges(timeline);
        const container = document.getElementById("range-buttons");
        container.innerHTML = ranges
            .map((r, i) => `<button class="btn btn-primary" onclick="selectRange(${i})">${r.label}</button>`)
            .join("");

        // Store ranges for later
        state._ranges = ranges;

        showScreen("place");
    }

    function generateRanges(timeline) {
        const ranges = [];
        ranges.push({
            label: `Antes de ${timeline[0]}`,
            min: -Infinity,
            max: timeline[0] - 1
        });
        for (let i = 0; i < timeline.length - 1; i++) {
            ranges.push({
                label: `Entre ${timeline[i]} y ${timeline[i + 1]}`,
                min: timeline[i],
                max: timeline[i + 1]
            });
        }
        ranges.push({
            label: `Despues de ${timeline[timeline.length - 1]}`,
            min: timeline[timeline.length - 1] + 1,
            max: Infinity
        });
        return ranges;
    }

    function selectRange(index) {
        state.selectedRange = index;
        showChallengeScreen();
    }

    /* === CHALLENGE PHASE === */
    function showChallengeScreen() {
        const opp = opponent(state.currentTurn);
        const oppTeam = state.teams[opp];
        const activeTeam = state.teams[state.currentTurn];
        const selectedLabel = state._ranges[state.selectedRange].label;

        document.getElementById("challenge-title").textContent = `Desafio!`;
        document.getElementById("challenge-info").innerHTML =
            `<strong>${activeTeam.name}</strong> eligio: <strong>${selectedLabel}</strong><br><br>` +
            `<strong>${oppTeam.name}</strong>, quieren desafiar? (Tienen ${oppTeam.chips} fichas)`;

        // Generate challenge range buttons (excluding the selected range)
        const container = document.getElementById("challenge-range-buttons");
        if (oppTeam.chips > 0) {
            const ranges = state._ranges;
            container.innerHTML = ranges
                .map((r, i) => {
                    if (i === state.selectedRange) return "";
                    return `<button class="btn btn-danger" onclick="acceptChallenge(${i})">${r.label}</button>`;
                })
                .join("");
        } else {
            container.innerHTML = `<p style="color: var(--text-muted);">No tienen fichas para desafiar.</p>`;
        }

        showScreen("challenge");
    }

    function acceptChallenge(rangeIndex) {
        state.isChallenge = true;
        state.challengerRange = rangeIndex;
        const opp = opponent(state.currentTurn);
        state.teams[opp].chips--;
        sfx.challenge();
        showRevealScreen();
    }

    function skipChallenge() {
        state.isChallenge = false;
        showRevealScreen();
    }

    /* === REVEAL PHASE === */
    function showRevealScreen() {
        document.getElementById("reveal-year").classList.remove("visible");
        document.getElementById("reveal-year").textContent = "";
        document.getElementById("reveal-result").style.display = "none";
        document.getElementById("btn-next-turn").style.display = "none";
        document.getElementById("btn-reveal-year").style.display = "";

        showScreen("reveal");
    }

    function revealYear() {
        const year = state.currentSong.year;
        const yearEl = document.getElementById("reveal-year");
        yearEl.textContent = year;
        yearEl.classList.add("visible");
        document.getElementById("btn-reveal-year").style.display = "none";

        // Determine who wins the card
        const ranges = state._ranges;
        const selectedRange = ranges[state.selectedRange];
        const activeCorrect = year >= selectedRange.min && year <= selectedRange.max;

        let challengerCorrect = false;
        if (state.isChallenge) {
            const challengerRange = ranges[state.challengerRange];
            challengerCorrect = year >= challengerRange.min && year <= challengerRange.max;
        }

        const resultEl = document.getElementById("reveal-result");
        const activeTeam = state.teams[state.currentTurn];
        const opp = opponent(state.currentTurn);
        const oppTeam = state.teams[opp];

        if (activeCorrect) {
            // Active team wins the card
            activeTeam.timeline.push(year);
            activeTeam.timeline.sort((a, b) => a - b);
            resultEl.innerHTML = `<span style="color: var(--success);">&#9989; ${activeTeam.name} acierta! La carta se agrega a su linea de tiempo.</span>`;
            sfx.correct();
        } else if (state.isChallenge && challengerCorrect) {
            // Challenger wins the card
            oppTeam.timeline.push(year);
            oppTeam.timeline.sort((a, b) => a - b);
            resultEl.innerHTML = `<span style="color: var(--accent-purple);">&#128170; ${oppTeam.name} gana el desafio! La carta va a su linea de tiempo.</span>`;
            sfx.correct();
        } else {
            // Nobody wins
            resultEl.innerHTML = `<span style="color: var(--danger);">&#10060; Nadie acerto. La carta se descarta.</span>`;
            sfx.wrong();
        }

        resultEl.style.display = "";

        // Check victory condition
        if (activeTeam.timeline.length >= 20) {
            state.winner = state.currentTurn;
            document.getElementById("btn-next-turn").textContent = "Ver Resultado";
            document.getElementById("btn-next-turn").onclick = () => showVictory(state.currentTurn);
        } else if (oppTeam.timeline.length >= 20) {
            state.winner = opp;
            document.getElementById("btn-next-turn").textContent = "Ver Resultado";
            document.getElementById("btn-next-turn").onclick = () => showVictory(opp);
        } else {
            document.getElementById("btn-next-turn").onclick = nextTurn;
            document.getElementById("btn-next-turn").textContent = "Siguiente Turno \u2192";
        }

        document.getElementById("btn-next-turn").style.display = "";
    }

    function nextTurn() {
        state.currentTurn = opponent(state.currentTurn);
        updateBoard();
        showScreen("board");
    }

    /* === VICTORY === */
    function showVictory(winnerKey) {
        const team = state.teams[winnerKey];
        document.getElementById("victory-title").innerHTML =
            `&#127942; ${team.name} GANA! &#127942;`;
        showScreen("victory");
        sfx.fanfare();
        spawnConfetti();
    }

    function spawnConfetti() {
        const container = document.getElementById("confetti-container");
        container.innerHTML = "";
        const colors = ["#4361ee", "#7209b7", "#f4a261", "#06d6a0", "#ef476f", "#edf2f4"];
        for (let i = 0; i < 80; i++) {
            const div = document.createElement("div");
            div.className = "confetti";
            div.style.left = Math.random() * 100 + "%";
            div.style.background = colors[Math.floor(Math.random() * colors.length)];
            div.style.animationDelay = Math.random() * 2 + "s";
            div.style.animationDuration = (2 + Math.random() * 2) + "s";
            div.style.width = (6 + Math.random() * 8) + "px";
            div.style.height = (6 + Math.random() * 8) + "px";
            div.style.borderRadius = Math.random() > 0.5 ? "50%" : "0";
            container.appendChild(div);
        }
    }

    function resetGame() {
        state = {
            teams: {
                a: { name: "Equipo A", timeline: [], chips: 0 },
                b: { name: "Equipo B", timeline: [], chips: 0 }
            },
            currentTurn: "a",
            usedSongIds: new Set(),
            currentSong: null,
            phase: "setup",
            winner: null,
            selectedRange: null,
            challengerRange: null,
            isChallenge: false
        };
        document.getElementById("team-a-name").value = "";
        document.getElementById("team-b-name").value = "";
        showScreen("setup");
    }

    /* === SOUND EFFECTS (Web Audio API) === */
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    const sfx = {
        vinylScratch() {
            const bufferSize = audioCtx.sampleRate * 0.3;
            const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
            const data = buffer.getChannelData(0);
            for (let i = 0; i < bufferSize; i++) {
                data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
            }
            const source = audioCtx.createBufferSource();
            source.buffer = buffer;
            const filter = audioCtx.createBiquadFilter();
            filter.type = "bandpass";
            filter.frequency.value = 800;
            filter.Q.value = 1;
            source.connect(filter);
            filter.connect(audioCtx.destination);
            source.start();
        },

        tick() {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.frequency.value = 1000;
            osc.type = "sine";
            gain.gain.value = 0.1;
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.05);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.05);
        },

        buzzer() {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.frequency.value = 150;
            osc.type = "square";
            gain.gain.value = 0.3;
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.5);
        },

        correct() {
            [523, 659].forEach((freq, i) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.frequency.value = freq;
                osc.type = "sine";
                gain.gain.value = 0.3;
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3 + i * 0.15);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start(audioCtx.currentTime + i * 0.15);
                osc.stop(audioCtx.currentTime + 0.3 + i * 0.15);
            });
        },

        wrong() {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.frequency.value = 300;
            osc.frequency.exponentialRampToValueAtTime(100, audioCtx.currentTime + 0.4);
            osc.type = "sawtooth";
            gain.gain.value = 0.2;
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.5);
        },

        challenge() {
            [440, 440, 523].forEach((freq, i) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.frequency.value = freq;
                osc.type = "square";
                gain.gain.value = 0.2;
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.1 + i * 0.12);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start(audioCtx.currentTime + i * 0.12);
                osc.stop(audioCtx.currentTime + 0.1 + i * 0.12);
            });
        },

        fanfare() {
            [523, 659, 784, 1047].forEach((freq, i) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.frequency.value = freq;
                osc.type = "sine";
                gain.gain.value = 0.3;
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5 + i * 0.2);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start(audioCtx.currentTime + i * 0.2);
                osc.stop(audioCtx.currentTime + 0.5 + i * 0.2);
            });
        }
    };

    /* === LOAD YOUTUBE API === */
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
    </script>
</body>
</html>
```

**Step 2: Open in browser and verify**

- Open `index.html` in Chrome
- Verify: Setup screen shows with logo, two inputs, start button
- Type team names, click "Comenzar Juego"
- Verify: Board screen shows both timelines with 2 random years each
- Click "Reproducir Cancion" (will fail gracefully since SONGS is empty — that's expected)
- Verify: Dark theme, fonts load, no console errors

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add complete game HTML with all screens, dark theme, SFX, and game logic"
```

---

## Phase 3: Data Integration

### Task 4: Embed song data into index.html

**Files:**
- Modify: `index.html` (replace SONGS placeholder)
- Input: `data/songs_final.json`

**Step 1: Create embed script**

Create `scripts/embed_songs.py`:

```python
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
```

**Step 2: Run and embed**

```bash
python scripts/embed_songs.py
```

Then replace the `const SONGS = [];` line in `index.html` with the contents of `data/songs_embedded.js`.

**Step 3: Open in browser and verify**

- Open `index.html`, start game
- Click "Reproducir Cancion" — should load a YouTube video (audio plays)
- Verify countdown works, vinyl spins
- Go through full flow: guess → place → reveal

**Step 4: Commit**

```bash
git add index.html scripts/embed_songs.py
git commit -m "feat: embed song data into index.html"
```

---

## Phase 4: Polish & Testing

### Task 5: End-to-end manual playtest

**Step 1: Full game flow test**

Open `index.html` in Chrome. Test this exact sequence:

1. **Setup**: Enter "Los Rockeros" and "Las Divas", click start
2. **Board**: Verify both teams show 2 year cards, chips = 0
3. **Play**: Click play, verify YouTube audio, vinyl spins, countdown ticks
4. **Stop early**: Click stop early button before 60s
5. **Guess**: Click reveal — verify song/artist shown, year hidden. Click "Acertaron" — verify chips increment
6. **Place**: Verify range buttons match the timeline. Select a range
7. **Challenge**: Verify challenge screen shows. Click "Sin Desafio"
8. **Reveal**: Click "Revelar Ano" — verify year shows with animation. Verify card placed correctly
9. **Next turn**: Verify turn switches to other team
10. **Challenge flow**: Play until a team has 1+ chips. On opponent turn, test challenge: spend chip, pick different range, verify resolution

**Step 2: Edge case tests**

- Start with no team names (should default to "Equipo A"/"Equipo B")
- Verify timelines stay sorted after card insertion
- Verify you can't challenge with 0 chips (buttons disabled/hidden)
- Verify song counter decrements

**Step 3: Fix any issues found**

**Step 4: Commit**

```bash
git add index.html
git commit -m "fix: polish game flow based on playtest feedback"
```

---

### Task 6: Visual polish pass

**Files:**
- Modify: `index.html` (CSS section)

**Step 1: Review on a large screen**

- Open in Chrome, press F11 for fullscreen (simulates TV)
- Check: text readability at distance, button sizes, timeline card visibility
- Check: screen transitions are smooth
- Check: vinyl animation is smooth
- Check: confetti on victory screen works

**Step 2: Fix any visual issues**

Common fixes to check:
- Timeline wrapping on many cards (flex-wrap behavior)
- Button spacing on place/challenge screens
- Year reveal animation smoothness
- Color contrast on all text

**Step 3: Commit**

```bash
git add index.html
git commit -m "style: visual polish for TV display"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | Tasks 1-2 | Song data pipeline (Python scripts) |
| 2 | Task 3 | Complete HTML file with all screens, CSS, JS, SFX |
| 3 | Task 4 | Embed song data into HTML |
| 4 | Tasks 5-6 | Playtest and visual polish |

**Total: 6 tasks.** Phase 1 (data) and Phase 2 (HTML) can be worked in parallel since they're independent.
