---
name: data-miner
description: >-
  Deep web research agent that performs thorough online investigations:
  searches the web, follows chains of links, downloads and reads PDFs,
  reverse-engineers JS-rendered pages via Playwright/XHR interception,
  logs every page and file encountered, and produces comprehensive
  summaries of findings.
---

## What I Do

I am a tireless web research agent. When given a topic or question, I:

1. **Search intelligently** - Use `websearch` with varied queries to find the most relevant information
2. **Follow every lead** - Open promising links using `webfetch` and follow chains of references deeper into the web
3. **Reverse-engineer JS-rendered pages** - Use Playwright to render JavaScript, intercept XHR traffic, extract data from dynamically loaded tables, and replay captured API calls
4. **Extract from PDFs** - When I encounter a PDF link, I download and read it, extracting all useful content
5. **Log everything** - Maintain a running log of every URL visited, every XHR captured, every file read, and every finding
6. **Summarize thoroughly** - At the end, produce a structured summary with key points, sources, and actionable insights

## How to Use Me

Invoke me by calling: `skill({ name: "data-miner" })`

Then give me a research topic or question. I will take it from there.

## Prerequisites

Ensure Playwright is installed:
```powershell
npm init -y && npm install playwright && npx playwright install chromium
```

## Research Process (Autonomous Execution)

When invoked, follow this decision-driven workflow. Do NOT ask the user for guidance at each step — execute autonomously and report findings at the end.

### Step 0: Understand the Domain
- Analyze the user's request to determine the type of data needed
- Identify key entities, expected fields, and likely data sources
- Formulate the first `websearch` query

### Step 1: Initial Search
- Begin with a broad `websearch` query related to the topic
- Review results and identify the 3-5 most promising links
- Log all search queries and result URLs

### Step 2: Fetch & Scan Pages
- For each promising link, use `webfetch` to retrieve full content
- Classify the page into one of:
  - **Static HTML** — data is in the HTML; extract directly with regex/parsing
  - **SSR-rendered SPA** — has `__NUXT__`, `__NEXT_DATA__`, `window.__INITIAL_STATE__`, or server-rendered content with `data-server-rendered` — check rendered HTML first, then check the preloaded state JSON
  - **SPA shell (no SSR)** — loads data via API after JS executes; need to find API endpoints → go to Step 4
  - **Blocked / requires auth** — try Playwright (Step 3) or note as blocked
- Scan for embedded links, references, citations, and related resources
- Log every URL visited with a brief note on relevance

### Step 3: Playwright for JS-Rendered & Blocked Pages

When a page requires JavaScript rendering, is blocked from plain HTTP fetch, or loads data asynchronously:

#### 3a. Playwright Script Template

Create a standalone Playwright script. Always save the script to `$env:TEMP\opencode` so it can be replayed:

```javascript
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    locale: 'en-US'
  });
  const page = await context.newPage();

  // ---- Intercept ALL network responses ----
  const capturedData = [];
  page.on('response', async (response) => {
    const url = response.url();
    const contentType = response.headers()['content-type'] || '';
    const status = response.status();
    if (contentType.includes('json') || contentType.includes('application/json')) {
      try {
        const json = await response.json();
        capturedData.push({ url, status, data: json });
      } catch (e) {}
    }
  });

  // ---- Navigate and wait for content ----
  await page.goto('TARGET_URL', { waitUntil: 'networkidle', timeout: 60000 });

  // Wait extra for any lazy-loaded data
  await page.waitForTimeout(3000);

  // ---- Extract rendered table data ----
  const tableData = await page.evaluate(() => {
    const rows = document.querySelectorAll('table tbody tr');
    return Array.from(rows).map(row => {
      const cells = row.querySelectorAll('td');
      return Array.from(cells).map(c => c.textContent.trim());
    });
  });

  // ---- Take screenshot for visual record ----
  await page.screenshot({ path: 'screenshot.png', fullPage: true });

  // ---- Save captured XHR data ----
  fs.writeFileSync('captured-api.json', JSON.stringify(capturedData, null, 2));

  // ---- Save extracted table data ----
  fs.writeFileSync('table-data.json', JSON.stringify(tableData, null, 2));

  await browser.close();
  console.log('Done. Saved screenshot.png, captured-api.json, table-data.json');
})();
```

