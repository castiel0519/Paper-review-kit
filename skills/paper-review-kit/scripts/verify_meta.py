#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_meta.py — 核验 papers_meta.json 中论文的元数据与 OA 状态：
  CrossRef(DOI) -> 标题/期刊/年份/作者
  OpenAlex(title 或 DOI) -> DOI/期刊/年份/被引/OA pdf 链接
  Europe PMC(pmcid/pmid) -> PMCID/全文本链接
  Unpaywall(DOI) -> best_oa_location url_for_pdf
输出 papers_meta_verified.json（含 verified 字段与 oa_info）。
"""
import argparse
import time
import urllib.parse

import requests

from prk_config import (
    cfg_get, load_config, load_papers_meta, parse_project_arg, project_path, write_json,
)
from prk_schema import validate_meta


def _year_from_crossref(m):
    """Crossref 的发布日期字段优先级（修复旧版 year=None 的问题）。"""
    for key in ("published-print", "published-online", "published", "issued", "created"):
        part = m.get(key) or {}
        parts = part.get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                continue
    return None


def make_ua(cfg):
    mailto = cfg_get(cfg, "apis", "mailto", default="researcher@example.com")
    agent = cfg_get(cfg, "apis", "user_agent", default=f"paper-review-kit/1.0 (mailto:{mailto})")
    return {"User-Agent": agent, "Accept": "application/json"}


def get(cfg, url, params=None, timeout=None):
    timeout = timeout or cfg_get(cfg, "download", "timeout", default=45)
    r = requests.get(url, params=params, headers=make_ua(cfg), timeout=timeout)
    r.raise_for_status()
    return r.json()


def crossref(cfg, doi):
    try:
        m = get(cfg, "https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
        return {
            "title": (m.get("title") or [""])[0],
            "journal": ((m.get("container-title") or [""])[0]),
            "year": _year_from_crossref(m),
            "authors": "; ".join(
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in (m.get("author") or [])[:12]),
        }
    except Exception as e:
        print(f"    [crossref] {e}")
        return None


def openalex_by_doi(cfg, doi):
    try:
        mailto = cfg_get(cfg, "apis", "mailto", default="researcher@example.com")
        return get(cfg, "https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi),
                   params={"mailto": mailto,
                           "select": "id,doi,title,display_name,publication_year,cited_by_count,"
                                     "open_access,best_oa_location,primary_location"})
    except Exception as e:
        print(f"    [openalex-doi] {e}")
        return None


def openalex_by_title(cfg, title):
    try:
        mailto = cfg_get(cfg, "apis", "mailto", default="researcher@example.com")
        d = get(cfg, "https://api.openalex.org/works",
                params={"search": title, "per-page": 5, "sort": "cited_by_count:desc",
                        "mailto": mailto,
                        "select": "id,doi,title,display_name,publication_year,"
                                  "cited_by_count,open_access,best_oa_location,"
                                  "primary_location"})
        return d.get("results", [])
    except Exception as e:
        print(f"    [openalex-title] {e}")
        return None


def europepmc_by_id(cfg, pmcid=None, pmid=None):
    if not (pmcid or pmid):
        return None
    try:
        q = f"PMCID:{pmcid}" if pmcid else f"EXT_ID:{pmid}"
        d = get(cfg, "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": q, "format": "json", "resultType": "core"})
        for r in d.get("resultList", {}).get("result", []):
            return r
    except Exception as e:
        print(f"    [europepmc] {e}")
    return None


def unpaywall(cfg, doi):
    try:
        d = get(cfg, f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}",
                params={"email": cfg_get(cfg, "apis", "mailto", default="researcher@example.com")})
        loc = d.get("best_oa_location") or {}
        return {"is_oa": d.get("is_oa"), "oa_status": d.get("oa_status"),
                "pdf_url": loc.get("url_for_pdf"), "landing": loc.get("url"),
                "version": loc.get("version")}
    except Exception as e:
        print(f"    [unpaywall] {e}")
        return None


def fill_from_verified(v, field_map, source):
    if not source:
        return
    for dst, src in field_map.items():
        if not v.get(dst) and source.get(src):
            v[dst] = source[src]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    cfg, args = parse_project_arg(parser)
    meta = load_papers_meta(cfg)
    errors, _ = validate_meta(meta)
    if errors:
        raise SystemExit("papers_meta.json 校验失败：\n  - " + "\n  - ".join(errors))

    out = {
        "project": meta.get("project", cfg_get(cfg, "project", "slug")),
        "title": meta.get("title", cfg_get(cfg, "project", "title")),
        "range": meta.get("range", cfg_get(cfg, "project", "range")),
        "papers": [],
    }
    for p in meta["papers"]:
        pid = p.get("id")
        print(f"[{pid}] {str(p.get('title', ''))[:60]}")
        v = dict(p)
        v["verified"] = {}

        cr = crossref(cfg, p["doi"]) if p.get("doi") else None
        if cr:
            v["verified"]["crossref"] = cr
            fill_from_verified(v, {
                "journal": "journal", "authors": "authors", "year": "year",
            }, cr)

        if p.get("doi"):
            w = openalex_by_doi(cfg, p["doi"])
            if w:
                loc = w.get("best_oa_location") or {}
                source = ((w.get("primary_location") or {}).get("source") or {})
                v["verified"]["openalex"] = {
                    "title": w.get("title") or w.get("display_name"),
                    "journal": source.get("display_name", ""),
                    "year": w.get("publication_year"),
                    "citations": w.get("cited_by_count"),
                    "is_oa": (w.get("open_access") or {}).get("is_oa"),
                    "oa_status": (w.get("open_access") or {}).get("oa_status"),
                    "oa_pdf": loc.get("pdf_url") or "",
                    "oa_landing": loc.get("landing_page_url") or "",
                }
                fill_from_verified(v, {
                    "journal": "journal", "year": "year",
                }, v["verified"]["openalex"])

        if not v.get("doi"):
            rows = openalex_by_title(cfg, p["title"]) or []
            for r in rows:
                t = (r.get("title") or "").strip().lower()
                src = (p.get("title") or "").strip().lower()
                if t and t[:80] == src[:80]:
                    doi = (r.get("doi") or "").replace("https://doi.org/", "")
                    if doi:
                        v["doi"] = doi
                    loc = r.get("best_oa_location") or {}
                    source = ((r.get("primary_location") or {}).get("source") or {})
                    v["verified"]["openalex_title_lookup"] = {
                        "title": r.get("title"),
                        "journal": source.get("display_name", ""),
                        "year": r.get("publication_year"),
                        "citations": r.get("cited_by_count"),
                        "is_oa": (r.get("open_access") or {}).get("is_oa"),
                        "oa_status": (r.get("open_access") or {}).get("oa_status"),
                        "oa_pdf": loc.get("pdf_url") or "",
                    }
                    fill_from_verified(v, {
                        "journal": "journal", "year": "year",
                    }, v["verified"]["openalex_title_lookup"])
                    break

        if p.get("pmcid") or p.get("pmid"):
            epmc = europepmc_by_id(cfg, p.get("pmcid"), p.get("pmid"))
            if epmc:
                jinfo = (epmc.get("journalInfo") or {}).get("journal") or {}
                v["verified"]["europepmc"] = {
                    "title": epmc.get("title"),
                    "journal": jinfo.get("title", ""),
                    "year": epmc.get("pubYear"),
                    "doi": epmc.get("doi"),
                    "pmid": epmc.get("pmid"),
                    "pmcid": epmc.get("pmcid"),
                    "fulltexts": [u.get("url") for u in
                                  (epmc.get("fullTextUrlList") or {}).get("fullTextUrl", [])],
                }
                fill_from_verified(v, {
                    "journal": "journal", "year": "year", "doi": "doi",
                }, v["verified"]["europepmc"])

        if p.get("doi"):
            up = unpaywall(cfg, p["doi"])
            if up:
                v["verified"]["unpaywall"] = up

        out["papers"].append(v)
        time.sleep(0.3)

    out_path = project_path(cfg, "papers_meta_verified.json")
    write_json(out_path, out)
    n_done = sum(1 for p in out["papers"] if p.get("doi"))
    print(f"\nDONE: {n_done}/{len(out['papers'])} DOI resolved -> {out_path}")


if __name__ == "__main__":
    main()
