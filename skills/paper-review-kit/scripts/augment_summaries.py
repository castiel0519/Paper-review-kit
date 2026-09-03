#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
augment_summaries.py — 从 Europe PMC / Crossref 把英文摘要与权威题录回填到 summaries/*.json，
节省人工输入 abstract_en 的时间；中文精读字段留待人工填写。
"""
import os
import re
import time
import urllib.parse

import requests

from prk_config import (
    cfg_get, load_papers_meta, output_dir, parse_project_arg, read_json, write_json,
)


def make_ua(cfg):
    mailto = cfg_get(cfg, "apis", "mailto", default="researcher@example.com")
    agent = cfg_get(cfg, "apis", "user_agent", default=f"paper-review-kit/1.0 (mailto:{mailto})")
    return {"User-Agent": agent, "Accept": "application/json"}


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def epmc_abstract(cfg, doi, pmid):
    try:
        q = f"EXT_ID:{pmid}" if pmid else f'DOI:"{doi}"'
        r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                         params={"query": q, "format": "json", "resultType": "core"},
                         headers=make_ua(cfg), timeout=30)
        r.raise_for_status()
        for rec in r.json().get("resultList", {}).get("result", []):
            ab = strip_html(rec.get("abstractText") or "")
            return ab, rec
    except Exception as e:
        print(f"    [epmc] {e}")
    return None, None


def crossref_abstract(cfg, doi):
    try:
        r = requests.get("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                         headers=make_ua(cfg), timeout=30)
        r.raise_for_status()
        m = r.json()["message"]
        return strip_html(m.get("abstract") or "")
    except Exception as e:
        print(f"    [crossref] {e}")
        return None


def main():
    cfg, args = parse_project_arg()
    meta = load_papers_meta(cfg, verified=True, required=False)
    if meta is None:
        meta = load_papers_meta(cfg, verified=False)
    papers = {str(p["id"]): p for p in meta["papers"]}
    sum_dir = output_dir(cfg, "summaries")
    if not sum_dir.is_dir():
        print("summaries/ 不存在，请先运行 init_summaries.py")
        return
    for fn in sorted(sum_dir.iterdir()):
        if fn.suffix != ".json":
            continue
        s = read_json(fn)
        if not isinstance(s, dict):
            continue
        pid = str(s.get("id"))
        p = papers.get(pid, {})
        doi, pmid = p.get("doi"), p.get("pmid")
        updated = False
        if not s.get("abstract_en") and doi:
            ab, rec = epmc_abstract(cfg, doi, pmid)
            if not ab:
                ab = crossref_abstract(cfg, doi)
            if ab:
                s["abstract_en"] = ab
                updated = True
        for k, src in [("journal", p.get("journal")), ("year", p.get("year")),
                       ("doi", doi), ("pmid", pmid), ("pmcid", p.get("pmcid"))]:
            if src and not s.get(k):
                s[k] = src
                updated = True
        if updated:
            write_json(fn, s)
            print(f"[{pid}] abstract filled ({len(s.get('abstract_en',''))} chars)")
        time.sleep(0.2)
    print("augment done")


if __name__ == "__main__":
    main()
