#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
augment_summaries.py — 从 Europe PMC / Crossref 把英文摘要与权威题录回填到 summaries/*.json，
节省人工输入 abstract_en 的时间；中文精读字段留待人工填写。
"""
import json
import os
import re
import time
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SUM_DIR = os.path.join(BASE, "summaries")
META = os.path.join(BASE, "papers_meta_verified.json")

UA = {"User-Agent": "ml-microfluidics-review/1.0 (mailto:ml.microfluidics.review@example.com)",
      "Accept": "application/json"}


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def epmc_abstract(doi, pmid):
    try:
        q = f"EXT_ID:{pmid}" if pmid else f'DOI:"{doi}"'
        r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                         params={"query": q, "format": "json", "resultType": "core"},
                         headers=UA, timeout=30)
        r.raise_for_status()
        for rec in r.json().get("resultList", {}).get("result", []):
            ab = strip_html(rec.get("abstractText") or "")
            return ab, rec
    except Exception as e:
        print(f"    [epmc] {e}")
    return None, None


def crossref_abstract(doi):
    try:
        r = requests.get("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                         headers=UA, timeout=30)
        r.raise_for_status()
        m = r.json()["message"]
        ab = m.get("abstract") or ""
        return strip_html(ab)
    except Exception as e:
        print(f"    [crossref] {e}")
        return None


def main():
    meta = json.load(open(META, encoding="utf-8"))
    papers = {p["id"]: p for p in meta["papers"]}
    for fn in sorted(os.listdir(SUM_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(SUM_DIR, fn)
        s = json.load(open(path, encoding="utf-8"))
        pid = s.get("id")
        p = papers.get(pid, {})
        doi, pmid = p.get("doi"), p.get("pmid")
        updated = False
        if not s.get("abstract_en") and doi:
            ab, rec = epmc_abstract(doi, pmid)
            if not ab:
                ab = crossref_abstract(doi)
            if ab:
                s["abstract_en"] = ab
                updated = True
        # 题录补全
        for k, src in [("journal", p.get("journal")), ("year", p.get("year")),
                       ("doi", doi), ("pmid", pmid), ("pmcid", p.get("pmcid"))]:
            if src and not s.get(k):
                s[k] = src
                updated = True
        if updated:
            json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"[{pid}] abstract filled ({len(s.get('abstract_en',''))} chars)")
        time.sleep(0.2)
    print("augment done")


if __name__ == "__main__":
    main()
