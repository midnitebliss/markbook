#!/usr/bin/env python3
"""Auto-categorize bookmarks using Claude API."""

import json
import os
import time

import anthropic
from dotenv import load_dotenv

from lib.db import init_db, get_conn, get_uncategorized_bookmarks, set_category

load_dotenv()

BATCH_SIZE = 20  # tweets per API call

SYSTEM_PROMPT = """You are a tweet categorizer. Given a batch of tweets, assign exactly ONE category to each tweet from this list:

- Tech/AI
- Business/Finance
- Science
- Politics
- Career/Professional
- Design/Creative
- Humor/Entertainment
- News/Current Events
- Personal Development
- Health/Fitness
- Education/Learning
- Other

Respond with a JSON array of objects: [{"id": <tweet_id>, "category": "<category>"}]
No explanation, just the JSON array."""


def categorize_batch(client, tweets: list[dict]) -> dict[int, str]:
    """Send a batch of tweets to Claude and get categories back."""
    tweet_texts = []
    for _, row in tweets.iterrows():
        text = (row["text"] or "")[:300]
        author = row["author_handle"] or "unknown"
        tweet_texts.append(f'[ID={row["id"]}] @{author}: {text}')

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": "\n\n".join(tweet_texts)},
        ],
    )

    response_text = message.content[0].text.strip()
    # Handle markdown code blocks
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    results = json.loads(response_text)
    return {item["id"]: item["category"] for item in results}


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY in your .env file.")
        print("Get one at: https://console.anthropic.com/settings/keys")
        return

    init_db()
    uncategorized = get_uncategorized_bookmarks(limit=500)

    if uncategorized.empty:
        print("All bookmarks are already categorized!")
        return

    total = len(uncategorized)
    print(f"Categorizing {total} bookmarks...")

    client = anthropic.Anthropic(api_key=api_key)
    categorized = 0

    for i in range(0, total, BATCH_SIZE):
        batch = uncategorized.iloc[i : i + BATCH_SIZE]

        try:
            results = categorize_batch(client, batch)
        except Exception as e:
            print(f"  Error on batch {i // BATCH_SIZE + 1}: {e}")
            continue

        conn = get_conn()
        for bookmark_id, category in results.items():
            set_category(conn, bookmark_id, category)
            categorized += 1
        conn.commit()
        conn.close()

        print(f"  {categorized}/{total} done")
        time.sleep(0.5)  # rate limit courtesy

    print(f"\nCategorized {categorized} bookmarks.")


if __name__ == "__main__":
    main()
