#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retry_downloads.py — 只重试 results.json 中的失败论文：
- 追加人工核验的公开 PDF 地址（d-nb 仓库、Radboud 仓库等，带 Referer 下载）
- Sci-Hub 回退已开启 verify=False（第三方镜像自签名证书）
- ThreadPoolExecutor(4) 并发
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import download_papers_fast as dp

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
RESULTS = os.path.join(BASE, "papers", "results.json")
META = os.path.join(BASE, "papers_meta_verified.json")
OUT_DIR = os.path.join(BASE, "papers")

MANUAL_URLS = {
    "09": [("https://d-nb.info/1270867725/34", None)],
    "10": [("https://repository.ubn.ru.nl//bitstream/handle/2066/227680/227680.pdf",
            "https://repository.ubn.ru.nl/")],
    "19": [("https://europepmc.org/articles/PMC10222806?pdf=render", None)],
    "03": [("https://europepmc.org/articles/PMC11906218?pdf=render", None)],
    "06": [("https://europepmc.org/articles/PMC10141994?pdf=render", None)],
}


def process(p, manual):
    pid = p["id"]
    print(f"[{pid}] retry start", flush=True)
    entry = {"id": pid, "doi": p.get("doi"), "pmid": p.get("pmid"),
             "pmcid": p.get("pmcid"), "status": "failed", "attempts": [], "file": None}
    cands = [(u, ref) for u, ref in manual]
    for u in dp.candidates_for(p):
        cands.append((u, None))
    dest = os.path.join(OUT_DIR, f"{pid}_{dp.slugify(p['title'])}.pdf")
    for url, ref in cands:
        got, msg = dp.download(url, dest, referer=ref)
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
    got, msg = dp.try_scihub(p.get("doi"), dest)
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
    results = json.load(open(RESULTS, encoding="utf-8"))
    meta = json.load(open(META, encoding="utf-8"))
    papers = {p["id"]: p for p in meta["papers"]}
    failed = [k for k, v in results.items() if v.get("status") != "ok"]
    print("retry failed:", failed, flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(process, papers[k], MANUAL_URLS.get(k, [])): k for k in failed}
        for fut in as_completed(futs):
            entry = fut.result()
            results[entry["id"]] = entry
            json.dump(results, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ok = sum(1 for v in results.values() if v.get("status") == "ok")
    print(f"DONE: {ok}/{len(results)}")


if __name__ == "__main__":
    main()
