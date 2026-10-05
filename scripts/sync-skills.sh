#!/usr/bin/env bash
# Sync skills between this repo (.opencode/skills) and the global skills dir
# (~/.config/opencode/skills). The repo is the source of truth; the global copy is
# what OpenCode actually loads. Nothing enforces that, so run this after editing.
#
# Skills are matched by the `name:` field in SKILL.md, NOT by folder name — they
# differ for DnC (name `DnC`, folder `divide-and-conquer`) and for the ILAS
# extract skill (name `ilAS-data-extract`, folder `ilas-fund-analysis`).

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ROOT="$REPO/.opencode/skills"
DST_ROOT="${SKILLS_GLOBAL_DIR:-$HOME/.config/opencode/skills}"

DRY_RUN=0; ALL=0; YES=0; STATUS_ONLY=0; PRUNE=0

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

usage() {
  cat <<'EOF'
Sync OpenCode skills between this repo and the global skills directory.

  sync-skills.sh [options] [selection]

Options:
  -s, --status    show status only, sync nothing
  -a, --all       sync every skill that is out of date
  -y, --yes       no prompt (use with --all, or pass a selection)
  -n, --dry-run   report what would change, write nothing
  -p, --prune     delete files in the global copy that the repo does not have
  -h, --help      this text

Selection:
  Comma-separated numbers and ranges, e.g.  1,3,5-7
  Blank to skip.  'a' selects everything.

Environment:
  SKILLS_GLOBAL_DIR   override the destination (default ~/.config/opencode/skills)
EOF
}

# Expand long options so getopts sees only single letters.
expanded=()
for a in "$@"; do
  case "$a" in
    --status)   expanded+=(-s) ;;
    --all)      expanded+=(-a) ;;
    --yes)      expanded+=(-y) ;;
    --dry-run)  expanded+=(-n) ;;
    --prune)    expanded+=(-p) ;;
    --help)     expanded+=(-h) ;;
    --)         expanded+=(--) ;;
    *)          expanded+=("$a") ;;
  esac
done
set -- "${expanded[@]}"

while getopts ":saynph" opt; do
  case "$opt" in
    s) STATUS_ONLY=1 ;; a) ALL=1 ;; y) YES=1 ;;
    n) DRY_RUN=1 ;;    p) PRUNE=1 ;; h) usage; exit 0 ;;
    *) die "unknown option -$OPTARG (try --help)" ;;
  esac
done
shift $((OPTIND - 1))
SELECTION="${1:-}"

[ -d "$SRC_ROOT" ] || die "repo skills dir not found: $SRC_ROOT"

# --- discovery ---------------------------------------------------------------
# Prints "key<TAB>path" per skill directory, keyed on the lowercased name: field.
discover() {
  local root="$1" dir file key
  [ -d "$root" ] || return 0
  for dir in "$root"/*/; do
    file="${dir}SKILL.md"
    [ -f "$file" ] || continue
    key="$(sed -n 's/^name:[[:space:]]*//p' "$file" | head -1 | tr -d '\r' | tr 'A-Z' 'a-z')"
    [ -n "$key" ] || key="$(basename "${dir%/}" | tr 'A-Z' 'a-z')"
    printf '%s\t%s\n' "$key" "${dir%/}"
  done
}

# Repo output that is not part of a skill.
EXCLUDE_NAMES=(node_modules __pycache__ .git .pytest_cache .DS_Store)
RSYNC_EX=(--exclude=node_modules/ --exclude=__pycache__/ --exclude=.git/ --exclude=.pytest_cache/ --exclude=.DS_Store)

# File list for a directory, one relative path per line, excludes pruned.
list_files() {
  [ -d "$1" ] || return 0
  local pred="" n
  for n in "${EXCLUDE_NAMES[@]}"; do
    pred+="${pred:+-o }-name $n"
  done
  ( cd "$1" && find . \( $pred \) -prune -o -type f -printf '%P\n' | sort )
}

file_hash() { md5sum "$1" 2>/dev/null | cut -d' ' -f1; }

# Membership test without a pipe: `grep -qx` exits on first match, which SIGPIPEs
# the writer and fails the whole pipeline under `set -o pipefail`.
contains() {
  local needle="$1" item
  shift
  for item in "$@"; do
    [ "$item" = "$needle" ] && return 0
  done
  return 1
}

