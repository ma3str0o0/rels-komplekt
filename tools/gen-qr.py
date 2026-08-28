#!/usr/bin/env python3
"""Генератор QR-кода бота MAX для футера — детерминированный SVG из URL.

Зависимость: segno (чистый Python, без Pillow и системных библиотек).
В репозиторий НЕ тянется — ставится отдельно:

    python3 -m venv .venv && .venv/bin/pip install segno
    .venv/bin/python tools/gen-qr.py

Коммитится только результат — assets/img/qr-max-bot.svg.
"""
import os
import sys

import segno

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ссылка на бота в мессенджере MAX. Проверена владельцем 2026-08-28,
# открывается и на мобильном, и на десктопе.
# ПРИ СМЕНЕ ССЫЛКИ ОБЯЗАТЕЛЬНО ПЕРЕГЕНЕРИРОВАТЬ SVG ЭТИМ СКРИПТОМ.
#
# ВНИМАНИЕ: при error='Q' version 3 вмещает 32 байта.
# Текущий URL = 31 символ → запас 1 символ.
# Более длинный URL уйдёт на version 4 (матрица 33x33):
# код станет плотнее и хуже читаться при том же CSS-размере.
# Если URL удлиняется — либо снижай error до 'M', либо увеличивай
# отображаемый размер в CSS, либо используй короткий редирект.
URL = "https://max.ru/id6671083158_bot"

OUT = os.path.join(ROOT, "assets/img/qr-max-bot.svg")

# Уровень коррекции Q — запас восстановления 25%. Достаётся бесплатно:
# version и физический размер матрицы те же, что были бы при M.
ERROR_LEVEL = "q"
# Quiet zone: 4 модуля по стандарту ISO/IEC 18004. Без неё сканеры не находят код.
BORDER = 4

# boost_error=False — уровень задан явно в ERROR_LEVEL, не даём segno
# менять его молча. Вывод должен быть предсказуем.
qr = segno.make(URL, error=ERROR_LEVEL, micro=False, boost_error=False)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
qr.save(
    OUT,
    kind="svg",
    scale=1,
    border=BORDER,
    dark="#000000",
    # Светлые модули заливаем белым, а не оставляем прозрачными: футер тёмный
    # в обеих темах, на прозрачном фоне код станет чёрным по чёрному.
    light="#FFFFFF",
    svgclass=None,
    lineclass=None,
    xmldecl=False,
    svgns=True,
    omitsize=True,          # без width/height — размер задаёт CSS
    unit=None,
    nl=False,
)

size = os.path.getsize(OUT)
print(f"{OUT}  version={qr.version}  error={qr.error}  {size} B")
print(f"URL: {URL}")
