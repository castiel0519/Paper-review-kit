# -*- coding: utf-8 -*-
"""Probe Europe PMC PDF render endpoints for paper 02."""
import requests

cands = [
    "https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC12587405&blobtype=pdf",
    "https://europepmc.org/api/fulltextRepo?pprId=PMC12587405&ftType=pdf",
    "https://europepmc.org/articles/PMC12587405?pdf=render",
    "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12587405/fullTextXML",
]
for u in cands:
    try:
        r = requests.get(u, timeout=30, headers={"User-Agent": "Mozilla/5.0",
                                                 "Accept": "application/pdf,application/xml,text/html"})
        print(u.split("?")[0].split("//")[-1], r.status_code, r.headers.get("Content-Type", ""), len(r.content), r.content[:12])
    except Exception as e:
        print(u, "ERR", type(e).__name__, str(e)[:80])
