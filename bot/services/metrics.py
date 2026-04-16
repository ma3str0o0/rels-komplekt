"""
Чтение и агрегация метрик из data/metrics.db
"""
import json
import sqlite3
from pathlib import Path
from bot.config import PROJECT_DIR

DB_PATH = PROJECT_DIR / "data" / "metrics.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def db_exists() -> bool:
    return DB_PATH.exists()


def get_stats(days: int = 1) -> dict:
    """Агрегированная статистика за последние N дней."""
    if not db_exists():
        return _empty_stats(days)
    conn = _connect()
    try:
        interval = f"-{days} days"

        total_views = conn.execute(
            "SELECT count(*) FROM events WHERE event='page_view' AND ts >= datetime('now',?)",
            (interval,)
        ).fetchone()[0]

        unique_ips = conn.execute(
            "SELECT count(DISTINCT ip) FROM events WHERE event='page_view' AND ts >= datetime('now',?)",
            (interval,)
        ).fetchone()[0]

        # Просмотры по страницам (топ-5)
        page_rows = conn.execute(
            "SELECT page, count(*) as cnt FROM events "
            "WHERE event='page_view' AND ts >= datetime('now',?) AND page IS NOT NULL "
            "GROUP BY page ORDER BY cnt DESC LIMIT 5",
            (interval,)
        ).fetchall()
        page_views = {r['page']: r['cnt'] for r in page_rows}

        # Топ-3 продукта
        top_rows = conn.execute(
            "SELECT product_id, count(*) as cnt FROM events "
            "WHERE event='product_view' AND ts >= datetime('now',?) AND product_id IS NOT NULL "
            "GROUP BY product_id ORDER BY cnt DESC LIMIT 3",
            (interval,)
        ).fetchall()
        top_products = [(r['product_id'], r['cnt']) for r in top_rows]

        # Подсчёт событий
        event_rows = conn.execute(
            "SELECT event, count(*) as cnt FROM events "
            "WHERE ts >= datetime('now',?) GROUP BY event",
            (interval,)
        ).fetchall()
        events = {r['event']: r['cnt'] for r in event_rows}

        # Поисковые запросы (топ-5)
        search_rows = conn.execute(
            "SELECT extra FROM events "
            "WHERE event='catalog_search' AND ts >= datetime('now',?) AND extra IS NOT NULL",
            (interval,)
        ).fetchall()
        queries: dict = {}
        for row in search_rows:
            try:
                q = json.loads(row['extra']).get('query', '')
                if q:
                    queries[q] = queries.get(q, 0) + 1
            except Exception:
                pass
        searches = sorted(queries.items(), key=lambda x: -x[1])[:5]

        return {
            'period':       _period_label(days),
            'views':        total_views,
            'unique_ips':   unique_ips,
            'page_views':   page_views,
            'top_products': top_products,
            'events':       events,
            'forms':        events.get('form_submit', 0) + events.get('order_submit', 0),
            'phone_clicks': events.get('phone_click', 0),
            'email_clicks': events.get('email_click', 0),
            'calc_uses':    events.get('calculator_use', 0),
            'pdf_downloads':events.get('pdf_download', 0),
            'searches':     searches,
        }
    finally:
        conn.close()


def get_top_products(days: int = 7, limit: int = 10) -> list[tuple]:
    """Топ товаров по product_view. Возвращает [(product_id, count), ...]"""
    if not db_exists():
        return []
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT product_id, count(*) as cnt FROM events "
            "WHERE event='product_view' AND ts >= datetime('now',?) AND product_id IS NOT NULL "
            "GROUP BY product_id ORDER BY cnt DESC LIMIT ?",
            (f"-{days} days", limit)
        ).fetchall()
        return [(r['product_id'], r['cnt']) for r in rows]
    finally:
        conn.close()


def _period_label(days: int) -> str:
    if days == 1:
        return "сегодня"
    if days == 7:
        return "7 дней"
    return f"{days} дней"


def _empty_stats(days: int) -> dict:
    return {
        'period': _period_label(days), 'views': 0, 'unique_ips': 0,
        'page_views': {}, 'top_products': [], 'events': {},
        'forms': 0, 'phone_clicks': 0, 'email_clicks': 0,
        'calc_uses': 0, 'pdf_downloads': 0, 'searches': [],
    }
