# Hitster v2 - Multi-Category Timeline Game

## Overview

Expand Hitster from a music-only timeline game to support multiple categories: Music (existing), Movies, and Historical Events. Each category has its own stimulus type and data source but shares the core timeline placement mechanic.

## Categories

| Category | Stimulus | Guess Target | Timeline | Data Source |
|----------|----------|-------------|----------|-------------|
| Music | Audio (30s) | Title + Artist | Year | Existing song data |
| Movies | YouTube trailer (30s) | Movie title | Year | TMDB API + YouTube trailers |
| Events | Image + short description | Event name | Year | Claude API + Wikipedia images |

## Architecture

### Folder Structure

```
Hitster/          <- v1, untouched
Hitster-v2/
  index.html      <- Multi-category UI
  server.py       <- Flask server (audio + image proxy)
  data/
    songs_full.json
    songs_light.json
    movies.json        <- 300 movies (1970+)
    events.json        <- 300 historical events (1950+)
  scripts/
    generate_movies.py
    generate_events.py
```

### Data Schemas

**Movies** (`movies.json`):
```json
{
  "id": 1,
  "title": "The Godfather",
  "year": 1972,
  "videoId": "sY1S34973zA",
  "posterUrl": "https://image.tmdb.org/t/p/w300/..."
}
```

**Events** (`events.json`):
```json
{
  "id": 1,
  "title": "Moon Landing",
  "description": "Neil Armstrong becomes the first human to walk on the Moon",
  "year": 1969,
  "imageUrl": "https://upload.wikimedia.org/..."
}
```

### UI Changes

1. **Setup screen**: Add category selector (Music / Movies / Events)
2. **Playing screen**:
   - Music/Movies: Vinyl disc + audio/video countdown (existing)
   - Events: Image display + description reveal + countdown
3. **Guess screen**: Adapt labels per category
4. **Board screen**: Generic "items remaining" counter

### Server Changes

- Keep existing `/audio/<videoId>` and `/prefetch/<videoId>` routes
- Add `/proxy-image?url=<encoded_url>` route for Wikipedia images (avoids CORS)

## Decisions

- Movies use YouTube trailers via the same audio server (play trailer audio, not video)
- Events show image + short hint, no audio
- All categories share the same timeline/placement/challenge mechanics
- v1 folder remains untouched for stability
