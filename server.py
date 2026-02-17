#!/usr/bin/env python3
"""Local API server that receives bookmarks from the Chrome extension."""

from flask import Flask, request, jsonify
from flask_cors import CORS

from lib.db import init_db, get_conn, upsert_many, get_stats

app = Flask(__name__)
CORS(app)

init_db()


@app.route("/api/bookmarks", methods=["POST"])
def receive_bookmarks():
    bookmarks = request.get_json()
    if not isinstance(bookmarks, list):
        return jsonify({"error": "Expected a JSON array"}), 400

    conn = get_conn()
    count = upsert_many(conn, bookmarks)
    conn.close()

    stats = get_stats()
    print(f"Received {count} bookmarks. Total in DB: {stats['total']}")

    return jsonify({"count": count, "total": stats["total"]})


@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())


if __name__ == "__main__":
    print("link_squared server running on http://localhost:7799")
    print("Waiting for bookmarks from the extension...")
    app.run(port=7799, debug=False)
