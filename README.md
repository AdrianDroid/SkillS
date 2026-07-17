# SkillS

Collection of opencode skills for AI-assisted software engineering.

## Skills

### data-miner

Autonomous web research agent. Given a topic, it searches intelligently, deep-dives into promising links, reverse-engineers JS-rendered pages via Playwright/XHR interception, extracts data from PDFs, and produces structured summaries with auditable source logs.

**Capabilities:**
- Web search with iterative refinement
- Playwright-based JS rendering + network interception
- API endpoint discovery and replay
- PDF text extraction
- Structured research reports with confidence assessment

**Case studies:**
- Heng An ILAS / Manulife fund data extraction (107 + 464 fund records)
- AMD stock 1-hour candlestick data (Yahoo Finance API)
- TWICE album FLAC download source mapping (61 torrents catalogued)

### Usage

```powershell
opencode
> Load the data-miner skill and ask a research question
```
