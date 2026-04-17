"""
Утилиты форматирования для отображения данных в боте.
"""


def format_price(price) -> str:
    """Форматирует цену: 144000 → '144 000 ₽/т', None → 'По запросу'."""
    if price is None:
        return "По запросу"
    try:
        p = int(price)
        return f"{p:,} ₽".replace(",", "\u202f")
    except (TypeError, ValueError):
        return "По запросу"
