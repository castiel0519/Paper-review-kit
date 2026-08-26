# -*- coding: utf-8 -*-
"""Extract figure image URLs from Europe PMC XML for paper 02."""
import re
import requests

url = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12587405/fullTextXML"
r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml"})
xml = r.text
# graphic hrefs
hrefs = re.findall(r'href="([^"]+\.(?:png|jpg|jpeg|tif|gif))"', xml, re.I)
print("graphic hrefs:", hrefs[:20])
# xlink:href (可能带namespaces)
hrefs2 = re.findall(r'xlink:href="([^"]+)"', xml, re.I)
print("xlink hrefs:", hrefs2[:20])
# figure title captures
figs = re.findall(r'<fig\b.*?</fig>', xml, re.S)
print("num figs:", len(figs))
for i, f in enumerate(figs[:3]):
    lab = re.findall(r'<label>([^<]+)</label>', f)
    title = re.findall(r'<title>([^<]+)</title>', f)
    print("FIG", i, lab, title)
    imgs = re.findall(r'(?:href|xlink:href)="([^"]+)"', f)
    print("  imgs:", imgs[:6])
