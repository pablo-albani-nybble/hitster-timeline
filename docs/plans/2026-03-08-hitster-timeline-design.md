# Hitster Timeline - Game Design Document

## Overview

Interactive musical board game web app combining mechanics from "Hitster" and "Timeline". Two teams compete by listening to songs, guessing the artist/title, and placing the song's release year in their timeline. Designed for local play projected via Screen Mirroring to a TV.

**Key constraint**: The host also plays, so all answers (artist, title, year) must remain hidden until explicitly revealed via buttons.

## Tech Stack

- **Single file**: `index.html` (~300KB with embedded song data)
- **Languages**: HTML5 + CSS3 + Vanilla JS (ES6+)
- **External dependencies** (CDN, requires internet):
  - YouTube IFrame API (audio playback)
  - Google Fonts: Inter + Space Grotesk
- **Audio effects**: Web Audio API (synthesized, no external files)
- **Platform**: Desktop first (mouse/keyboard), mobile version planned later

## Game Rules

### Setup
- Two teams with customizable names
- Each team starts with 2 random year cards (1900-2024), sorted ascending
- Both teams start with 0 chips (fichas)
- Turns alternate between teams

### Turn Flow (6 phases)

1. **Board**: Shows both timelines. Button to play next song (indicates whose turn it is)
2. **Playing**: Random unplayed song loads in hidden YouTube player. Spinning vinyl + 60s countdown. No spoilers shown. Auto-pause at 60s. Option to stop early.
3. **Guess** (Song/Artist): Host presses "Revelar Cancion/Artista" to show title + artist (year stays hidden). Buttons: "Acertaron (+1 Ficha)" or "Fallaron".
4. **Place** (Timeline): Dynamic range buttons generated from current team's timeline. E.g., cards [1970, 2000] produce: "Antes de 1970", "Entre 1970 y 2000", "Despues de 2000". Team selects a range.
5. **Challenge**: Opposing team can spend 1 chip to challenge (only if chips > 0). If they challenge, they pick a different range. Option to skip.
6. **Reveal**: Button "Revelar Ano". Year appears full-screen. Auto-resolution:
   - Active team correct: card inserts into their timeline
   - Active team wrong + challenger correct: card goes to challenger's timeline, challenger loses 1 chip
   - Active team wrong + challenger wrong: challenger loses 1 chip, card discarded
   - Nobody challenged + active team wrong: card discarded

### Victory
- First team to reach 20 cards in their timeline wins
- Victory screen with celebration animation

## Song Data

### Sources
- **Global rankings**: Pre-existing `canciones.json` file (top songs per year worldwide 1900-2026, top per decade 1900-1970)
- **Argentine rankings**: Generated via `generate_ar_songs.py` - Top 5 per year (1970-2026), strictly Spanish-language Argentine artists only

### Generation Pipeline
1. `generate_ar_songs.py`: Uses Claude API to generate Argentine song lists, then `youtube-search-python` to find videoIds. Output: `canciones_ar.json`
2. `merge_songs.py`: Merges `canciones.json` + `canciones_ar.json`, deduplicates by title+artist, assigns unique IDs, adds `region` field. Output: `songs_final.json`

### Song Schema
```json
{
  "id": 1,
  "title": "La Balsa",
  "artist": "Los Gatos",
  "year": 1967,
  "videoId": "abc123",
  "region": "ar"
}
```

## UI Architecture

### Screens (as `<section>` elements, show/hide)

1. **Setup**: Logo, two team name inputs, "Comenzar Juego" button
2. **Board**: Team A timeline (top), turn info + play button (center), Team B timeline (bottom), chip counters on sides
3. **Playing** (modal): Full dark overlay, spinning vinyl SVG, 60s circular countdown, stop-early button
4. **Guess**: "Revelar Cancion/Artista" button, then shows title+artist, "Acertaron"/"Fallaron" buttons
5. **Place**: Current team's timeline displayed, dynamic range buttons
6. **Challenge**: Challenge prompt for opposing team, range selection if challenged, skip button
7. **Reveal**: "Revelar Ano" button, year displayed full-screen, result message, "Siguiente Turno" button
8. **Victory**: Full-screen winner announcement, CSS confetti animation, "Jugar de Nuevo" button

### Transitions
- Fade + slide (300ms ease) between screens

## Visual Design

### Color Palette
```
--bg-primary:    #0a0a0f     (main background, near black)
--bg-card:       #1a1a2e     (cards and panels)
--bg-surface:    #16213e     (elevated surfaces)
--accent-blue:   #4361ee     (Team A, primary buttons)
--accent-purple: #7209b7     (Team B)
--accent-gold:   #f4a261     (chips, correct guesses)
--text-primary:  #edf2f4     (primary text)
--text-muted:    #8d99ae     (secondary text)
--success:       #06d6a0     (correct)
--danger:        #ef476f     (wrong, challenge)
```

### Typography
- **UI text**: Inter (Google Fonts CDN)
- **Numbers/years on cards**: Space Grotesk (bold, large)

### Card Design
- Rounded rectangles with glassmorphism (blur + transparency)
- Team-colored borders (blue/purple)
- Hover: subtle glow in team color
- Insert animation: slide-in with bounce

### Vinyl Animation (Playing screen)
- SVG vinyl disc with infinite CSS `rotate`
- Subtle shine/reflection sweep
- Circular countdown around vinyl using `conic-gradient`

### Buttons
- Minimum 60px height (TV visibility)
- Rounded, no visible borders, solid backgrounds
- Hover: scale(1.05) + glow
- "Revelar" buttons: shimmer/gradient animation for suspense

## Sound Effects (Web Audio API)

| Event | Sound | Technique |
|-------|-------|-----------|
| Song start | Vinyl scratch | Filtered white noise with ramp |
| Countdown tick | Soft tick | Short oscillator click |
| Time's up | Buzzer | Low square wave, short |
| Correct guess | Ascending ding | Two sine tones, C to E |
| Wrong guess | Womp womp | Descending tone |
| Challenge launched | Dramatic alert | Staccato dramatic tone |
| Victory | Fanfare | Ascending major arpeggio (C-E-G-C) |

## Game State Object
```js
{
  teams: {
    a: { name: "Equipo A", timeline: [1975, 2001], chips: 0 },
    b: { name: "Equipo B", timeline: [1983, 2015], chips: 0 }
  },
  currentTurn: "a",
  usedSongIds: new Set(),
  currentSong: null,
  phase: "board",  // setup | board | playing | guess | place | challenge | reveal | victory
  winner: null
}
```

## Language
- All UI text in Spanish
- All code (variables, comments, functions) in English
