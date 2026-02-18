# link_squared

A local-first tool to extract, organize, and browse your X/Twitter bookmarks. Uses a Chrome extension to pull bookmarks from your logged-in session, stores them in SQLite, and serves a Streamlit dashboard to search, filter, sort, and manage them. Optionally auto-categorizes bookmarks using Claude.

## How It Works

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  X Bookmarks │────▶│   Chrome     │────▶│  Flask API   │────▶│   SQLite     │
│  Page (DOM)  │     │  Extension   │     │  (port 7799) │     │   Database   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                      │
                     ┌──────────────┐     ┌──────────────┐            │
                     │  Claude API  │◀────│ categorize.py│◀───────────┤
                     │  (optional)  │     │              │            │
                     └──────────────┘     └──────────────┘            │
                                                                      │
                                          ┌──────────────┐            │
                                          │  Streamlit   │◀───────────┘
                                          │  Dashboard   │
                                          └──────────────┘
```

1. You open `x.com/i/bookmarks` in your browser (already logged in)
2. Click the extension icon → **Fetch Bookmarks**
3. The extension scrolls through the page, extracts every tweet, and sends the data to a local Flask server
4. The server stores everything in a local SQLite database
5. You browse, search, and filter your bookmarks via a Streamlit dashboard
6. Optionally, run `categorize.py` to auto-tag bookmarks with Claude

Everything stays on your machine. No data leaves your computer (except the optional Claude API call for categorization).

## Project Structure

```
link_squared/
├── extension/             # Chrome/Chromium extension (Manifest V3)
│   ├── manifest.json
│   ├── popup.html         # Extension popup UI
│   ├── popup.js           # Triggers content script injection
│   └── content.js         # Scrolls bookmarks page, extracts tweet data, sends to server
├── lib/
│   ├── __init__.py
│   └── db.py              # SQLite schema, upsert, query, filter, delete helpers
├── server.py              # Flask API server — receives bookmarks from the extension
├── app.py                 # Streamlit dashboard — browse, search, filter, delete
├── categorize.py          # Auto-categorize bookmarks using Claude API
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

### Prerequisites

- Python 3.10+
- A Chromium-based browser (Chrome, Comet, Brave, Arc, Edge, etc.)

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Load the Chrome extension

1. Open your browser's extensions page:
   - Chrome: `chrome://extensions`
   - Comet: `comet://extensions`
   - Brave: `brave://extensions`
   - Edge: `edge://extensions`
2. Enable **Developer mode** (toggle in the top-right)
3. Click **Load unpacked** → select the `extension/` folder inside this repo

### 3. (Optional) Set up Claude API key for auto-categorization

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
# Get one at: https://console.anthropic.com/settings/keys
```

## Usage

### Fetch bookmarks

```bash
# Terminal 1: Start the local API server
python server.py
```

Then in your browser:

1. Navigate to [x.com/i/bookmarks](https://x.com/i/bookmarks)
2. Click the **link_squared** extension icon
3. Click **Fetch Bookmarks**
4. Wait for it to scroll through all your bookmarks (progress shown in the popup)

### Browse bookmarks

```bash
# Terminal 2: Launch the dashboard
streamlit run app.py
```

Opens a local web UI at `http://localhost:8501` with:

- **Search** across tweet text, author name, and handle
- **Filter** by category or author
- **Sort** by newest, oldest, most liked, most retweeted, or most discussed
- **Delete** individual bookmarks
- **View** media thumbnails and engagement stats
- **Link** back to the original tweet on X

### Auto-categorize with Claude

```bash
python categorize.py
```

Sends uncategorized bookmarks to Claude in batches of 20 and assigns one of these categories:

| Category | Category |
|---|---|
| Tech/AI | Design/Creative |
| Business/Finance | Humor/Entertainment |
| Science | News/Current Events |
| Politics | Personal Development |
| Career/Professional | Health/Fitness |
| Education/Learning | Other |

Costs roughly $0.05 for 175 bookmarks. Safe to re-run — skips already-categorized bookmarks.

## Data

All data is stored locally in `db/link_squared.db` (SQLite). The database persists between runs — you only need to fetch bookmarks once. Re-fetching upserts by tweet ID, so no duplicates are created and engagement counts get updated.

### Schema

```sql
bookmarks (
    id              INTEGER PRIMARY KEY,
    tweet_id        TEXT UNIQUE,
    url             TEXT,
    text            TEXT,
    author_name     TEXT,
    author_handle   TEXT,
    created_at      TEXT,
    media_urls      TEXT,       -- JSON array
    like_count      INTEGER,
    retweet_count   INTEGER,
    reply_count     INTEGER,
    category        TEXT,       -- set by categorize.py
    raw_json        TEXT,
    ingested_at     TEXT
)
```

## FAQ

**Do I need the server running to browse bookmarks?**
No. `streamlit run app.py` reads directly from the SQLite file. The server is only needed when fetching new bookmarks via the extension.

**Will re-fetching create duplicates?**
No. Bookmarks are upserted by `tweet_id`. Re-fetching updates engagement counts but won't duplicate entries.

**Does this work with Comet / Brave / Arc / Edge?**
Yes. Any Chromium-based browser that supports Manifest V3 extensions.

**Is my data sent anywhere?**
Only if you run `categorize.py`, which sends tweet text to the Anthropic API. Everything else stays local.
