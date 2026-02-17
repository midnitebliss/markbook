#!/usr/bin/env python3
"""Streamlit app to browse and search X/Twitter bookmarks."""

import json

import pandas as pd
import streamlit as st

from lib.db import init_db, get_all, get_stats, get_categories, SORT_OPTIONS

init_db()

# --- Page config ---
st.set_page_config(page_title="link_squared", page_icon="🔗", layout="wide")
st.title("link_squared")
st.caption("Your X/Twitter bookmarks in one place")

# --- Stats ---
stats = get_stats()

if stats["total"] == 0:
    st.warning(
        "No bookmarks yet. Run `python server.py`, then use the extension to fetch."
    )
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Bookmarks", stats["total"])
col2.metric("Unique Authors", stats["authors"])
col3.metric("Categorized", stats["total"] - stats["uncategorized"])
if stats["earliest"]:
    col4.metric("Date Range", f"{stats['earliest'][:10]} — {stats['latest'][:10]}")

if stats["uncategorized"] > 0:
    st.info(
        f"{stats['uncategorized']} bookmarks need categorization. "
        "Run `python categorize.py` to auto-categorize with Claude."
    )

st.divider()

# --- Sidebar: Filters & Sort ---
with st.sidebar:
    st.header("Filters")

    search = st.text_input("Search", placeholder="Search tweet text, author...")

    # Category filter
    categories = get_categories()
    if categories:
        cat_options = ["All"] + [
            f"{c['category']} ({c['count']})" for c in categories
        ]
        selected_cat = st.selectbox("Category", cat_options)
        category_filter = None
        if selected_cat != "All":
            category_filter = selected_cat.rsplit(" (", 1)[0]
    else:
        category_filter = None

    # Author filter
    if stats["top_authors"]:
        author_options = ["All"] + [
            f"@{a['author_handle']} ({a['count']})"
            for a in stats["top_authors"]
            if a["author_handle"]
        ]
        selected_author = st.selectbox("Author", author_options)
        author_filter = None
        if selected_author != "All":
            author_filter = selected_author.split("@")[1].split(" ")[0]
    else:
        author_filter = None

    st.divider()
    st.header("Sort")
    sort_by = st.radio("Sort by", list(SORT_OPTIONS.keys()), index=0)

# --- Results ---
df = get_all(
    search=search or None,
    author=author_filter,
    category=category_filter,
    sort=sort_by,
    limit=500,
)

if df.empty:
    st.info("No bookmarks match your filters.")
    st.stop()

st.subheader(f"{len(df)} bookmarks")

for _, row in df.iterrows():
    with st.container():
        # Header line: author, date, category
        author = f"**@{row['author_handle']}**" if row["author_handle"] else "Unknown"
        name = row["author_name"] or ""
        date = row["created_at"][:10] if row["created_at"] else ""
        cat_badge = f"  `{row['category']}`" if row.get("category") else ""

        st.markdown(f"{name} ({author}) · {date}{cat_badge}")

        # Tweet text
        text = row["text"] or ""
        st.markdown(text[:500] + ("..." if len(text) > 500 else ""))

        # Engagement stats and link
        likes = row["like_count"] or 0
        retweets = row["retweet_count"] or 0
        replies = row["reply_count"] or 0
        st.caption(
            f"❤️ {likes:,}  🔁 {retweets:,}  💬 {replies:,}  "
            f"[Open on X]({row['url']})"
        )

        # Media thumbnails
        media = json.loads(row["media_urls"]) if row["media_urls"] else []
        if media:
            cols = st.columns(min(len(media), 4))
            for i, url in enumerate(media[:4]):
                cols[i].image(url, use_container_width=True)

        st.divider()