# Compares a repo skill dir against its global counterpart.
# Prints "STATUS<TAB>changed<TAB>missing_in_global<TAB>extra_in_global"
compare_dirs() {
  local src="$1" dst="$2"
  local changed=0 missing=0 extra=0 rel
  local -a src_files=() dst_files=()

  while IFS= read -r rel; do src_files+=("$rel"); done < <(list_files "$src")
  while IFS= read -r rel; do dst_files+=("$rel"); done < <(list_files "$dst")

  for rel in "${src_files[@]}"; do
    if [ ! -f "$dst/$rel" ]; then
      missing=$((missing + 1))
    elif [ "$(file_hash "$src/$rel")" != "$(file_hash "$dst/$rel")" ]; then
      changed=$((changed + 1))
    fi
  done
  for rel in "${dst_files[@]}"; do
    [ -f "$src/$rel" ] || extra=$((extra + 1))
  done

  local status=OK
  if [ "$missing" -gt 0 ] || [ "$changed" -gt 0 ]; then status=DRIFT; fi
  [ -d "$dst" ] || status=NEW
  [ "$extra" -gt 0 ] && [ "$status" = OK ] && status=EXTRA

  printf '%s\t%d\t%d\t%d\n' "$status" "$changed" "$missing" "$extra"
}

# --- status table ------------------------------------------------------------
declare -a ROWS=()          # "key|folder|label|status|changed|missing|extra"
declare -a ACTION_KEYS=()

build_rows() {
  local key src dst name
  while IFS=$'\t' read -r key src; do
    [ -n "$key" ] || continue
    name="$(sed -n 's/^name:[[:space:]]*//p' "$src/SKILL.md" | head -1)"
    [ -n "$name" ] || name="$key"
    dst="$DST_ROOT/$(find_global_dir "$key")"
    local st ch mi ex
    IFS=$'\t' read -r st ch mi ex <<<"$(compare_dirs "$src" "$dst")"
    ROWS+=("$(printf '%s|%s|%s|%s|%s|%s|%s' "$key" "$(basename "$src")" "$name" "$st" "$ch" "$mi" "$ex")")
  done < <(discover "$SRC_ROOT")
}

# Global directory whose SKILL.md declares this name; else the name itself.
find_global_dir() {
  local key="$1" dir file k
  [ -d "$DST_ROOT" ] || { printf '%s' "$key"; return; }
  for dir in "$DST_ROOT"/*/; do
    file="${dir}SKILL.md"
    [ -f "$file" ] || continue
    k="$(sed -n 's/^name:[[:space:]]*//p' "$file" | head -1 | tr -d '\r' | tr 'A-Z' 'a-z')"
    [ -n "$k" ] || k="$(basename "${dir%/}" | tr 'A-Z' 'a-z')"
    if [ "$k" = "$key" ]; then basename "${dir%/}"; return; fi
  done
  printf '%s' "$key"
}

print_table() {
  ACTION_KEYS=()
  printf '\n%-3s %-22s %-24s %s\n' "#" "FOLDER" "SKILL name" "STATUS"
  printf '%s\n' "$(printf '%.0s-' {1..78})"
  local i=1 row key folder name st ch mi ex detail
  for row in "${ROWS[@]}"; do
    IFS='|' read -r key folder name st ch mi ex <<<"$row"
    detail=""
    [ "$ch" -gt 0 ] && detail+="${ch} changed"
    [ "$mi" -gt 0 ] && detail+="${detail:+ }${mi} missing"
    [ "$ex" -gt 0 ] && detail+="${detail:+ }${ex} extra"
    case "$st" in
      OK)    label="ok" ;;
      DRIFT) label="OUT OF DATE"; ACTION_KEYS+=("$i") ;;
      NEW)   label="not installed";  ACTION_KEYS+=("$i") ;;
      EXTRA) label="extra files in global"; ACTION_KEYS+=("$i") ;;
      *)     label="$st" ;;
    esac
    printf '%-3s %-22s %-24s %s%s\n' "$i" "$folder" "$name" "$label" "${detail:+  ($detail)}"
    i=$((i + 1))
  done
  printf '\nrepo   %s\nsync   %s\n' "$SRC_ROOT" "$DST_ROOT"
}

# --- selection ---------------------------------------------------------------
PICKED=()
# Appends row numbers to PICKED. Aborts the script on bad input (which a
# command substitution inside mapfile would not — die there dies a subshell).
parse_selection() {
  local input="$1" part lo hi n
  PICKED=()
  input="${input// /}"
  [ -z "$input" ] && return 0
  if [ "$input" = "a" ]; then
    PICKED=("${ACTION_KEYS[@]}")
    return 0
  fi
  local -a parts
  IFS=',' read -ra parts <<<"$input"
  for part in "${parts[@]}"; do
    [ -n "$part" ] || continue
    if [[ "$part" =~ ^[0-9]+$ ]]; then
      PICKED+=("$part")
    elif [[ "$part" =~ ^([0-9]+)-([0-9]+)$ ]]; then
      lo="${BASH_REMATCH[1]}"; hi="${BASH_REMATCH[2]}"
      [ "$lo" -gt "$hi" ] && { lo="$hi"; hi="${BASH_REMATCH[1]}"; }
      for ((n = lo; n <= hi; n++)); do PICKED+=("$n"); done
    else
      die "cannot parse selection: '$part' (try numbers, ranges, or 'a')"
    fi
  done
}