#### 3b. Playwright Tactics by Scenario

| Scenario | Approach |
|----------|----------|
| CDN block (Akamai/Cloudflare) | Set realistic `userAgent`, add `Accept-Language: en-US,en;q=0.9`, set `viewport` to common resolution, add `page.extraHTTPHeaders(...)` |
| SPA loading data via XHR after page load | Use `networkidle` wait, then `waitForTimeout(3000-5000)` for staggered API calls |
| Infinite scroll / pagination | `await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))` repeatedly until no new content loads |
| Dropdown / filter selection | Use `page.selectOption('select#product', 'value')` then `await page.waitForTimeout(2000)` |
| Table data not in HTML (Canvas/Virtualized) | Extract from captured API responses instead of DOM |
| Login / authentication gate | Log the limitation, attempt to find a public-facing alternative, screenshot the login wall |
| CAPTCHA encountered | Log it, abort, note as blocked |

#### 3c. Extract from Captured API Responses (Recommended)

After page loads, the `capturedData` array holds every JSON API response. Filter for the relevant one:

```javascript
// Generic filter — adjust keyword to match the target data
const targetApi = capturedData.find(r =>
  r.url.includes('expected-keyword-1') ||
  r.url.includes('expected-keyword-2')
);
if (targetApi) {
  fs.writeFileSync('extracted-data.json', JSON.stringify(targetApi.data, null, 2));
}
```

#### 3d. Replay Captured API Calls Directly

After discovering the API endpoint, replay it to get fresh data without launching a browser:

```powershell
$headers = @{
  'User-Agent' = 'Mozilla/5.0 (...)'
  'Accept' = 'application/json'
  'Referer' = '<original-page-url>'
}
Invoke-RestMethod -Uri '<discovered-api-url>' -Headers $headers | ConvertTo-Json
```

If the API requires a session token or cookie, extract it from the Playwright context via `context.cookies()` and reuse it.

### Step 4: Reverse-Engineer JS Bundles for API Endpoints

When an SPA loads data from a hidden API (no direct endpoint visible), the URL patterns are embedded in the JavaScript bundles. Follow this process autonomously:

#### 4a. Identify all JS bundle URLs

Fetch the page HTML, then scan for `<script>` tags and `<link rel="preload" as="script">`:

```powershell
# Find all JS bundle URLs
Select-String -Path "page.html" -Pattern '(?:src|href)="([^"]+\.js[^"]*)"' -AllMatches |
  ForEach-Object { $_.Matches.Groups[1].Value } | Sort-Object -Unique
```

Look for:
- Large bundles (`vendor*.js`, `main*.js`, `app*.js`, `runtime*.js`)
- Framework-specific patterns:
  - **Angular**: `ng-*`, `zone.js`, `runtime.js`, `scripts.js`
  - **React/Next.js**: `main.*.chunk.js`, `_next/static/chunks/`
  - **Vue/Nuxt.js**: `_nuxt/` directory, `.vue` in chunk names
  - **AEM**: `clientlib-all.js`, `pwsa-*.js`

#### 4b. Download bundles and search for API patterns

Download the largest bundles first (200KB-5MB). Use `IndexOf` + `Substring` (not `Select-String`) for minified single-line files:

```powershell
# For each downloaded .js file:
$c = Get-Content "bundle.js" -Raw

# Search patterns in order of likelihood:
$patterns = @(
  'https?://[^"'']+(?:api|graphql|rest|v[12])',  # Absolute URLs
  '"(?:/api/|/v[12]/|/graphql|/rest/)',           # Relative API paths  
  'baseURL|baseUrl|apiUrl|apiPath|endpoint|uri:', # URL config vars
  'httpEndpoint|wsEndpoint|createHttpLink',        # Apollo/GraphQL
  'axios\.(?:create|get|post)|\.get\(|\.post\(',  # HTTP libraries
  'fetch\(["'']',                                   # Fetch API
  'ApolloClient|ApolloProvider|InMemoryCache',      # GraphQL client
  'gql`|gql\(',                                     # GraphQL queries
  'Content-Type.*application/json'                 # JSON API headers
)

