#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_papers_fast.py — 并发 PDF 下载器：
- 候选顺序：papers_meta 中该论文的 manual_urls/download_overrides →
  Europe PMC PDF render（PMCID）→ PMC 直链 → 出版商直链 → OpenAlex OA PDF → EPMC fulltexts
- 仅当 project.yml compliance.allow_third_party=true 或命令行显式
  --allow-third-party 时，才允许 Sci-Hub 回退；默认关闭。
- ThreadPoolExecutor 并发下载；流式写临时文件，成功后原子改名。
输出 papers/{ID}_{slug}.pdf + papers/results.json
"""
import argparse
import os
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from prk_config import (
    cfg_get, load_config, load_papers_meta, output_dir, parse_project_arg, project_path, write_json,
)
from prk_schema import validate_meta

SCI_HUB_MIRRORS = ["https://sci-hub.se/", "https://sci-hub.st/", "https://sci-hub.ru/"]

# 被其他脚本 import 时也需要能工作；这两个默认值会在 main/process 调用时被 cfg 覆盖。
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def make_headers(cfg=None, referer=None, json_api=False):
    headers = {
        "User-Agent": cfg_get(cfg, "apis", "user_agent", default=UA["User-Agent"]),
        "Accept": "application/json" if json_api else
                  "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def get(cfg, url, params=None, timeout=None, stream=False, headers=None, verify=True):
    timeout = timeout or cfg_get(cfg, "download", "timeout", default=45)
    return requests.get(url, params=params, headers=headers or make_headers(cfg),
                        timeout=timeout, stream=stream, allow_redirects=True, verify=verify)


def slugify(text, maxlen=48):
    text = re.sub(r"[^0-9A-Za-z]+", "-", text).strip("-").lower()
    return text[:maxlen] or "paper"


def resolve_pmcid(cfg, p):
    if p.get("pmcid"):
        return p["pmcid"]
    doi, pmid = p.get("doi"), p.get("pmid")
    if not (doi or pmid):
        return None
    try:
        q = f"EXT_ID:{pmid}" if pmid else f"DOI:{doi}"
        r = get(cfg, "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": q, "format": "json", "resultType": "lite"}, timeout=25,
                headers=make_headers(cfg, json_api=True))
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


def manual_candidates(p):
    """papers_meta.json 里的 manual_urls / download_overrides，迁走脚本内硬编码。"""
    out = []
    for key in ("manual_urls", "download_overrides"):
        for item in p.get(key) or []:
            if isinstance(item, str):
                out.append((item, None))
            elif isinstance(item, dict) and item.get("url"):
                out.append((item["url"], item.get("referer")))
    return out


def download(cfg, url, dest, referer=None, verify=True):
    """流式下载到临时文件，校验 PDF 魔数后原子改名。"""
    max_size = int(cfg_get(cfg, "download", "max_mb", default=60)) * 1_000_000
    headers = make_headers(cfg, referer=referer)
    tmp = dest + ".part"
    try:
        with get(cfg, url, stream=True, headers=headers, verify=verify) as r:
            if r.status_code >= 400:
                return None, f"HTTP {r.status_code}"
            content_type = r.headers.get("Content-Type", "") or ""
            if "html" in content_type.lower() and "pdf" not in content_type.lower():
                return None, f"html page (ctype={content_type[:60]})"
            size = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > max_size:
                        f.close()
                        os.remove(tmp)
                        return None, f"too large (> {max_size} bytes)"
                    f.write(chunk)
            if size < 10_000:
                os.remove(tmp)
                return None, f"too small ({size} bytes)"
            with open(tmp, "rb") as f:
                head = f.read(5)
            if head != b"%PDF-":
                os.remove(tmp)
                return None, f"not pdf (ctype={content_type[:60]})"
            os.replace(tmp, dest)
            return dest, "ok"
    except Exception as e:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return None, f"err {type(e).__name__}: {e}"


def try_scihub(cfg, doi, dest):
    if not doi:
        return None, "no doi"
    for mirror in SCI_HUB_MIRRORS:
        url = mirror + urllib.parse.quote(doi, safe="")
        try:
            r = requests.get(url, timeout=25, verify=False, headers=make_headers(cfg))
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
            got, msg = download(cfg, pdf_url, dest, referer=url, verify=False)
            if got:
                return got, f"scihub::{mirror}"
            print(f"    [scihub {mirror}] {msg}")
        except Exception as e:
            print(f"    [scihub {mirror}] {e}")
    return None, "scihub failed"


def candidates_for(cfg, p):
    doi, pmcid = p.get("doi"), p.get("pmcid")
    cands = manual_candidates(p)
    if pmcid:
        cands.append((f"https://europepmc.org/articles/{pmcid}?pdf=render", None))
        cands.append((f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/", None))
    for u in publisher_urls(doi):
        cands.append((u, None))
    vp = p.get("verified", {}) or {}
    for key in ("openalex", "openalex_title_lookup"):
        oa = vp.get(key) or {}
        if oa.get("oa_pdf"):
            cands.append((oa["oa_pdf"], None))
    epmcv = vp.get("europepmc") or {}
    for u in epmcv.get("fulltexts", []):
        if u.lower().endswith(".pdf") or "pdf" in u.lower() or "render" in u.lower():
            cands.append((u, None))
    # dedupe
    seen, uniq = set(), []
    for u, ref in cands:
        if u and u not in seen:
            seen.add(u)
            uniq.append((u, ref))
    return uniq


def process_one(cfg, p, allow_third_party=False):
    pid = p["id"]
    print(f"[{pid}] start {str(p.get('title', ''))[:55]}", flush=True)
    entry = {"id": pid, "doi": p.get("doi"), "pmid": p.get("pmid"),
             "pmcid": p.get("pmcid"), "status": "failed", "attempts": [], "file": None}
    if not entry["pmcid"]:
        entry["pmcid"] = resolve_pmcid(cfg, p)
    cands = candidates_for(cfg, p)
    papers_dir = output_dir(cfg, "papers")
    dest = str(papers_dir / f"{pid}_{slugify(str(p.get('title', '')))}.pdf")
    for url, ref in cands:
        got, msg = download(cfg, url, dest, referer=ref)
        entry["attempts"].append({"url": url, "msg": msg, "file": got if got else None})
        if got:
            entry["status"] = "ok"
            entry["file"] = dest
            entry["size"] = os.path.getsize(dest)
            print(f"    OK via {url[:90]} ({entry['size']} bytes)", flush=True)
            return entry
        print(f"    fail {msg} <- {url[:80]}", flush=True)
        time.sleep(0.2)
    if allow_third_party:
        got, msg = try_scihub(cfg, p.get("doi"), dest)
        entry["attempts"].append({"url": "scihub-fallback", "msg": msg,
                                  "file": got if got else None})
        if got:
            entry["status"] = "ok"
            entry["file"] = dest
            entry["size"] = os.path.getsize(dest)
            print(f"    OK via third-party ({entry['size']} bytes)", flush=True)
        else:
            print(f"    FAILED: {msg}", flush=True)
    else:
        entry["attempts"].append({"url": "scihub-fallback",
                                  "msg": "blocked_by_policy", "file": None})
        print("    FAILED: no compliant source (third-party blocked by policy)", flush=True)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-third-party", action="store_true",
                        help="显式授权尝试 Sci-Hub 等第三方渠道（默认关闭）")
    cfg, args = parse_project_arg(parser)
    allow = bool(args.allow_third_party or cfg_get(cfg, "compliance", "allow_third_party", default=False))
    meta = load_papers_meta(cfg, verified=True, required=False)
    if meta is None:
        meta = load_papers_meta(cfg, verified=False)
    errors, _ = validate_meta(meta)
    if errors:
        raise SystemExit("papers_meta 校验失败：\n  - " + "\n  - ".join(errors))

    output_dir(cfg, "papers")
    papers = meta["papers"]
    results = {}
    workers = int(cfg_get(cfg, "download", "workers", default=6))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(process_one, cfg, p, allow): p for p in papers}
        for fut in as_completed(futs):
            entry = fut.result()
            results[entry["id"]] = entry
            write_json(project_path(cfg, "papers", "results.json"), results)
    ok = sum(1 for v in results.values() if v.get("status") == "ok")
    print(f"\nDONE: {ok}/{len(papers)} PDFs downloaded")


if __name__ == "__main__":
    main()
