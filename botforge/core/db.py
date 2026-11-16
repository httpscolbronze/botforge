"""
db.py — SQLite database layer for BotForge
Handles all bot config storage, retrieval and updates.
"""

import sqlite3
import uuid
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'botforge.db')


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            config      TEXT NOT NULL,
            has_docs    INTEGER DEFAULT 0,
            created_at  TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def create_bot(name: str, system_prompt: str, config: dict, has_docs: bool = False) -> str:
    bot_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'INSERT INTO bots (id, name, system_prompt, config, has_docs, created_at) VALUES (?,?,?,?,?,?)',
        (bot_id, name, system_prompt, json.dumps(config), int(has_docs), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return bot_id


def get_bot(bot_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM bots WHERE id=?', (bot_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id':            row[0],
        'name':          row[1],
        'system_prompt': row[2],
        'config':        json.loads(row[3]),
        'has_docs':      bool(row[4]),
        'created_at':    row[5],
    }


def update_bot(bot_id: str, fields: dict):
    allowed = {'name', 'system_prompt', 'config', 'has_docs'}
    updates = []
    values = []
    for k, v in fields.items():
        if k in allowed:
            updates.append(f'{k}=?')
            values.append(json.dumps(v) if k == 'config' else v)
    if not updates:
        return
    values.append(bot_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f'UPDATE bots SET {", ".join(updates)} WHERE id=?', values)
    conn.commit()
    conn.close()


def list_bots() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, has_docs, created_at FROM bots ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'has_docs': bool(r[2]), 'created_at': r[3]} for r in rows]
