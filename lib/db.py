import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "link_squared.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    text TEXT,
    author_name TEXT,
    author_handle TEXT,
    created_at TEXT,
    media_urls TEXT,
    like_count INTEGER,
    retweet_count INTEGER,
    reply_count INTEGER,
    category TEXT,
    raw_json TEXT,
    ingested_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bookmarks_author ON bookmarks(author_handle);
CREATE INDEX IF NOT EXISTS idx_bookmarks_created ON bookmarks(created_at);
CREATE INDEX IF NOT EXISTS idx_bookmarks_category ON bookmarks(category);
"""



def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    # Migrate existing DBs that lack the category column (must run before SCHEMA)
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='bookmarks'"
    ).fetchone()
    if existing:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(bookmarks)").fetchall()]
        if "category" not in cols:
            conn.execute("ALTER TABLE bookmarks ADD COLUMN category TEXT")
            conn.commit()
    # Now create tables/indexes (safe for both new and migrated DBs)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def upsert_bookmark(conn, bookmark: dict):
    conn.execute(
        """INSERT INTO bookmarks
           (tweet_id, url, text, author_name, author_handle, created_at,
            media_urls, like_count, retweet_count, reply_count, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(tweet_id) DO UPDATE SET
               text = excluded.text,
               author_name = excluded.author_name,
               like_count = excluded.like_count,
               retweet_count = excluded.retweet_count,
               reply_count = excluded.reply_count,
               raw_json = excluded.raw_json,
               ingested_at = datetime('now')
        """,
        (
            bookmark["tweet_id"],
            bookmark["url"],
            bookmark.get("text"),
            bookmark.get("author_name"),
            bookmark.get("author_handle"),
            bookmark.get("created_at"),
            json.dumps(bookmark.get("media_urls", [])),
            bookmark.get("like_count"),
            bookmark.get("retweet_count"),
            bookmark.get("reply_count"),
            json.dumps(bookmark.get("raw_json", {})),
        ),
    )


def upsert_many(conn, bookmarks: list[dict]):
    for bm in bookmarks:
        upsert_bookmark(conn, bm)
    conn.commit()
    return len(bookmarks)


SORT_OPTIONS = {
    "Newest first": "created_at DESC",
    "Oldest first": "created_at ASC",
    "Most liked": "like_count DESC",
    "Most retweeted": "retweet_count DESC",
    "Most discussed": "reply_count DESC",
}


def get_all(search=None, author=None, category=None, sort="Newest first", limit=500):
    import pandas as pd

    conn = get_conn()
    sql = "SELECT * FROM bookmarks WHERE 1=1"
    params = []

    if search:
        sql += " AND (text LIKE ? OR author_name LIKE ? OR author_handle LIKE ?)"
        params.extend([f"%{search}%"] * 3)

    if author:
        sql += " AND author_handle = ?"
        params.append(author)

    if category:
        sql += " AND category = ?"
        params.append(category)

    order = SORT_OPTIONS.get(sort, "created_at DESC")
    sql += f" ORDER BY {order}"

    if limit:
        sql += " LIMIT ?"
        params.append(limit)

    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def get_categories():
    conn = get_conn()
    rows = conn.execute(
        """SELECT category, COUNT(*) as count FROM bookmarks
           WHERE category IS NOT NULL
           GROUP BY category ORDER BY count DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_uncategorized_bookmarks(limit=50):
    import pandas as pd

    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT id, text, author_handle FROM bookmarks WHERE category IS NULL LIMIT ?",
        conn,
        params=[limit],
    )
    conn.close()
    return df


def set_category(conn, bookmark_id: int, category: str):
    conn.execute(
        "UPDATE bookmarks SET category = ? WHERE id = ?", (category, bookmark_id)
    )


def delete_bookmark(bookmark_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_conn()
    stats = {}
    stats["total"] = conn.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
    stats["authors"] = conn.execute(
        "SELECT COUNT(DISTINCT author_handle) FROM bookmarks"
    ).fetchone()[0]

    row = conn.execute(
        "SELECT MIN(created_at), MAX(created_at) FROM bookmarks"
    ).fetchone()
    stats["earliest"] = row[0]
    stats["latest"] = row[1]

    top_authors = conn.execute(
        """SELECT author_handle, author_name, COUNT(*) as count
           FROM bookmarks GROUP BY author_handle
           ORDER BY count DESC LIMIT 10"""
    ).fetchall()
    stats["top_authors"] = [dict(r) for r in top_authors]

    stats["uncategorized"] = conn.execute(
        "SELECT COUNT(*) FROM bookmarks WHERE category IS NULL"
    ).fetchone()[0]

    conn.close()
    return stats
