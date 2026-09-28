---
name: daily-news-briefing
description: Use when the user asks for a daily news briefing, news report, headlines roundup, or current events summary covering HK/Hong Kong, US, finance, or world news. Use for any request to produce a "grounded" or well-sourced news digest.
---

# Daily News Briefing

## Overview

Produce a daily "grounded" news briefing covering four sections: Hong Kong (HK), United States (US), Finance, and World. Every claim must cite its source URL. Output must be self-contained mobile-friendly HTML with no external dependencies. Supports English (en) and Traditional Chinese (zh-hk).

## Task

Create today's news briefing by:
1. Searching for current headlines in all four categories in parallel
2. Drilling deeper — after initial search, fetch detailed articles for the most significant stories to provide rich context
3. Selecting the most significant 5-8 stories per section
4. Writing a paragraph-length summary per story (not just a headline) with bold lead-in, key context, and source URL
5. Rendering output as mobile-friendly HTML

## Output Format — Mobile-Friendly HTML

The output MUST be a complete, self-contained HTML document. Use this exact structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily News Briefing — [Date]</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, Helvetica, Arial, sans-serif; background: #f5f5f5; color: #222; line-height: 1.5; padding: 16px; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  .date { color: #666; font-size: 14px; margin-bottom: 20px; }
  h2 { font-size: 17px; color: #1a1a2e; border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; margin: 24px 0 12px; }
  .story { background: #fff; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .story p { font-size: 15px; }
  .story .source { font-size: 12px; color: #888; margin-top: 4px; }
  .story .source a { color: #0066cc; text-decoration: none; }
  .footer { margin-top: 24px; padding-top: 12px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }
</style>
</head>
<body>
<h1>Daily News Briefing</h1>
<div class="date">[Date]</div>

<h2>Hong Kong</h2>
<div class="story"><p><strong>[Headline]</strong> — [Paragraph summary with detail, context, and key facts.]</p><div class="source"><a href="[URL]">[Source Name]</a> · <a href="[URL2]">[Source Name 2]</a></div></div>
...

<h2>United States</h2>
...

<h2>Finance</h2>
...

<h2>World</h2>
...

<div class="footer">Briefing produced [date/time]. Sources verified at time of collection.</div>
</body>
</html>
```

## Verification Rules

- Every story MUST have clickable source URL(s) — prefer multiple corroborating sources
- Each story must start with a **bold headline** followed by a rich paragraph, not just a single sentence
- Do NOT include a story if you cannot find a verifiable source
- If two sources conflict, note the discrepancy rather than picking one
- Do NOT fabricate or extrapolate — a story is either sourced or not included
- Prefer primary sources (official statements, verified news orgs) over secondary
- When searching for HK news, check both English (SCMP, The Standard) and Chinese sources (DotDotNews, HK01, RTHK)
- After initial search, always do follow-up searches on top stories to gather paragraph-level detail

## Common Mistakes

- Markdown output instead of HTML — always produce complete HTML document
- Omitting source URLs — every story must have a clickable source link
- Fake/made-up news — verify everything before including
- No separate date — include the briefing date prominently
- Not mobile-responsive — the viewport meta tag and CSS must work on phone screens
- Shallow 1-2 sentence summaries — users want paragraph-length detail with context
- Single sourcing — prefer 2+ corroborating sources per story where available
- Forgetting follow-up searches — headlines alone are insufficient; drill into details
