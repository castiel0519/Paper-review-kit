#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_papers_fast.py — 并发加速版 PDF 下载器：
- 优先 Europe PMC PDF render（PMCID）→ PMC 直链 → 出版商直链 → OpenAlex OA PDF → EPMC fulltexts
- 全部失败且用户授权第三方时回退 Sci-Hub 镜像
- ThreadPoolExecutor(max_workers=6) 并发下载，绕开单连接限速
输出 papers/{ID}_{slug}.pdf + papers/results.json
"""
import json
import os
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
META_PATH = os.path.join(BASE, "papers_meta_verified.json")
if not os.path.exists(META_PATH):
    META_PATH = os.path.join(BASE, "papers_meta.json")
OUT_DIR = os.path.join(BASE, "papers")
RESULTS_PATH = os.path.join(OUT_DIR, "results.json")
EMAIL = "ml.microfluidics.review@example.com"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
SCI_HUB_MIRRORS = ["https://sci-hub.se/", "https://sci-hub.st/", "https://sci-hub.ru/"]
MAX_SIZE = 60_000_000


def get(url, params=None, timeout=45, stream=False, headers=None, verify=True):
    return requests.get(url, params=params, headers=headers or UA, timeout=timeout,
                        stream=stream, allow_redirects=True, verify=verify)


def slugify(text, maxlen=48):
    text = re.sub(r"[^0-9A-Za-z]+", "-", text).strip("-").lower()
    return text[:maxlen] or "paper"


def resolve_pmcid(p):
    if p.get("pmcid"):
        return p["pmcid"]
    doi, pmid = p.get("doi"), p.get("pmid")
    if not (doi or pmid):
        return None
    try:
        q = f"EXT_ID:{pmid}" if pmid else f"DOI:{doi}"
        r = get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": q, "format": "json", "resultType": "lite"}, timeout=25)
        r.raise_for_status()
        for rec in r.json().get("resultList", {}).get("result", []):
            return rec.get("pmcid")
    except Exception as e:
        print(f"    [resolve] {e}")
    return None


def publisher_urls(doi):
    urls = []
    if not doi:
        return urls
    if doi.startswith("10.1038/"):
        urls.append(f"https://www.nature.com/articles/{doi.split('/')[-1]}.pdf")
    if doi.startswith("10.1007/"):
        urls.append(f"https://link.springer.com/article/{doi}.pdf")
    if doi.startswith("10.3389/"):
        urls.append(f"https://www.frontiersin.org/articles/{doi}/pdf")
    if doi.startswith("10.1002/"):
        urls.append(f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}")
        urls.append(f"https://onlinelibrary.wiley.com/doi/pdf/{doi}")
    if doi.startswith("10.1021/"):
        urls.append(f"https://pubs.acs.org/doi/pdf/{doi}")
    if doi.startswith("10.1039/"):
        urls.append(f"https://pubs.rsc.org/en/content/articlepdf/{doi.replace('10.1039/', '')}")
    if doi.startswith("10.1063/"):
        urls.append(f"https://pubs.aip.org/aip/pof/article-pdf/doi/10.1063/{doi.split('/')[-1]}.pdf")
    if doi.startswith("10.1016/"):
        urls.append(f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}")
    return urls


def download(url, dest, referer=None, verify=True):
    headers = dict(UA)
    if referer:
        headers["Referer"] = referer
    try:
        with get(url, stream=True, headers=headers, verify=verify) as r:
            if r.status_code >= 400:
                return None, f"HTTP {r.status_code}"
            content = b""
            for chunk in r.iter_content(chunk_size=65536):
                content += chunk
                if len(content) > MAX_SIZE:
                    return None, "too large"
            if not content.startswith(b"%PDF"):
                return None, f"not pdf (ctype={r.headers.get('Content-Type','')[:40]})"
            if len(content) < 10_000:
                return None, f"too small ({len(content)} bytes)"
            with open(dest, "wb") as f:
                f.write(content)
            return dest, "ok"
    except Exception as e:
        return None, f"err {type(e).__name__}: {e}"


def try_scihub(doi, dest):
    if not doi:
        return None, "no doi"
    for mirror in SCI_HUB_MIRRORS:
        url = mirror + urllib.parse.quote(doi, safe="")
        try:
            r = requests.get(url, timeout=25, verify=False, headers=UA)
            if r.status_code >= 400:
                continue
            html = r.text
            m = None
            for pat in [r'<embed[^>]+src="([^"]+\.pdf[^"]*)"', r'<iframe[^>]+src="([^"]+\.pdf[^"]*)"',
                        r'<a[^>]+href="([^"]+\.pdf[^"]*)"']:
                m = re.search(pat, html, re.I)
                if m:
                    break
            if not m:
                m = re.search(r'(https?://[^\s"\'<>]+\.pdf)', html, re.I)
            if not m:
                continue
            pdf_url = m.group(1)
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url
            elif pdf_url.startswith("/"):
                pdf_url = url.rstrip("/") + pdf_url
            got, msg = download(pdf_url, dest, referer=url, verify=False)
            if got:
                return got, f"scihub::{mirror}"
            print(f"    [scihub {mirror}] {msg}")
        except Exception as e:
            print(f"    [scihub {mirror}] {e}")
    return None, "scihub failed"


def candidates_for(p):
    doi, pmcid = p.get("doi"), p.get("pmcid")
    cands = []
    if pmcid:
        cands.append(f"https://europepmc.org/articles/{pmcid}?pdf=render")
        cands.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/")
    cands += publisher_urls(doi)
    vp = p.get("verified", {}) or {}
    for key in ("openalex", "openalex_title_lookup"):
        oa = vp.get(key) or {}
        if oa.get("oa_pdf"):
            cands.append(oa["oa_pdf"])
    epmcv = vp.get("europepmc") or {}
    for u in epmcv.get("fulltexts", []):
        if u.lower().endswith(".pdf") or "pdf" in u.lower() or "render" in u.lower():
            cands.append(u)
    # dedupe
    seen, uniq = set(), []
    for u in cands:
        if u and u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def process_one(p):
    pid = p["id"]
    print(f"[{pid}] start {p['title'][:55]}", flush=True)
    entry = {"id": pid, "doi": p.get("doi"), "pmid": p.get("pmid"),
             "pmcid": p.get("pmcid"), "status": "failed", "attempts": [], "file": None}
    # resolve pmcid
    if not entry["pmcid"]:
        entry["pmcid"] = resolve_pmcid(p)
    cands = candidates_for(p)
    dest = os.path.join(OUT_DIR, f"{pid}_{slugify(p['title'])}.pdf")
    for url in cands:
        got, msg = download(url, dest)
        entry["attempts"].append({"url": url, "msg": msg, "file": got if got else None})
        if got:
            entry["status"] = "ok"
            entry["file"] = dest
            entry["size"] = os.path.getsize(dest)
            print(f"    OK via {url[:90]} ({entry['size']} bytes)", flush=True)
            return entry
        else:
            print(f"    fail {msg} <- {url[:80]}", flush=True)
        time.sleep(0.2)
    got, msg = try_scihub(p.get("doi"), dest)
    entry["attempts"].append({"url": "scihub-fallback", "msg": msg, "file": got if got else None})
    if got:
        entry["status"] = "ok"
        entry["file"] = dest
        entry["size"] = os.path.getsize(dest)
        print(f"    OK via third-party ({entry['size']} bytes)", flush=True)
    else:
        print(f"    FAILED: {msg}", flush=True)
    return entry


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    meta = json.load(open(META_PATH, encoding="utf-8"))
    papers = meta["papers"]
    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(process_one, p): p for p in papers}
        for fut in as_completed(futs):
            entry = fut.result()
            results[entry["id"]] = entry
            json.dump(results, open(RESULTS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ok = sum(1 for v in results.values() if v.get("status") == "ok")
    print(f"\nDONE: {ok}/{len(papers)} PDFs downloaded")


if __name__ == "__main__":
    main()
