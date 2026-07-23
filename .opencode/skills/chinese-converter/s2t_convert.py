#!/usr/bin/env python3
"""Convert text between Simplified and Traditional Chinese using OpenCC.

Supports .lrc files, directory names, and arbitrary text files.
"""

import os
import sys
import argparse
import opencc
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

LOCK = Lock()
stats = {"converted": 0, "error": 0, "skipped": 0}


def get_converter(mode):
    config_map = {
        "s2t": "s2t.json",
        "t2s": "t2s.json",
        "s2tw": "s2tw.json",
        "tw2s": "tw2s.json",
        "s2hk": "s2hk.json",
        "hk2s": "hk2s.json",
    }
    config = config_map.get(mode, "s2t.json")
    return opencc.OpenCC(config)


def convert_file(filepath, cc):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = cc.convert(content)
        if content != new_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            with LOCK:
                stats["converted"] += 1
            return "converted"
        else:
            with LOCK:
                stats["skipped"] += 1
            return "skipped"
    except UnicodeDecodeError:
        with LOCK:
            stats["error"] += 1
        return f"error: not UTF-8"
    except Exception as e:
        with LOCK:
            stats["error"] += 1
        return f"error: {e}"


def rename_dirs(base_dir, cc, dry_run):
    dirs_to_rename = []
    for root, dirs, _ in os.walk(str(base_dir), topdown=False):
        for d in dirs:
            new = cc.convert(d)
            if d != new:
                old_path = os.path.join(root, d)
                new_path = os.path.join(root, new)
                dirs_to_rename.append((old_path, new_path))

    count = 0
    for old_path, new_path in dirs_to_rename:
        if dry_run:
            print(f"  WOULD RENAME: {os.path.basename(old_path)} -> {os.path.basename(new_path)}")
            count += 1
            continue
        try:
            if os.path.exists(new_path):
                # Merge: move unique items from old to new
                for item in os.listdir(old_path):
                    src = os.path.join(old_path, item)
                    dst = os.path.join(new_path, item)
                    if not os.path.exists(dst):
                        os.rename(src, dst)
                # Remove old dir if empty
                if not os.listdir(old_path):
                    os.rmdir(old_path)
                else:
                    # Fall back to _converted suffix
                    final_path = new_path + "_converted"
                    os.rename(old_path, final_path)
                    print(f"  RENAMED (merged): {os.path.basename(old_path)} -> {os.path.basename(final_path)}")
                    count += 1
                    continue
            else:
                os.rename(old_path, new_path)
            print(f"  RENAMED DIR: {os.path.basename(old_path)} -> {os.path.basename(new_path)}")
            count += 1
        except Exception as e:
            print(f"  ERROR renaming {old_path}: {e}", file=sys.stderr)
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Convert Simplified <-> Traditional Chinese in files and directory names"
    )
    parser.add_argument("--dir", "-d", type=str, default=str(Path.home() / "Music"),
                        help="Target directory (default: ~/Music)")
    parser.add_argument("--mode", "-m", type=str, default="s2t",
                        choices=["s2t", "t2s", "s2tw", "tw2s", "s2hk", "hk2s"],
                        help="Conversion direction (default: s2t)")
    parser.add_argument("--workers", "-w", type=int, default=20,
                        help="Concurrent workers (default: 20)")
    parser.add_argument("--ext", "-e", type=str, default=".lrc",
                        help="File extensions to process, comma-separated (default: .lrc)")
    parser.add_argument("--rename-dirs", action="store_true", default=True,
                        help="Rename directories with Chinese names (default: true)")
    parser.add_argument("--no-rename-dirs", action="store_false", dest="rename_dirs",
                        help="Skip directory renaming")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying anything")
    args = parser.parse_args()

    base_dir = Path(args.dir).expanduser().resolve()
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        sys.exit(1)

    cc = get_converter(args.mode)
    extensions = tuple(e.strip() for e in args.ext.split(","))

    print(f"Mode: {args.mode} ({args.dir})")
    print(f"Extensions: {', '.join(extensions)}")
    if args.dry_run:
        print("DRY RUN — no files will be modified\n")

    # Step 1: Rename directories
    if args.rename_dirs:
        print("\nRenaming directories...")
        dir_count = rename_dirs(base_dir, cc, args.dry_run)
        print(f"  {dir_count} directories {'would be' if args.dry_run else ''} renamed")

    # Step 2: Convert file content
    print(f"\nScanning for files with extensions {extensions}...")
    all_files = [f for f in base_dir.rglob("*") if f.suffix.lower() in extensions]
    print(f"Found {len(all_files)} files")

    if args.dry_run:
        # Count convertible files
        convertible = 0
        for fp in all_files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read(2000)
                if cc.convert(content) != content:
                    convertible += 1
            except Exception:
                pass
        print(f"  {convertible} files would be converted")
        print(f"  {len(all_files) - convertible} files would be skipped")
        print("\nDry run complete.")
        return

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(convert_file, f, cc): f for f in all_files}
        done = 0
        total = len(futures)
        for future in as_completed(futures):
            done += 1
            if done % max(1, total // 20) == 0 or done == total:
                pct = done * 100 // total
                print(f"  Progress: {done}/{total} ({pct}%) — converted={stats['converted']} skipped={stats['skipped']} errors={stats['error']}")

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"  Files converted:  {stats['converted']}")
    print(f"  Files skipped:    {stats['skipped']}")
    print(f"  Errors:           {stats['error']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
