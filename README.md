# Skills

Personal [OpenCode](https://opencode.ai) skill collection. Each skill is a `SKILL.md` the agent loads when a request matches its description. Helper scripts and templates live next to the skill that owns them.

Open this repo in OpenCode. Skills under `.opencode/skills/` are available in the session. Ask in natural language; the agent loads the matching skill. To reuse one elsewhere, copy its directory into that project's `.opencode/skills/`.

Run leftovers (`.cache/`, `.playwright-mcp/`, generated briefings and reports) are not part of the collection.

## Layout

```
.opencode/skills/<folder>/SKILL.md
```

Folder name and skill `name:` can differ. Invoke by the `name:` field, not the folder.

## ILAS pipeline

Three skills, used in order. Do not skip a stage.

1. **ilAS-data-extract** — scrape an ILAS plan's fund universe into an enriched CSV (NAV, 1Y/3Y/5Y, vol, Sharpe, TER, region, sector, type). Stops below 90% coverage.
2. **macro-research** — verified macro snapshot (rates, equities, commodities, geopolitics) as JSON. No recommendations.
3. **ilas-fund-report** — top-down reallocation report (macro → region → sector → funds → age-stratified portfolios) as Markdown plus a self-contained HTML page.

| Skill name | Folder | Role |
|---|---|---|
| `ilAS-data-extract` | `ilas-fund-analysis` | Extraction only. Hands a CSV to the report skill. |
| `macro-research` | `macro-research` | Facts for any market analysis, not only ILAS. |
| `ilas-fund-report` | `ilas-fund-report` | Analysis and report. Refuses incomplete CSVs. Templates: `template.html`, `report.js`, `schemas/`. Run notes: `RUN.md`. |

## Coordination

| Skill | What it does |
|---|---|
| `DnC` | Folder `divide-and-conquer`. Recursively split a project into bite-size units and dispatch independent waves in parallel via sub-agents. Parent coordinates and integrates; it does not also do the leaf work. |
| `six-hats` | Turns a decision into an audit record: falsifiable preview, six labelled hat slots per round across 1–3 rounds, verdict that confirms or revises. Requires the `sequentialthinking` MCP server. Tests: `pressure-tests.md`. |

## Research and writing

| Skill | What it does |
|---|---|
| `data-miner` | Autonomous web research: search, follow links, Playwright/XHR interception, PDF extraction, source log, structured summary. |
| `daily-news-briefing` | Sourced HK / US / finance / world digest as mobile HTML (en or zh-hk). Every claim needs a URL. |
| `financial-analyst` | Asset and strategy analysis (equities, crypto, forex, commodities) with risk-first framing. Educational, not advice. |
| `prompt-master` | Design, critique, and revise LLM prompts (persona, task, context, constraints, output format). |

## Music library

| Skill | What it does | Helper |
|---|---|---|
| `flac-searcher` | Find, download, dedupe, and organize lossless files (Soulseek/slskd, Chinese cloud drives, Russian trackers, Chinese forums). | — |
| `lyrics-fetcher` | Scan MP3/M4A/FLAC/WMA tags and write `.lrc` sidecars from LRCLIB and NetEase. | `fetch_lyrics.py` (`mutagen`, `requests`) |
| `chinese-converter` | Simplified ↔ Traditional Chinese for lyric files, filenames, and directory names via OpenCC. | `s2t_convert.py` (`opencc`) |

Music scripts default to `~/Music`. Pass `--dir` to point them elsewhere.
