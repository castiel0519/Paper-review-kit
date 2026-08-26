# -*- coding: utf-8 -*-
"""Probe PMC page for paper 02 PDF link."""
import re
import requests

urls = {
    "02_pmc_html": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12587405/pdf/",
}
for name, u in urls.items():
    r = requests.get(u, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    print(name, r.status_code, len(r.text))
    links = re.findall(r'href="([^"]+\.pdf[^"]*)"', r.text, re.I)
    print("pdf links:", links[:10])
    links2 = re.findall(r'"([^"]*\.pdf)"', r.text, re.I)
    print("pdf links2:", links2[:10])
