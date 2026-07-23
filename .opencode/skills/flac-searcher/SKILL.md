---
name: flac-searcher
description: |
  Use when the user wants to search for, download, organize, deduplicate, or clean up FLAC/lossless
  music files. Covers Soulseek via slskd, Chinese cloud drives (Baidu/Quark/Xunlei/Aliyun/Chengtong),
  Russian trackers (RuTracker, LosslessClub), Chinese music forums, and final library organization
  with lyrics. Best for Chinese/Cantopop/mandopop artists but applicable to any genre.
---

# FLAC Searcher & Downloader

Complete methodology for finding and downloading FLAC/lossless music from free sources, organizing the library, and attaching lyrics.

---

## 🔧 Soulseek via slskd (Primary Source)

### Setup
```bash
docker run -d --name slskd --restart unless-stopped \
  -p 5030:5030 -p 5031:5031 \
  -v /path/to/slskd_app:/app \
  -v /path/to/slskd_downloads:/downloads \
  -v /path/to/share:/shared \
  -e SLSKD_REMOTE_CONFIGURATION=true \
  slskd/slskd:latest
```

### Anti-Leech: Share Padding
Many Soulseek users block users with < 1000 shared files. Bypass:
```bash
mkdir -p /downloads/_share
# Create 500+ small dummy files
for i in $(seq 1 500); do
  dd if=/dev/urandom of="/downloads/_share/padding_$i.dat" bs=1M count=1 2>/dev/null
done
```

### API Auth
```bash
# Get bearer token
TOKEN=$(curl -s -X POST http://127.0.0.1:5030/api/v0/session \
  -H "Content-Type: application/json" \
  -d '{"username":"slskd","password":"slskd"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token')")
```

### Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v0/search` | POST | Search for files (searchText, searchMode, filter) |
| `/api/v0/users/{username}/browse` | GET | Browse a user's shared files |
| `/api/v0/transfers/downloads/{username}` | POST | Queue files for download |
| `/api/v0/transfers/downloads` | GET | List all transfers |
| `/api/v0/transfers/downloads/{username}` | GET | List transfers for specific user |
| `/api/v0/users/{username}` | GET | Check if user is online |

### Search Tips
- Search in Chinese and English: `G.E.M.` `鄧紫棋` `邓紫棋`
- Use album names: `新的心跳` `Xposed`
- Wait 22+ seconds between searches (Soulseek rate limit)
- Search from broad (`chinese pop flac`) to specific
- Try Cantonese-specific: `cantopop flac` `hk pop lossless`

### Queue Strategy
- Browse the user → get their current share structure
- Find ALL `.flac` files matching artist
- Queue in batches of 25-50 (smaller batches = more reliable)
- Files may get "Rejected: File not shared" if user changes share mid-transfer
- Files may get "Rejected: Overwhelmed with requests" — wait and retry
- Some users have per-session caps (~475 files / ~14 GB)

### Persistent Watcher Strategy
```python
# Pseudocode for a persistent harvester
while True:
    token = get_token()
    status = get_transfer_status(token)
    if files_done == file_count:  # previous batch completed or rejected
        try browse_user(token)
        if browse_ok and files_found:
            queue_in_batches()
    sleep(60)
```

---

## ☁️ Chinese Cloud Drives

### Access Requirements

| Service | Registration | Free Download | Notes |
|---------|-------------|---------------|-------|
| **Baidu Pan** (百度网盘) | +86 phone required | No (extremely slow without VIP) | Most common source |
| **Quark Pan** (夸克网盘) | +86 phone required | No | Links expire frequently |
| **Xunlei** (迅雷) | +86 phone required | No | — |
| **Aliyun Drive** (阿里云盘) | +86 phone required | Yes (good speeds) | Most generous free tier |
| **Chengtong/ctfile** (城通网盘) | Email only | Yes (slow ~100KB/s) | Most accessible for non-Chinese |
| **123Pan** (123云盘) | +86 phone required | Yes (limited) | — |

### Limitations
- **ALL** major Chinese cloud drives require +86 phone for registration
- Share links expire frequently (404: 分享不存在)
- Temporary Chinese phone services are unreliable for these platforms
- **Chengtong (ctfile)** is the only service that works with just email registration

### Where to Find Links
- **Baidu Tieba** (tieba.baidu.com) — search artist name
- **Zhihu** (zhuanlan.zhihu.com) — collection articles
- **Bilibili** (bilibili.com) — video descriptions often have links
- **Chinese music forums** — see Forums section below
- Search queries: `Artist 无损 FLAC 合集 百度云` `Artist 专辑 下载 夸克`

### Baidu Pan API Access (Limited)
```python
# Step 1: Submit extract code
r = requests.post(f"https://pan.baidu.com/share/verify?surl={SHARE_ID}&t={TS}",
    data={"pwd": "EXTRACT_CODE"})
# Returns randsk token on success (errno=0)

# Step 2: Request file list (requires login cookie)
r = requests.get(f"https://pan.baidu.com/share/list?surl={SHARE_ID}&dir=/",
    cookies={"BDCLND": "1", "randsk": RANDSK})
# errno=2 = "啊哦，链接出错了" — needs full login session
```
**Without a logged-in Baidu account, you can authenticate the share password but cannot list or download files.**

