
"""
db.py — SQLite database layer for BotForge
Handles all bot config storage, retrieval and updates.
"""

import sqlite3
import uuid
import json
from pathlib import Path
from datetime import datetime
from contextlib import closing

DB_PATH = Path(__file__).resolve().parent.parent / "botforge.db"


def get_connection():
    """Create a database connection."""
    return sqlite3.connect(DB_PATH, timeout=10)


def init_db():
    """Initialize the database."""
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bots (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    system_prompt TEXT NOT NULL,
                    config TEXT NOT NULL,
                    has_docs INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)


def create_bot(
    name: str,
    system_prompt: str,
    config: dict,
    has_docs: bool = False
) -> str:
    """Create a bot and return its unique ID."""

    bot_id = str(uuid.uuid4())

    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO bots
                (id, name, system_prompt, config, has_docs, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    bot_id,
                    name,
                    system_prompt,
                    json.dumps(config),
                    int(has_docs),
                    datetime.now().isoformat()
                )
            )

    return bot_id


def get_bot(bot_id: str) -> dict | None:
    """Retrieve a bot by ID."""

    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM bots WHERE id = ?",
            (bot_id,)
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "system_prompt": row[2],
        "config": json.loads(row[3]),
        "has_docs": bool(row[4]),
        "created_at": row[5]
    }


def update_bot(bot_id: str, fields: dict):
    """Update permitted bot fields."""

    allowed = {
        "name",
        "system_prompt",
        "config",
        "has_docs"
    }

    updates = []
    values = []

    for key, value in fields.items():

        if key not in allowed:
            continue

        if key == "config":
            value = json.dumps(value)

        elif key == "has_docs":
            value = int(bool(value))

        updates.append(f"{key} = ?")
        values.append(value)

    if not updates:
        return

    values.append(bot_id)

    query = f"""
        UPDATE bots
        SET {", ".join(updates)}
        WHERE id = ?
    """

    with closing(get_connection()) as conn:
        with conn:
            conn.execute(query, values)


def list_bots() -> list[dict]:
    """Return all bots, newest first."""

    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT id, name, has_docs, created_at
            FROM bots
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "has_docs": bool(row[2]),
            "created_at": row[3]
        }
        for row in rows
    ]
