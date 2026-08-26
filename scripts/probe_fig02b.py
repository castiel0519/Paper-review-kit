# -*- coding: utf-8 -*-
"""Probe Europe PMC figure image serving patterns for paper 02."""
import requests

cands = [
    "https://europepmc.org/articles/PMC12587405/bin/d5lc00216h-f1.jpg",
    "https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC12587405&blobtype=figure&id=d5lc00216h-f1.jpg",
    "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12587405/fullTextXML",
]
for u in cands:
    try:
        r = requests.get(u, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        print(u[:80], r.status_code, r.headers.get("Content-Type", ""), len(r.content), r.content[:10])
    except Exception as e:
        print(u[:80], "ERR", type(e).__name__, str(e)[:60])
