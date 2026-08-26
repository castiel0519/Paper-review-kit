#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_meta.py — 核验 papers_meta.json 中 20 篇候选论文的元数据与OA状态：
  CrossRef(DOI) -> 标题/期刊/年份/作者
  OpenAlex(title 或 DOI) -> DOI/期刊/年份/被引/OA pdf 链接
  Europe PMC(pmcid/pmid) -> PMCID/全文本链接
  Unpaywall(DOI) -> best_oa_location url_for_pdf
输出 papers_meta_verified.json（含 verified 字段与 oa_info）。
"""
import json
import os
import sys
import time
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
META = os.path.join(BASE, "papers_meta.json")
OUT = os.path.join(BASE, "papers_meta_verified.json")
EMAIL = "ml.microfluidics.review@example.com"
UA = {"User-Agent": "ml-microfluidics-review/1.0 (mailto:%s)" % EMAIL,
      "Accept": "application/json"}


def get(url, params=None, timeout=45):
    r = requests.get(url, params=params, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.json()


def crossref(doi):
    try:
        m = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
        return {
            "title": (m.get("title") or [""])[0],
            "journal": ((m.get("container-title") or [""])[0]),
            "year": None,
            "authors": "; ".join(
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in (m.get("author") or [])[:12]),
        }
    except Exception as e:
        print(f"    [crossref] {e}")
        return None


def openalex_by_doi(doi):
    try:
        w = get("https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi),
                params={"mailto": EMAIL, "select": "id,doi,title,display_name,publication_year,cited_by_count,"
                                                   "open_access,best_oa_location,primary_location"})
        return w
    except Exception as e:
        print(f"    [openalex-doi] {e}")
        return None


def openalex_by_title(title):
    try:
        d = get("https://api.openalex.org/works",
                params={"search": title, "per-page": 5, "sort": "cited_by_count:desc",
                        "mailto": EMAIL, "select": "id,doi,title,display_name,publication_year,"
                                                   "cited_by_count,open_access,best_oa_location,"
                                                   "primary_location"})
        return d.get("results", [])
    except Exception as e:
        print(f"    [openalex-title] {e}")
        return None


def europepmc_by_id(pmcid=None, pmid=None):
    try:
        q = f"PMCID:{pmcid}" if pmcid else f"EXT_ID:{pmid}"
        d = get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": q, "format": "json", "resultType": "core"})
        for r in d.get("resultList", {}).get("result", []):
            return r
    except Exception as e:
        print(f"    [europepmc] {e}")
    return None


def unpaywall(doi):
    try:
        d = get(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}",
                params={"email": EMAIL})
        loc = d.get("best_oa_location") or {}
        return {"is_oa": d.get("is_oa"), "oa_status": d.get("oa_status"),
                "pdf_url": loc.get("url_for_pdf"), "landing": loc.get("url"),
                "version": loc.get("version")}
    except Exception as e:
        print(f"    [unpaywall] {e}")
        return None


def main():
    meta = json.load(open(META, encoding="utf-8"))
    out = {"project": meta["project"], "title": meta["title"], "papers": []}
    for p in meta["papers"]:
        pid = p["id"]
        print(f"[{pid}] {p['title'][:60]}")
        v = dict(p)
        v["verified"] = {}
        cr = crossref(p["doi"]) if p.get("doi") else None
        if cr:
            v["verified"]["crossref"] = cr
            if not v.get("journal"):
                v["journal"] = cr.get("journal")
            if not v.get("authors"):
                v["authors"] = cr.get("authors")
            if not v.get("year"):
                v["year"] = cr.get("year")
        oa = None
        if p.get("doi"):
            w = openalex_by_doi(p["doi"])
            if w:
                oa = w
                loc = w.get("best_oa_location") or {}
                v["verified"]["openalex"] = {
                    "title": w.get("title") or w.get("display_name"),
                    "journal": ((w.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                    "year": w.get("publication_year"),
                    "citations": w.get("cited_by_count"),
                    "is_oa": (w.get("open_access") or {}).get("is_oa"),
                    "oa_status": (w.get("open_access") or {}).get("oa_status"),
                    "oa_pdf": loc.get("pdf_url") or "",
                    "oa_landing": loc.get("landing_page_url") or "",
                }
                if not v.get("journal"):
                    v["journal"] = v["verified"]["openalex"]["journal"]
                if not v.get("year"):
                    v["year"] = v["verified"]["openalex"]["year"]
        if not v.get("doi"):
            rows = openalex_by_title(p["title"]) or []
            for r in rows:
                t = (r.get("title") or "").lower()
                if t and t[:60] == p["title"].lower()[:60]:
                    doi = (r.get("doi") or "").replace("https://doi.org/", "")
                    if doi:
                        v["doi"] = doi
                    v["verified"]["openalex_title_lookup"] = {
                        "title": r.get("title"), "journal": ((r.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                        "year": r.get("publication_year"), "citations": r.get("cited_by_count"),
                        "is_oa": (r.get("open_access") or {}).get("is_oa"),
                        "oa_status": (r.get("open_access") or {}).get("oa_status"),
                        "oa_pdf": ((r.get("best_oa_location") or {}).get("pdf_url") or ""),
                    }
                    break
        if p.get("pmcid") or p.get("pmid"):
            epmc = europepmc_by_id(p.get("pmcid"), p.get("pmid"))
            if epmc:
                v["verified"]["europepmc"] = {
                    "title": epmc.get("title"), "journal": (epmc.get("journalInfo", {}).get("journal", {}) or {}).get("title", ""),
                    "year": epmc.get("pubYear"), "doi": epmc.get("doi"), "pmid": epmc.get("pmid"),
                    "pmcid": epmc.get("pmcid"), "fulltexts": [u.get("url") for u in epmc.get("fullTextUrlList", {}).get("fullTextUrl", [])],
                }
                if not v.get("journal"):
                    v["journal"] = v["verified"]["europepmc"]["journal"]
                if not v.get("year"):
                    v["year"] = v["verified"]["europepmc"]["year"]
                if not v.get("doi"):
                    v["doi"] = epmc.get("doi")
        if p.get("doi"):
            up = unpaywall(p["doi"])
            if up:
                v["verified"]["unpaywall"] = up
        out["papers"].append(v)
        time.sleep(0.3)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n_done = sum(1 for p in out["papers"] if p.get("doi"))
    print(f"\nDONE: {n_done}/{len(out['papers'])} DOI resolved -> {OUT}")


if __name__ == "__main__":
    main()
