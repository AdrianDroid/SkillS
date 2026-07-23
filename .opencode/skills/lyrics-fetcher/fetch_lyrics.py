#!/usr/bin/env python3
"""
Fetch synced lyrics (.lrc) for all audio files in ~/Music.
Sources: LRCLIB (primary), NetEase (fallback for CJK).
Saves .lrc sidecar files alongside each audio file.
"""

import os
import re
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import requests
import mutagen
from mutagen.id3 import ID3, USLT
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.asf import ASF

MUSIC_DIR = Path.home() / "Music"
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".wma", ".wav", ".ogg", ".aac", ".opus", ".ape", ".aiff"}
LRC_EXTS = {".lrc", ".txt"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(MUSIC_DIR / "lyrics_fetch.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

LOCK = Lock()
STATS = {"found": 0, "not_found": 0, "skipped": 0, "error": 0, "embedded": 0}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json",
})
LRCLIB_BASE = "https://lrclib.net/api"


def get_tags(filepath):
    """Extract (artist, title, album) from audio metadata, returns (str, str, str or None)."""
    ext = filepath.suffix.lower()
    try:
        audio = mutagen.File(filepath, easy=False)
        if audio is None:
            return _parse_filename(filepath)

        if ext == ".mp3":
            return _get_mp3_tags(filepath, audio)
        elif ext == ".m4a":
            return _get_mp4_tags(audio)
        elif ext == ".flac":
            return _get_flac_tags(audio)
        elif ext == ".wma":
            return _get_asf_tags(audio)
        else:
            return _get_common_tags(audio)
    except Exception as e:
        log.debug("Error reading tags from %s: %s", filepath, e)
        return _parse_filename(filepath)


def _get_mp3_tags(filepath, audio):
    """Read ID3 tags from MP3 file."""
    try:
        tags = ID3(filepath)
        artist = _join_tag(tags.get("TPE1"))
        title = _join_tag(tags.get("TIT2"))
        album = _join_tag(tags.get("TALB"))
        if artist and title:
            return artist, title, album
    except Exception:
        pass
    if hasattr(audio, "tags") and audio.tags:
        return _get_common_tags(audio)
    return _parse_filename(filepath)


def _get_mp4_tags(audio):
    """Read MP4 metadata."""
    if not hasattr(audio, "tags") or audio.tags is None:
        return _parse_filename(Path(audio.filename))
    tags = audio.tags
    artist = _join_tag(tags.get("\xa9ART"))
    title = _join_tag(tags.get("\xa9nam"))
    album = _join_tag(tags.get("\xa9alb"))
    if artist and title:
        return artist, title, album
    return _parse_filename(Path(audio.filename))


def _get_flac_tags(audio):
    """Read Vorbis comments from FLAC."""
    if hasattr(audio, "tags") and audio.tags:
        artist = _join_tag(audio.tags.get("artist"))
        title = _join_tag(audio.tags.get("title"))
        album = _join_tag(audio.tags.get("album"))
        if artist and title:
            return artist, title, album
    return _parse_filename(Path(audio.filename))


def _get_asf_tags(audio):
    """Read ASF tags from WMA."""
    if hasattr(audio, "tags") and audio.tags:
        artist = _join_tag(audio.tags.get("Author"))
        title = _join_tag(audio.tags.get("Title"))
        album = _join_tag(audio.tags.get("WM/AlbumTitle"))
        if artist and title:
            return artist, title, album
    return _parse_filename(Path(audio.filename))


def _get_common_tags(audio):
    """Generic tag reading fallback."""
    if not hasattr(audio, "tags") or audio.tags is None:
        return _parse_filename(Path(audio.filename))
    tags = audio.tags
    for artist_key in ("artist", "TPE1", "\xa9ART", "Author"):
        for title_key in ("title", "TIT2", "\xa9nam", "Title"):
            artist = _join_tag(tags.get(artist_key))
            title = _join_tag(tags.get(title_key))
            if artist and title:
                album = _join_tag(tags.get("album")) or _join_tag(tags.get("TALB")) or _join_tag(tags.get("\xa9alb"))
                return artist, title, album
    return _parse_filename(Path(audio.filename))


def _join_tag(tag):
    """Convert a mutagen tag value to string."""
    if tag is None:
        return None
    if isinstance(tag, list):
        tag = tag[0] if tag else None
    if tag is None:
        return None
    s = str(tag).strip()
    return s if s else None


