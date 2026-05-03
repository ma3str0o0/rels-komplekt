#!/usr/bin/env python3
"""Генератор sitemap.xml — статические страницы + 158 продуктовых URL из catalog.json."""
import json
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://rels-komplekt.ru"
DATE = datetime.date.today().isoformat()

PAGES = [
    ("/", "weekly", "1.0"),
    ("/catalog.html", "weekly", "0.9"),
    ("/calculator.html", "monthly", "0.7"),
    ("/contacts.html", "yearly", "0.6"),
    ("/order.html", "monthly", "0.5"),
    ("/privacy.html", "yearly", "0.3"),
    ("/about.html", "yearly", "0.5"),
    ("/rails-reference.html", "monthly", "0.7"),
]

with open(os.path.join(ROOT, "data/catalog.json"), encoding="utf-8") as f:
    catalog = json.load(f)

urls = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
]

for path, freq, prio in PAGES:
    urls.append(
        f"  <url><loc>{SITE}{path}</loc><lastmod>{DATE}</lastmod>"
        f"<changefreq>{freq}</changefreq><priority>{prio}</priority></url>"
    )

for item in catalog:
    pid = item.get("id") or item.get("page_name")
    if not pid:
        continue
    urls.append(
        f'  <url><loc>{SITE}/product.html?id={pid}</loc><lastmod>{DATE}</lastmod>'
        f'<changefreq>monthly</changefreq><priority>0.6</priority></url>'
    )

urls.append("</urlset>")

out = os.path.join(ROOT, "sitemap.xml")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(urls) + "\n")

print(f"sitemap.xml: {len(PAGES)} static + {len(catalog)} products = {len(PAGES) + len(catalog)} URLs")
print(f"  → {out}")