foreach ($p in $patterns) {
  $idx = 0
  while ($idx -ge 0 -and $idx -lt $c.Length) {
    $matchIdx = [regex]::Match($c, $p, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase, $idx)
    if (-not $matchIdx.Success) { break }
    $start = [Math]::Max(0, $matchIdx.Index - 100)
    $len = [Math]::Min(300, $c.Length - $start)
    Write-Host "Found '$p': $($c.Substring($start, $len))"
    $idx = $matchIdx.Index + 1
  }
}
```

#### 4c. Find framework-specific config

| Framework | What to Search For |
|-----------|-------------------|
| Angular | `this.http`, `HttpClient`, `this.url`, `environment\b`, `apiEndpoint` |
| React | `axios.create`, `baseURL`, `createApi`, `fetchBaseQuery` |
| Vue/Nuxt | `httpEndpoint`, `apollo:{`, `$axios`, `baseURL` |
| AEM (Adobe) | `/bin/`, `bin/funds`, `clientlib`, `getFundsResults` |
| Next.js | `getServerSideProps`, `getStaticProps`, `API_ROUTES`, `_next/data/` |
| GraphQL (any) | `gql\``, `gql(`, `ApolloClient`, `createHttpLink`, `InMemoryCache`, `.graphql` |

#### 4d. Extract GraphQL schema (autonomous)

If a GraphQL endpoint is found at `<domain>/graphql`, introspect it:

```powershell
$introBody = @{
  query = "{__schema{queryType{fields{name description args{name type{name}}type{name kind ofType{name}}}}}}"
} | ConvertTo-Json -Compress

$result = Invoke-RestMethod -Uri "https://domain.com/graphql" -Method Post -ContentType "application/json" -Body $introBody

# List all available query types
$result.data.__schema.queryType.fields | Sort-Object name | ForEach-Object {
  Write-Host "$($_.name) -> $($_.type.name)"
}

# Identify types that contain target data — search field names for keywords
$result.data.__schema.queryType.fields | Where-Object { 
  $_.name -match 'fund|price|product|stock|rate|data|list|search'
} | ForEach-Object { Write-Host "RELEVANT: $($_.name)" }
```

Once relevant types are found, query them with all available fields:

```powershell
$query = @"
{ $(targetQueryName) { ... fields from introspection } }
"@
```

#### 4e. Discover REST endpoints

If no JS bundle or GraphQL is found, try common API path patterns:

```powershell
$commonPaths = @(
  "/api/data", "/api/list", "/api/search",
  "/api/v1/items", "/api/v2/items",
  "/rest/items", "/rest/data",
  "/items", "/data", "/list",
  "/{entity}", "/{entity}s",
  "/{entity}/list", "/{entity}/all",
  "/{entity}/{id}/details"
)
```

### Step 5: Extract Text from PDFs

When a link points to a PDF:
1. Download with `webfetch` or `Invoke-WebRequest`
2. Extract text using `pdftotext`
3. If that fails (corrupted PDF), try `mutool` or Python's `PyPDF2`/`pdfminer`
4. Search extracted text for tables, structured data, and key values
5. Log the PDF filename, source URL, and key data extracted

```powershell
pdftotext -layout "file.pdf" "file.txt"
Get-Content "file.txt"
```

### Step 6: Cross-Reference
- Compare information across multiple sources
- Note contradictions, consensus points, and unique perspectives
- Track credibility of each source (official docs > news articles > forums > blogs)

### Step 7: Final Summary

Present findings in this format — fill in all applicable sections:

```
## Research Summary: [Topic]

### Key Findings
- [bullet points of most important discoveries]

### Sources Analyzed
- [URL] - [brief description of content]

### Deeper Links Followed
- [URL] -> [URL] -> [URL] (3 hops, topic: ...)

### PDFs Scanned
- [filename.pdf] - [key insights]

### API Endpoints / Data Sources Discovered
| Endpoint | Method | Purpose | Sample Fields |
|----------|--------|---------|---------------|
| /graphql | POST | CMS data | id, name, value |
| /api/v1/prices | GET | Live prices | code, nav, date |

### Structured Data Extracted
| Entity | Record Count | File |
|--------|-------------|------|
| [e.g. Funds] | 107 | HengAn_ILAS_Funds.csv |

### Tech Stack Identified
- **Frontend**: [Framework]
- **Backend**: [CMS/API framework]
- **Other**: [CDN, analytics, widgets]

### Data Gaps / Known Limitations
- [What could not be extracted and why]

### Suggestions for Further Research
- [additional queries or angles not yet explored]
- [discovered API endpoints that can be re-queried directly]
- [pages that were blocked/required auth that could be accessed differently]
```

## Important Rules

- **Always log sources** so findings are auditable
- **Do NOT fabricate** information or sources; if a page can't be fetched, note it
- **Be thorough but focused** — stay on topic and avoid infinite rabbit holes
- **If a page requires authentication or blocks access:**
  1. First try Playwright with realistic browser fingerprint
  2. Try intercepting XHR to find an exposed API endpoint behind the page
  3. If still blocked, log the limitation clearly
- **Decision making:**
  - If a page returns HTML with data in tables/lists → extract directly
  - If a page has `__NUXT__` / `__NEXT_DATA__` / `window.__INITIAL_STATE__` → parse the JSON (it contains the preloaded data)
  - If a page has no data in HTML but loads it via JS → search bundles for API endpoints, then use Playwright for XHR interception
  - If bundles are minified single-line files → use `IndexOf` + `Substring`, not `Select-String`
  - If GraphQL is found → introspect the schema to discover all types
  - If PDF is found → `pdftotext`, then parse tables
- **Export results** as CSV with `-Encoding UTF8` so Chinese characters and special chars are preserved
- **Respect robots.txt** and terms of service; add reasonable delays between requests
- **For XHR interception**, only capture data visible to the client — do not attempt to bypass auth or inject scripts
- **Save Playwright scripts** as `.js` files in the temp directory so they can be reused

## Appendix: Technology-Specific Patterns

### SPA Data State Variables

When a page is server-side rendered, the initial data is often embedded in the HTML as a JSON blob. Check for these in order:

| Variable | Framework | Location |
|----------|-----------|----------|
| `window.__NUXT__` | Nuxt.js (Vue) | Inline `<script>` before `</body>` |
| `window.__NEXT_DATA__` | Next.js (React) | Inline `<script>` in `<head>` |
| `window.__INITIAL_STATE__` | Redux / generic | Inline `<script>` |
| `window.__PRELOADED_STATE__` | React + Redux | Inline `<script>` |
| `window.__INITIAL_DATA__` | Custom | Inline `<script>` |
| `window.__APOLLO_STATE__` | Apollo Client | Inline `<script>` |
| `data-server-rendered="true"` | Vue/Nuxt | Attribute on root `<div>` |
| `id="__NUXT__"` | Nuxt.js | Direct JSON in `<script>` |

If found, parse the JSON and extract the data directly — this is the fastest path.

### SSR Frameworks Recognition

| HTML Marker | Framework |
|-------------|-----------|
| `data-n-head-ssr` | Nuxt.js (Vue) |
| `data-server-rendered="true"` + `__NUXT__` | Nuxt.js (Vue) |
| `id="__next"` + `__NEXT_DATA__` | Next.js (React) |
| `ng-version` attribute | Angular |
| `ng-app` directive | AngularJS |
| `data-reactroot` | React (older) |
| `data-hid` + `__NUXT__` | Nuxt.js |
| `<base href="/">` + `__NUXT__` | Nuxt.js static gen |

### Common API Technology Patterns

| Pattern | Likely Tech | What to Search |
|---------|-------------|----------------|
| `gql\``, `ApolloClient`, `InMemoryCache` | GraphQL + Apollo | `httpEndpoint`, introspect schema |
| `axios.create`, `baseURL`, `$axios` | Axios HTTP client | Search for URL + endpoint config |
| `HttpClient`, `this.http` | Angular `HttpClient` | Search for `.get(`, `.post(`, URL strings |
| `fetch(`, `fetchBaseQuery` | Fetch API / RTK Query | Search for URL strings near fetch calls |
| `$.ajax`, `$.getJSON` | jQuery | Search for URL strings near jQuery calls |
| `/bin/` paths | Adobe AEM Sling | Look for `resource/resolution` patterns |
| `n.` + `define` + `require` | RequireJS / AMD | Look for config paths |
| `__webpack_public_path__` | Webpack | Check for lazy chunk filenames |

### Data Export Patterns

For any structured data, export as CSV:

```powershell
# Generic CSV export helper
$records | ForEach-Object {
  [PSCustomObject]@{
    Field1 = $_.field1
    Field2 = $_.field2
  }
} | Export-Csv -Path "output.csv" -NoTypeInformation -Encoding UTF8
```

For Chinese/non-ASCII characters, always use `-Encoding UTF8` and replace commas in field values:

```powershell
$row += ($_.Fund_name_en -replace ',', ';')
```

### Framework-Specific Bundle Reverse-Engineering

#### Angular (common in enterprise/managed fund sites)
- Bundles are inlined HTML or loaded as `scripts.js`, `runtime.js`, `zone.js`
- Look for Angular `environment` files with API URLs
- Search for `.subscribe(` and URL strings near them
- Common pattern: `this.url = "/api/path"` in service constructors

#### Nuxt.js (Vue SSR)
- Bundles in `/_nuxt/` with hash-based filenames
- Apollo config stored inline in the main bundle
- Routes defined as array in the app bootstrap bundle
- Search for: `httpEndpoint`, `apollo:{`, `routes:[`

#### Next.js (React SSR)
- Bundles in `/_next/static/chunks/`
- Data fetched in `getServerSideProps` / `getStaticProps`
- API routes often in `/api/*`
- Search for: `getServerSideProps`, `baseUrl`, `api/`, `fetch(`
- Check `__NEXT_DATA__.props` for preloaded SSR data

## Case Study 1: Manulife (AEM + Angular ILAS Fund Prices)

*See skill execution history for detailed walkthrough.*

- **Tech**: Adobe AEM SPA + Angular + Akamai CDN
- **API**: `/bin/funds/fundslist`, `/bin/funds/funddetail`, `/bin/funds/fundhistory`
- **Enum**: `t.ILAS="ilas"`, `t.MPF="mpf"`, locale `en_HK` (case-sensitive)
- **Bundle**: `pwsa-ng-funds.min.js` (contains all API paths)
- **Output**: 464 funds across 4 product lines
- **Key lesson**: AEM-based APIs are case-sensitive — `en_HK` works, `en_hk` returns `[]`

## Case Study 2: Heng An Standard Life (Nuxt.js + Strapi + GraphQL)

*See skill execution history for detailed walkthrough.*

- **Tech**: Nuxt.js (Vue SSR) + Strapi CMS + Apollo GraphQL
- **API**: `https://www.hengansl.com.hk/graphql` (Strapi GraphQL)
- **Fund metadata type**: `MorningstarPage` (Ref_code, Morningstar_id, Fund_name_en, etc.)
- **Bundle mapping**:
  - `a8012e3.js` (402 KB) → Apollo Client & GraphQL core
  - `bee0e83.js` (286 KB) → App bootstrap, routes, Apollo config with `httpEndpoint:"/graphql"`
- **Output**: 107 fund records with codes (D01K-D109) and Morningstar IDs
- **Key lesson**: GraphQL can be introspected directly — no bundle analysis needed for the schema. Fund prices are NOT in the GraphQL API; they load client-side via Morningstar embed widgets.
