"""Local audio server for Hitster Timeline.

Downloads YouTube audio via yt-dlp and serves it to the frontend.
Caches files in ./cache/ to avoid re-downloading.

Usage:
    python server.py
    # Then open index.html — it connects to http://localhost:5123
"""

import os
import subprocess
import threading
from pathlib import Path

from flask import Flask, Response, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Track in-progress downloads to avoid duplicates
_downloading: dict[str, threading.Event] = {}
_download_lock = threading.Lock()


def _audio_path(video_id: str) -> Path:
    return CACHE_DIR / f"{video_id}.webm"


def _download(video_id: str) -> Path | None:
    """Download audio for a videoId. Returns path on success, None on failure."""
    dest = _audio_path(video_id)
    if dest.exists():
        return dest

    # Coordinate concurrent requests for the same video
    with _download_lock:
        if video_id in _downloading:
            event = _downloading[video_id]
        else:
            event = threading.Event()
            _downloading[video_id] = event

    if not event.is_set():
        # Only one thread actually downloads
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f", "ba[ext=webm]/ba",  # best audio, prefer webm
                    "--no-playlist",
                    "-o", str(dest),
                    f"https://www.youtube.com/watch?v={video_id}",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                print(f"[yt-dlp error] {video_id}: {result.stderr[:300]}")
                dest.unlink(missing_ok=True)
        except subprocess.TimeoutExpired:
            print(f"[yt-dlp timeout] {video_id}")
            dest.unlink(missing_ok=True)
        finally:
            event.set()
            with _download_lock:
                _downloading.pop(video_id, None)

    # Wait if another thread was downloading
    event.wait(timeout=65)
    return dest if dest.exists() else None


@app.route("/audio/<video_id>")
def serve_audio(video_id: str):
    """Download (if needed) and serve audio for a YouTube videoId."""
    # Sanitize input
    if not video_id.replace("-", "").replace("_", "").isalnum():
        return jsonify(error="Invalid video ID"), 400

    path = _download(video_id)
    if path is None:
        return jsonify(error="Download failed"), 502

    return send_file(path, mimetype="audio/webm")


@app.route("/prefetch/<video_id>", methods=["POST"])
def prefetch(video_id: str):
    """Trigger background download without waiting for completion."""
    if not video_id.replace("-", "").replace("_", "").isalnum():
        return jsonify(error="Invalid video ID"), 400

    def bg():
        _download(video_id)

    threading.Thread(target=bg, daemon=True).start()
    return jsonify(status="downloading")


@app.route("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    print("Hitster Audio Server running on http://localhost:5123")
    print(f"Cache directory: {CACHE_DIR.resolve()}")
    app.run(host="127.0.0.1", port=5123, threaded=True)
