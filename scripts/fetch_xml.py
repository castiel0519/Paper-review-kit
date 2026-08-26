# -*- coding: utf-8 -*-
"""Fetch Europe PMC fullTextXML for paper 02 (RSC Lab Chip, PDF blocked) -> papers_txt/02.txt + digest."""
import json
import os
import re
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(BASE, "papers_txt")
os.makedirs(TXT, exist_ok=True)

PMCID = "PMC12587405"
url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML"
r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml"})
print("status", r.status_code, "len", len(r.content))
xml = r.text
# 简单去标签：保留段落与标题
xml = re.sub(r"<(title|h\d|p|fig-caption|[a-z]+-caption)>", "\n", xml)
text = re.sub(r"<[^>]+>", " ", xml)
text = re.sub(r"&lt;", "<", text)
text = re.sub(r"&gt;", ">", text)
text = re.sub(r"&amp;", "&", text)
text = re.sub(r"\s+", " ", text).strip()
out = os.path.join(TXT, "02.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("===PAGE 1===\n" + text + "\n")
print("wrote", out, len(text))

# digest
dig = os.path.join(BASE, "digests", "02.md")
with open(dig, "w", encoding="utf-8") as f:
    f.write("### 02 digest\n\n## XML full text (Europe PMC)\n" + text[:12000] + "\n")
print("wrote", dig)
