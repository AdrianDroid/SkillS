---
name: chinese-converter
description: |
  Use ONLY when the user asks to convert text between Simplified Chinese (简体中文) and Traditional Chinese
  (繁體中文), or from simp. Chinese to tran. Chinese, or s2t/t2s. Converts .lrc lyric files, directory names,
  filenames, or any text content in a specified directory using OpenCC.
---

# Chinese Converter (简繁转换)

Converts text content between Simplified Chinese (简体中文) and Traditional Chinese (繁體中文) in files and directory names within a specified path.

## Script

The script is at `{skill_dir}/s2t_convert.py`.

Dependencies: `opencc` (install with `pip install opencc` or `apt install opencc`).

## Usage

```bash
python3 {skill_dir}/s2t_convert.py [--dir DIR] [--mode s2t|t2s] [--workers N]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--dir`, `-d` | `~/Music` | Target directory to scan |
| `--mode`, `-m` | `s2t` | Conversion direction: `s2t` (Simplified→Traditional) or `t2s` (Traditional→Simplified) |
| `--workers`, `-w` | `20` | Concurrent file workers |
| `--ext`, `-e` | `.lrc` | File extension to process (comma-separated, e.g. `.lrc,.txt,.md`) |
| `--rename-dirs` | `true` | Also rename directories with Chinese names (`true`/`false`) |
| `--dry-run` | off | Show what would be changed without modifying anything |

### Default behavior

1. Walks the entire directory recursively
2. Converts content of all matching files from Simplified to Traditional Chinese (or vice versa)
3. Renames directories containing Simplified/Traditional Chinese characters
4. Handles conflicts by merging unique files from duplicate directories
5. Skips files that have no convertible characters
6. Uses OpenCC for accurate character and phrase-level conversion

### Example

```bash
# Convert all .lrc files in ~/Music to Traditional Chinese
python3 {skill_dir}/s2t_convert.py

# Convert .txt and .md files in ~/Documents
python3 {skill_dir}/s2t_convert.py --dir ~/Documents --ext .txt,.md

# Reverse: Traditional to Simplified Chinese
python3 {skill_dir}/s2t_convert.py --dir ~/Books --mode t2s --ext .txt

# Preview changes without modifying anything
python3 {skill_dir}/s2t_convert.py --dir ~/Lyrics --dry-run
```

## Notes

- Uses OpenCC's `s2t.json` / `t2s.json` config for accurate character and phrase-level conversion
- Detects and handles directory name conflicts by merging content
- 16+ errors on first run are typically permission-denied on root-owned files (e.g. `slskd` downloads); run with `sudo` for those paths
- UTF-8 encoding assumed; files with other encodings are skipped with a warning