def _parse_filename(filepath):
    """Extract artist/title from filename as last resort."""
    stem = filepath.stem
    parent = filepath.parent

    # Pattern: "Artist - Title" or "TrackNum - Artist - Title"
    patterns = [
        r"^\d+[\.\s-]+\s*(.+?)\s*[-–—]\s*(.+)$",
        r"^(.+?)\s*[-–—]\s*(.+)$",
    ]
    for pat in patterns:
        m = re.match(pat, stem)
        if m:
            artist = m.group(1).strip()
            title = m.group(2).strip()
            # Remove feat/remaster info from title
            title = re.sub(r"\s*\(feat\..*\)", "", title, flags=re.IGNORECASE)
            title = re.sub(r"\s*\[.*?\]", "", title)
            if artist and title:
                return artist, title, None

    # Pattern: "TrackNum - Title" — use parent folder as artist
    m = re.match(r"^\d+[\.\s-]+\s*(.+)$", stem)
    if m:
        title = m.group(1).strip()
        artist = parent.name
        if "-" in parent.name:
            artist = parent.name.split("-")[0].strip()
        return artist, title, None

    # Last resort: use stem as title, parent as artist
    return parent.name, stem, None


def _normalize(s):
    """Normalize string for matching (lowercase, strip, collapse whitespace)."""
    if not s:
        return ""
    s = re.sub(r"[^\w\s]", "", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def has_embedded_lyrics(filepath):
    """Check if the audio file already has embedded lyrics."""
    ext = filepath.suffix.lower()
    try:
        if ext == ".mp3":
            tags = ID3(filepath)
            uslt = tags.getall("USLT")
            if uslt and any(u.text.strip() for u in uslt):
                return True
            sylt = tags.getall("SYLT")
            if sylt:
                return True
        elif ext == ".m4a":
            audio = MP4(filepath)
            if audio.tags and audio.tags.get("\xa9lyr"):
                return bool(audio.tags["\xa9lyr"][0].strip())
        elif ext == ".flac":
            audio = FLAC(filepath)
            if audio.tags and audio.tags.get("lyrics"):
                return bool(audio.tags["lyrics"][0].strip())
    except Exception:
        pass
    return False


def extract_embedded_lrc(filepath):
    """Try to extract embedded lyrics and save as .lrc file."""
    ext = filepath.suffix.lower()
    try:
        if ext == ".mp3":
            tags = ID3(filepath)
            for uslt in tags.getall("USLT"):
                text = uslt.text.strip()
                if text:
                    return text
            for sylt in tags.getall("SYLT"):
                lines = []
                for sync in sylt.sync:
                    ts = sync[1]
                    minutes = ts // 60000
                    seconds = (ts % 60000) // 1000
                    centiseconds = (ts % 1000) // 10
                    text = sync[0].decode("utf-8", errors="replace") if isinstance(sync[0], bytes) else sync[0]
                    lines.append(f"[{minutes:02d}:{seconds:02d}.{centiseconds:02d}]{text}")
                if lines:
                    return "\n".join(lines)
        elif ext == ".m4a":
            audio = MP4(filepath)
            if audio.tags and audio.tags.get("\xa9lyr"):
                text = audio.tags["\xa9lyr"][0]
                if text.strip():
                    return text
        elif ext == ".flac":
            audio = FLAC(filepath)
            if audio.tags and audio.tags.get("lyrics"):
                text = audio.tags["lyrics"][0]
                if text.strip():
                    return text
    except Exception as e:
        log.debug("Error extracting embedded lyrics from %s: %s", filepath, e)
    return None


def fetch_lrclib(artist, title):
    """Fetch synced lyrics from LRCLIB API."""
    params = {"artist_name": artist, "track_name": title}
    try:
        resp = SESSION.get(f"{LRCLIB_BASE}/get", params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("syncedLyrics"):
                return data["syncedLyrics"]
            if data.get("plainLyrics"):
                return data["plainLyrics"]
    except requests.exceptions.Timeout:
        log.debug("LRCLIB timeout for %s - %s", artist, title)
    except Exception as e:
        log.debug("LRCLIB error for %s - %s: %s", artist, title, e)
    return None


def fetch_lrclib_search(artist, title):
    """Search LRCLIB by query string."""
    query = f"{artist} {title}"
    try:
        resp = SESSION.get(f"{LRCLIB_BASE}/search", params={"q": query}, timeout=10)
        if resp.status_code == 200:
            results = resp.json()
            if results:
                best = None
                best_score = 0
                anorm = _normalize(artist)
                tnorm = _normalize(title)
                for r in results:
                    ra = _normalize(r.get("artistName", ""))
                    rt = _normalize(r.get("trackName", ""))
                    score = 0
                    if ra == anorm and rt == tnorm:
                        score = 3
                    elif ra == anorm or rt == tnorm:
                        score = 2
                    elif ra in anorm or anorm in ra:
                        score = 1
                    if score > best_score:
                        best_score = score
                        best = r
                if best and best_score >= 2:
                    if best.get("syncedLyrics"):
                        return best["syncedLyrics"]
                    if best.get("plainLyrics"):
                        return best["plainLyrics"]
    except Exception as e:
        log.debug("LRCLIB search error for %s - %s: %s", artist, title, e)
    return None


def fetch_netease(artist, title):
    """Fetch lyrics from NetEase Cloud Music API."""
    query = f"{artist} {title}"
    search_url = "https://music.163.com/api/search/get/web"
    params = {"s": query, "type": 1, "offset": 0, "limit": 10}
    headers = {
        "Referer": "https://music.163.com/",
        "User-Agent": SESSION.headers["User-Agent"],
    }
    try:
        resp = SESSION.get(search_url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("code") != 200:
            return None
        songs = data.get("result", {}).get("songs", [])
        if not songs:
            return None

        anorm = _normalize(artist)
        tnorm = _normalize(title)
        best_id = None
        best_score = 0

        for song in songs:
            sa = _normalize(song.get("artists", [{}])[0].get("name", ""))
            st = _normalize(song.get("name", ""))
            score = 0
            if sa == anorm and st == tnorm:
                score = 3
            elif sa == anorm or st == tnorm:
                score = 2
            elif anorm in sa or tnorm in st:
                score = 1
            if score > best_score:
                best_score = score
                best_id = song.get("id")

        if best_id is None or best_score < 2:
            return None

        lyric_url = "https://music.163.com/api/song/lyric"
        lrc_params = {"id": best_id, "lv": 1, "kv": 1, "tv": -1}
        lresp = SESSION.get(lyric_url, params=lrc_params, headers=headers, timeout=15)
        if lresp.status_code != 200:
            return None
        ldata = lresp.json()
        if ldata.get("code") != 200:
            return None

        # Prefer synced lyrics (lrc)
        lrc = ldata.get("lrc", {})
        if lrc and lrc.get("lyric"):
            text = lrc["lyric"].strip()
            if text:
                return text

        # Fallback to karaoke lyrics
        klyric = ldata.get("klyric", {})
        if klyric and klyric.get("lyric"):
            text = klyric["lyric"].strip()
            if text:
                return text

    except requests.exceptions.Timeout:
        log.debug("NetEase timeout for %s - %s", artist, title)
    except Exception as e:
        log.debug("NetEase error for %s - %s: %s", artist, title, e)
    return None


def is_timestamped(text):
    """Check if text contains LRC timestamps."""
    return bool(re.search(r"\[\d{2}:\d{2}[\.:]\d{2,3}\]", text))


def save_lrc(filepath, lrc_text, artist=None, title=None):
    """Save lyrics text as .lrc file alongside the audio file."""
    if not lrc_text or not lrc_text.strip():
        return False

    lrc_path = filepath.with_suffix(".lrc")
    try:
        with open(lrc_path, "w", encoding="utf-8") as f:
            if not is_timestamped(lrc_text):
                f.write("[ti:{}]\n".format(title or ""))
                f.write("[ar:{}]\n".format(artist or ""))
                f.write("[re:opencode-lyrics-fetcher]\n")
            f.write(lrc_text.strip())
            f.write("\n")
        return True
    except Exception as e:
        log.error("Failed to write %s: %s", lrc_path, e)
        return False


def _has_cjk(s):
    """Check if string contains CJK characters."""
    if not s:
        return False
    for ch in s:
        cp = ord(ch)
        if (0x3040 <= cp <= 0x30FF or 0x4E00 <= cp <= 0x9FFF or
            0xAC00 <= cp <= 0xD7AF or 0x3105 <= cp <= 0x312F or
            0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF):
            return True
    return False


def process_file(filepath):
    """Process a single audio file: check, fetch, save."""
    try:
        return _process_file(filepath)
    except Exception as e:
        log.error("Unexpected error processing %s: %s", filepath, e)
        with LOCK:
            STATS["error"] += 1
        return "error"


def _process_file(filepath):
    lrc_path = filepath.with_suffix(".lrc")
    if lrc_path.exists() and lrc_path.stat().st_size > 0:
        with LOCK:
            STATS["skipped"] += 1
        return "skipped"

    # Check embedded lyrics first
    if has_embedded_lyrics(filepath):
        lrc_text = extract_embedded_lrc(filepath)
        if lrc_text and save_lrc(filepath, lrc_text):
            with LOCK:
                STATS["embedded"] += 1
                STATS["found"] += 1
            return "embedded"

    artist, title, album = get_tags(filepath)
    if not artist or not title:
        with LOCK:
            STATS["error"] += 1
        log.debug("Could not extract artist/title from %s", filepath)
        return "error"

    lrc_text = None
    # Try LRCLIB exact match
    lrc_text = fetch_lrclib(artist, title)
    # Try LRCLIB search
    if not lrc_text:
        lrc_text = fetch_lrclib_search(artist, title)
    # Try NetEase only for CJK titles
    if not lrc_text and _has_cjk(title):
        lrc_text = fetch_netease(artist, title)

    if lrc_text and save_lrc(filepath, lrc_text, artist, title):
        with LOCK:
            STATS["found"] += 1
            log.info("FOUND: %s - %s (%s)", artist, title, filepath.relative_to(MUSIC_DIR))
        return "found"
    else:
        with LOCK:
            STATS["not_found"] += 1
            log.debug("NOT FOUND: %s - %s (%s)", artist, title, filepath.relative_to(MUSIC_DIR))
        return "not_found"


def collect_audio_files(base_dir):
    """Collect all audio files under base_dir."""
    files = []
    for root, dirs, fnames in os.walk(base_dir):
        root_path = Path(root)
        for fname in fnames:
            ext = Path(fname).suffix.lower()
            if ext in AUDIO_EXTENSIONS:
                files.append(root_path / fname)
    return files


def main():
    parser = argparse.ArgumentParser(description="Fetch synced lyrics for music library")
    parser.add_argument("--dir", "-d", type=str, default=str(MUSIC_DIR),
                        help="Music directory (default: ~/Music)")
    parser.add_argument("--workers", "-w", type=int, default=10,
                        help="Number of concurrent workers (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan and count files without fetching")
    parser.add_argument("--limit", "-l", type=int, default=0,
                        help="Limit number of files to process (for testing)")
    args = parser.parse_args()

    base_dir = Path(args.dir).expanduser().resolve()
    if not base_dir.exists():
        log.error("Directory not found: %s", base_dir)
        sys.exit(1)

    log.info("Scanning %s for audio files...", base_dir)
    all_files = collect_audio_files(base_dir)
    log.info("Found %d audio files", len(all_files))

    if args.limit > 0:
        all_files = all_files[:args.limit]
        log.info("Limited to %d files for testing", len(all_files))

    if args.dry_run:
        log.info("Dry run complete. %d files would be processed.", len(all_files))
        return

    log.info("Starting lyric fetch with %d workers...", args.workers)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_file, f): f for f in all_files}
        done = 0
        total = len(futures)
        for future in as_completed(futures):
            done += 1
            if done % 100 == 0:
                pct = done * 100 // total
                with LOCK:
                    log.info("Progress: %d/%d (%d%%) — found=%d not_found=%d skipped=%d errors=%d embedded=%d",
                             done, total, pct, STATS["found"], STATS["not_found"],
                             STATS["skipped"], STATS["error"], STATS["embedded"])

    log.info("=" * 50)
    log.info("FINAL STATS:")
    log.info("  Found lyrics:     %d", STATS["found"])
    log.info("  Not found:        %d", STATS["not_found"])
    log.info("  Skipped (exists): %d", STATS["skipped"])
    log.info("  Errors:           %d", STATS["error"])
    log.info("  Embedded:         %d", STATS["embedded"])
    log.info("  Total processed:  %d", sum(STATS.values()))
    log.info("=" * 50)


if __name__ == "__main__":
    main()