# --- sync --------------------------------------------------------------------
sync_one() {
  local key="$1" src dst name changed=0 missing=0
  while IFS=$'\t' read -r k s; do
    [ "$k" = "$key" ] || continue
    src="$s"; break
  done < <(discover "$SRC_ROOT")
  [ -n "${src:-}" ] || { printf '  !! %s: not found in repo\n' "$key"; return 1; }

  name="$(sed -n 's/^name:[[:space:]]*//p' "$src/SKILL.md" | head -1)"
  dst="$DST_ROOT/$(find_global_dir "$key")"

  if [ "$DRY_RUN" -eq 1 ]; then
    printf '  [dry-run] %s -> %s\n' "$name" "$dst"
    return 0
  fi

  mkdir -p "$dst"
  rsync -a --delete "${RSYNC_EX[@]}" "$src/" "$dst/"

  if [ "$PRUNE" -eq 0 ] && [ -d "$dst" ]; then
    local rel
    while IFS= read -r rel; do
      [ -f "$src/$rel" ] && continue
      printf '  note: %s/%s exists only in the global copy (--prune removes it)\n' "$(basename "$dst")" "$rel"
    done < <(list_files "$dst")
  fi

  if [ "$PRUNE" -eq 1 ] && [ -d "$dst" ]; then
    while IFS= read -r rel; do
      [ -f "$src/$rel" ] && continue
      printf '  prune  %s/%s\n' "$(basename "$dst")" "$rel"
      rm -f "$dst/$rel"
    done < <(list_files "$dst")
    find "$dst" -type d -empty -delete 2>/dev/null || true
  fi
  printf '  synced %s -> %s\n' "$name" "$dst"
}

main() {
  build_rows
  [ "${#ROWS[@]}" -eq 0 ] && die "no skills found in $SRC_ROOT"
  print_table

  if [ "$STATUS_ONLY" -eq 1 ]; then
    [ "${#ACTION_KEYS[@]}" -eq 0 ] && printf '\nEverything is in sync.\n'
    return 0
  fi

  if [ "${#ACTION_KEYS[@]}" -eq 0 ]; then
    printf '\nEverything is in sync. Nothing to do.\n'
    return 0
  fi

  if [ "$ALL" -eq 1 ] && [ -z "$SELECTION" ]; then
    PICKED=("${ACTION_KEYS[@]}")
  elif [ -n "$SELECTION" ]; then
    parse_selection "$SELECTION"
  elif [ "$YES" -eq 1 ]; then
    die "--yes needs --all or a selection"
  else
    printf '\nOut of date: %s\n' "$(printf '%s ' "${ACTION_KEYS[@]}")"
    printf 'Select to sync (numbers/ranges, blank to skip, a = all): '
    read -r answer || answer=""
    parse_selection "$answer"
  fi

  [ "${#PICKED[@]}" -eq 0 ] && { printf 'Nothing selected.\n'; return 0; }

  # Skip rows already in sync rather than rewriting them.
  local row i=1 key folder name st ch mi ex targets=() skipped=()
  for row in "${ROWS[@]}"; do
    IFS='|' read -r key folder name st ch mi ex <<<"$row"
    if contains "$i" "${PICKED[@]}"; then
      case "$st" in
        DRIFT|NEW) targets+=("$key") ;;
        # Only actionable for --prune; otherwise a no-op rewrite.
        EXTRA) [ "$PRUNE" -eq 1 ] && targets+=("$key") || skipped+=("$name") ;;
        *) skipped+=("$name") ;;
      esac
    fi
    i=$((i + 1))
  done
  [ "${#skipped[@]}" -gt 0 ] && printf 'Already in sync, skipping: %s\n' "$(printf '%s ' "${skipped[@]}")"
  [ "${#targets[@]}" -eq 0 ] && { printf 'Nothing to do.\n'; return 0; }

  printf '\nSyncing %d skill(s)\n' "${#targets[@]}"
  local t
  for t in "${targets[@]}"; do sync_one "$t" || printf '  !! %s failed\n' "$t"; done

  printf '\nDone.'
  [ "$DRY_RUN" -eq 1 ] && printf ' (dry run — nothing written)'
  printf '\n'
}

main "$@"