"""
CRM-lite: чтение и запись заявок (таблица leads в data/metrics.db).
"""
import json
import sqlite3
from typing import Optional
from bot.config import PROJECT_DIR

DB_PATH = PROJECT_DIR / "data" / "metrics.db"

STATUS_LABELS = {
    'new':    '🆕 Новая',
    'called': '📞 Позвонили',
    'kp':     '📄 КП выслан',
    'done':   '✅ Сделка',
    'reject': '❌ Отказ',
}

_table_ok = False


def db_exists() -> bool:
    return DB_PATH.exists()


def _connect() -> sqlite3.Connection:
    global _table_ok
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    if not _table_ok:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                source     TEXT,
                name       TEXT NOT NULL,
                contact    TEXT NOT NULL,
                message    TEXT,
                items_json TEXT,
                status     TEXT NOT NULL DEFAULT 'new',
                tg_msg_id  INTEGER,
                ip         TEXT
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_leads_ts ON leads(ts)')
        conn.commit()
        _table_ok = True
    return conn


def save_lead(name: str, contact: str, source: str, message: str,
              items_json: str, ip: str) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            'INSERT INTO leads (name, contact, source, message, items_json, ip) '
            'VALUES (?,?,?,?,?,?)',
            (name, contact, source, message, items_json, ip),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def save_lead_msg_id(lead_id: int, msg_id: int) -> None:
    if not db_exists():
        return
    conn = _connect()
    try:
        conn.execute('UPDATE leads SET tg_msg_id=? WHERE id=?', (msg_id, lead_id))
        conn.commit()
    finally:
        conn.close()


def update_lead_status(lead_id: int, status: str) -> bool:
    if not db_exists():
        return False
    conn = _connect()
    try:
        cur = conn.execute('UPDATE leads SET status=? WHERE id=?', (status, lead_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_lead(lead_id: int) -> Optional[dict]:
    if not db_exists():
        return None
    conn = _connect()
    try:
        row = conn.execute('SELECT * FROM leads WHERE id=?', (lead_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_leads(status: Optional[str] = None, limit: int = 20) -> list:
    if not db_exists():
        return []
    conn = _connect()
    try:
        if status:
            rows = conn.execute(
                'SELECT * FROM leads WHERE status=? ORDER BY ts DESC LIMIT ?',
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM leads ORDER BY ts DESC LIMIT ?',
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_lead_stats() -> dict:
    if not db_exists():
        return {s: 0 for s in ('total', 'new', 'called', 'kp', 'done', 'reject')}
    conn = _connect()
    try:
        rows   = conn.execute(
            'SELECT status, count(*) as cnt FROM leads GROUP BY status'
        ).fetchall()
        counts = {r['status']: r['cnt'] for r in rows}
        total  = conn.execute('SELECT count(*) FROM leads').fetchone()[0]
        return {
            'total':  total,
            'new':    counts.get('new',    0),
            'called': counts.get('called', 0),
            'kp':     counts.get('kp',     0),
            'done':   counts.get('done',   0),
            'reject': counts.get('reject', 0),
        }
    finally:
        conn.close()
