#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_papers.py — 依据 papers_meta_verified.json（或 papers_meta.json）解析OA链接并下载 PDF。
解析顺序：PMC 直链 -> Unpaywall -> Semantic Scholar -> 出版商直链 -> Europe PMC 全文。
全部失败且用户已授权第三方时，回退尝试 Sci-Hub 镜像（HTML 内嵌 PDF 解析）。
下载后用 %PDF 魔数与文件大小校验，结果写入 papers/results.json。
"""
import json
import os
import re
import time
import urllib.parse

import requests

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
THIRD_PARTY = True  # 用户授权：OA渠道失败后尝试第三方镜像
SCI_HUB_MIRRORS = ["https://sci-hub.se/", "https://sci-hub.st/", "https://sci-hub.ru/"]
MAX_SIZE = 40_000_000


def get(url, params=None, timeout=60, stream=False, headers=None):
    return requests.get(url, params=params, headers=headers or UA, timeout=timeout,
                        stream=stream, allow_redirects=True)


def slugify(text, maxlen=48):
    text = re.sub(r"[^0-9A-Za-z]+", "-", text).strip("-").lower()
    return text[:maxlen] or "paper"


def europepmc(doi=None, pmid=None):
    try:
        q = f"EXT_ID:{pmid}" if pmid else f"DOI:{doi}"
        r = get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": q, "format": "json", "resultType": "core"})
        r.raise_for_status()
        for rec in r.json().get("resultList", {}).get("result", []):
            return rec.get("pmcid"), rec
    except Exception as e:
        print(f"    [europepmc] {e}")
    return None, None


def unpaywall(doi):
    try:
        r = get(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}",
                params={"email": EMAIL})
        r.raise_for_status()
        d = r.json()
        loc = d.get("best_oa_location") or {}
        return loc.get("url_for_pdf") or loc.get("url"), d
    except Exception as e:
        print(f"    [unpaywall] {e}")
    return None, None


def semanticscholar(doi):
    try:
        r = get("https://api.semanticscholar.org/graph/v1/paper/DOI:%s" % urllib.parse.quote(doi),
                params={"fields": "openAccessPdf,title,venue,year"})
        r.raise_for_status()
        d = r.json()
        oa = d.get("openAccessPdf") or {}
        return oa.get("url"), d
    except Exception as e:
        print(f"    [semanticscholar] {e}")
    return None, None


def publisher_urls(doi, pmcid):
    urls = []
    if pmcid:
        urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/")
    if doi.startswith("10.1038/s"):
        urls.append(f"https://www.nature.com/articles/{doi.split('/')[-1]}.pdf")
    elif doi.startswith("10.1038/"):
        urls.append(f"https://www.nature.com/articles/{doi.split('/')[-1]}.pdf")
    if doi.startswith("10.1007/") or doi.startswith("10.1038/s41598") or doi.startswith("10.1038/s42003"):
        urls.append(f"https://link.springer.com/article/{doi}.pdf")
    if doi.startswith("10.3389/"):
        urls.append(f"https://www.frontiersin.org/articles/{doi}/pdf")
    if doi.startswith("10.1155/"):
        urls.append(f"https://downloads.hindawi.com/journals/{doi.split('/')[-1]}.pdf")
    if doi.startswith("10.1002/"):
        urls.append(f"https://onlinelibrary.wiley.com/doi/pdf/{doi}")
    if doi.startswith("10.1021/"):
        urls.append(f"https://pubs.acs.org/doi/pdf/{doi}")
    if doi.startswith("10.1039/"):
        urls.append(f"https://pubs.rsc.org/en/content/articlepdf/{doi.replace('10.1039/','')}")
    if doi.startswith("10.1063/"):
        urls.append(f"https://pubs.aip.org/aip/pof/article-pdf/doi/10.1063/{doi.split('/')[-1]}.pdf")
    return urls


def download(url, dest, referer=None):
    headers = dict(UA)
    if referer:
        headers["Referer"] = referer
    try:
        with get(url, stream=True, headers=headers) as r:
            if r.status_code >= 400:
                return None, f"HTTP {r.status_code}"
            ctype = r.headers.get("Content-Type", "").lower()
            content = b""
            for chunk in r.iter_content(chunk_size=65536):
                content += chunk
                if len(content) > MAX_SIZE:
                    return None, "too large"
            if not content.startswith(b"%PDF"):
                return None, f"not pdf (ctype={ctype[:40]}, head={content[:8]!r})"
            if len(content) < 10_000:
                return None, f"too small ({len(content)} bytes)"
            with open(dest, "wb") as f:
                f.write(content)
            return dest, "ok"
    except Exception as e:
        return None, f"err {type(e).__name__}: {e}"


def try_scihub(doi, dest):
    """第三方回退：解析 Sci-Hub 页面内嵌 PDF 地址并下载。"""
    if not (THIRD_PARTY and doi):
        return None, "third-party disabled"
    for mirror in SCI_HUB_MIRRORS:
        url = mirror + urllib.parse.quote(doi, safe="")
        try:
            with get(url, stream=False) as r:
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
                # 页面里可能直接给 pdf 链接（相对/绝对）
                m = re.search(r'(https?://[^\s"\'<>]+\.pdf)', html, re.I)
            if not m:
                continue
            pdf_url = m.group(1)
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url
            elif pdf_url.startswith("/"):
                pdf_url = url.rstrip("/") + pdf_url
            got, msg = download(pdf_url, dest, referer=url)
            if got:
                return got, f"scihub::{mirror}"
            print(f"    [scihub {mirror}] {msg}")
        except Exception as e:
            print(f"    [scihub {mirror}] {e}")
    return None, "scihub failed"


def crossref_title(doi):
    try:
        r = get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")
        r.raise_for_status()
        m = r.json()["message"]
        return m.get("title", [""])[0]
    except Exception:
        return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    meta = json.load(open(META_PATH, encoding="utf-8"))
    results = {}
    if os.path.exists(RESULTS_PATH):
        results = json.load(open(RESULTS_PATH, encoding="utf-8"))

    for p in meta["papers"]:
        pid = p["id"]
        print(f"[{pid}] {p['title'][:70]}...")
        if results.get(pid, {}).get("status") == "ok" and os.path.exists(results[pid]["file"]):
            print("    already ok, skip")
            continue
        doi, pmid, pmcid = p.get("doi"), p.get("pmid"), p.get("pmcid")
        entry = {"id": pid, "doi": doi, "pmid": pmid, "pmcid": pmcid, "status": "failed",
                 "attempts": [], "file": None}
        # resolve pmcid if missing
        if pmcid is None and (doi or pmid):
            try:
                pmcid, rec = europepmc(doi, pmid)
                if pmcid:
                    entry["pmcid"] = pmcid
                    entry["europepmc_title"] = (rec or {}).get("title")
                    entry["journal"] = (rec or {}).get("journalInfo", {}).get("journal", {}).get("title")
                    entry["year"] = str((rec or {}).get("pubYear") or "")
            except Exception as e:
                print(f"    [epmc-resolve] {e}")
        if doi:
            entry["crossref_title"] = crossref_title(doi)

        candidates = []
        if entry.get("pmcid"):
            candidates += publisher_urls(doi or "10.0/0", entry["pmcid"])
        if doi:
            candidates += publisher_urls(doi, None)
        # Europe PMC full text URLs as extra candidates
        if entry.get("pmcid"):
            candidates.append(f"https://www.ncbi.nlm.nih.gov/pmc/articles/{entry['pmcid']}/pdf/")
        # verified OA PDF 与 Europe PMC 全文链接（来自 papers_meta_verified.json）
        vp = p.get("verified", {}) or {}
        _oa = vp.get("openalex") or vp.get("openalex_title_lookup") or {}
        if _oa.get("oa_pdf"):
            candidates.append(_oa["oa_pdf"])
        epmcv = vp.get("europepmc") or {}
        for u in epmcv.get("fulltexts", []):
            candidates.append(u)
        # dedupe
        seen, uniq = set(), []
        for u in candidates:
            if u and u not in seen:
                seen.add(u)
                uniq.append(u)

        dest = os.path.join(OUT_DIR, f"{pid}_{slugify(p['title'])}.pdf")
        for url in uniq:
            got, msg = download(url, dest)
            entry["attempts"].append({"url": url, "msg": msg, "file": got if got else None})
            if got:
                entry["status"] = "ok"
                entry["file"] = dest
                entry["size"] = os.path.getsize(dest)
                print(f"    OK via {url} -> {dest} ({entry['size']} bytes)")
                break
            else:
                print(f"    fail {msg}  <- {url[:90]}")
            time.sleep(0.4)
        if entry["status"] != "ok":
            got, msg = try_scihub(doi, dest)
            entry["attempts"].append({"url": "scihub-fallback", "msg": msg, "file": got if got else None})
            if got:
                entry["status"] = "ok"
                entry["file"] = dest
                entry["size"] = os.path.getsize(dest)
                print(f"    OK via third-party -> {dest} ({entry['size']} bytes)")
            else:
                print(f"    third-party failed: {msg}")
        results[pid] = entry
        json.dump(results, open(RESULTS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    ok = sum(1 for v in results.values() if v.get("status") == "ok")
    print(f"\nDONE: {ok}/{len(meta['papers'])} PDFs downloaded")


if __name__ == "__main__":
    main()
