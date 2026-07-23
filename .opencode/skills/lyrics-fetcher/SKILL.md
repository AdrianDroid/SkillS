---
name: lyrics-fetcher
description: |
  Use when the user asks to fetch, search, download, or find lyrics for songs in their music library.
  Scans audio files (MP3, M4A, FLAC, WMA) for metadata, queries LRCLIB and NetEase APIs, and saves
  .lrc synced-lyric sidecar files alongside each audio file.
---

# Lyrics Fetcher

Fetches synced lyrics (.lrc) for all audio files in a music library by reading embedded metadata, querying LRCLIB and NetEase APIs, and saving `.lrc` sidecar files.

## Script

The script is at `{skill_dir}/fetch_lyrics.py`.

Dependencies: `mutagen`, `requests` (install with `pip install mutagen requests`).

## Usage

```bash
python3 {skill_dir}/fetch_lyrics.py [options]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--dir`, `-d` | `~/Music` | Music directory to scan |
| `--workers`, `-w` | `10` | Concurrent API workers |
| `--dry-run` | off | Scan and count files without fetching |
| `--limit`, `-l` | `0` | Process only N files (for testing) |

### Default behavior

1. Walks the entire music directory recursively
2. Reads ID3/MP4/FLAC/WMA tags for artist + title
3. Falls back to filename parsing when tags are missing
4. Tries LRCLIB API (exact match, then search)
5. Tries NetEase API for songs with CJK (Chinese/Japanese/Korean) titles
6. Saves `.lrc` file next to the audio file
7. Skips files that already have an `.lrc` sidecar (resume-safe)
8. Extracts embedded lyrics from audio metadata when present

### Example

```bash
# Fetch lyrics for all songs in ~/Music with 10 workers
python3 {skill_dir}/fetch_lyrics.py

# Test on a single album
python3 {skill_dir}/fetch_lyrics.py --dir "~/Music/Lossy/Adele" --limit 5

# Dry run to count files
python3 {skill_dir}/fetch_lyrics.py --dry-run
```

## Logging

Output is logged to `~/Music/lyrics_fetch.log` (detailed) and stdout.

## Notes

- Instrumental/classical tracks rarely return lyrics (expected)
- Some directories may have permission issues (e.g., slskd downloads)
- ~50% hit rate is typical for mixed libraries (vocals only)