### Chengtong (ctfile) — Most Accessible
- Registration: email only (no phone)
- Download speed: ~100KB/s free, multi-part downloads possible
- API: `https://webapi.ctfile.com/getfile.php?f={FILE_ID}&passcode={PWD}`
- Free users: one file at a time, slow speed
- Links often expire (404: "share does not exist")

---

## 🇷🇺 Russian Trackers

| Tracker | FLAC Availability | Notes |
|---------|------------------|-------|
| **RuTracker** (rutracker.org) | Limited Chinese content | Mostly MP3 for Chinese artists |
| **LosslessClub** (losslessclub.com) | Very limited | Only major Western releases |
| **nnm-club.me** | None for Chinese | — |
| **Redacted.ch** | Good but invite-only | Hard to access |

RuTracker search query: `site:rutracker.org "Artist" "FLAC" "lossless"`

---

## 🏛️ Chinese Music Forums

| Forum | Access | Content | Strategy |
|-------|--------|---------|----------|
| **ptcd.net** | Free registration (email) | Paid thread: 29 music coins for 8.3GB collections | Post 15+ threads (+2 coins each) to earn coins |
| **hifiti.com** | Free registration (email) | Gold coin walls for some links | Reply to unlock |
| **hi-res.com.cn** | +86 phone required | 8.3GB collections | Blocked without phone |
| **pengxinziyuan.com** | +86 phone required | Cloud drive links | Blocked without phone |
| **51flacmusic.com** | Login required | Individual albums | Test login feasibility |
| **yuehaishibei.com** | VIP required | Per-album FLAC | Paid |
| **wusunku.com** | Invite code | Full collections | Hard to access |

### Forum Coin Grinding Strategy (e.g., ptcd.net)
```python
# 1. Create threads in active sections
for fid in [42, 43, 44, 47]:  # 华语, 欧美, 日韩, 影视
    # Post threads (each worth +2 coins)
    requests.post(f"forum.php?mod=post&action=newthread&fid={fid}",
        data={"formhash": FH, "subject": "...", "message": "..."})

# 2. Daily check-in (+1 coin)
# 3. Upload avatar (+5 coins)
# 4. Reply to existing threads (+1 coin each)
# 5. Referral links (+1 coin per IP)
```

**Key insight**: All require moderator approval for new user posts. This can take days or weeks.

---

## 📦 Final Library Organization

```bash
# Target structure
~/Music/Artist Name/
├── Album Name (Year)/
│   ├── 01 - Track Title.flac
│   ├── 01 - Track Title.lrc
│   └── ...
└── Singles/
    ├── Song Title.flac
    └── Song Title.lrc
```

### Dedup Strategy
1. Group files by size (exact duplicates have same size)
2. Check for same track name across albums vs Singles
3. Keep in proper album, remove from Singles
4. Compilation duplicates (Best Of, Greatest Hits) are expected — keep both
5. Remove orphan `.lrc` files (no matching `.flac`)

### Lyrics Fetching
- Use **LRCLIB** (`https://lrclib.net/api/get?artist_name=X&track_name=Y`) — free, no auth
- Fallback: **NetEase Music API** (`music.163.com/api/song/lyric?id=ID`) — best for Chinese songs
- Python packages: `requests`, optionally `mutagen` for embedded metadata
- Rate limit: 1 request/second

---

## 📋 Full Workflow

1. **Soulseek**: Setup slskd → share-pad → search → browse → queue → monitor → retry
2. **Cloud Drives**: Search for links → check viability (phone required? expired?) → if Chengtong try direct download
3. **Forums**: Register → grind coins → purchase collection threads
4. **Trackers**: Search RuTracker/LosslessClub for FLAC (rare for Chinese music)
5. **Organize**: Copy all collected FLACs → clean naming → deduplicate → move to final library
6. **Lyrics**: Fetch from LRCLIB + NetEase → save as .lrc sidecars
7. **Cleanup**: Remove temp downloads, padding files, screenshots, scripts, logs

---

## 🧠 Lessons Learned

- **Soulseek is the only reliable free source** for Chinese FLACs that doesn't require +86 phone
- nythnike (typical power user) has the most comprehensive G.E.M. collection
- Session caps (~475 files) are per-session, not permanent — user must come back online
- Share structures change frequently — re-browse before re-queueing
- Chinese cloud drives: ALL require +86 phone for registration, making them inaccessible
- Chengtong (ctfile): email-only registration but links expire fast and free download is slow
- RuTracker has NO FLAC for most Chinese artists — only MP3 320kbps
- Forum coin grinding takes days/weeks due to moderation queues
- Neither Apple Music nor Spotify can be freely ripped to FLAC
