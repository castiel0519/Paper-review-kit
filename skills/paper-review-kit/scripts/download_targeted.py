#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_targeted.py — 定向补下载：01（Nat Commun 大文件，用 EPMC render 单连接稳定下载）
与 10（Matter，Radboud 仓库带 Referer）。顺带尝试 02/11 的候选链接。
"""
import json
import os

import download_papers_fast as dp

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(BASE, "papers", "results.json")
OUT_DIR = os.path.join(BASE, "papers")
META = json.load(open(os.path.join(BASE, "papers_meta_verified.json"), encoding="utf-8"))
PAPERS = {p["id"]: p for p in META["papers"]}

TARGETS = {
    "01": [("https://europepmc.org/articles/PMC10761910?pdf=render", None),
           ("https://www.nature.com/articles/s41467-023-44068-3.pdf", None)],
    "10": [("https://repository.ubn.ru.nl//bitstream/handle/2066/227680/227680.pdf",
            "https://repository.ubn.ru.nl/")],
    "02": [("https://europepmc.org/articles/PMC12587405?pdf=render", None),
           ("https://pubs.rsc.org/en/content/articlepdf/2025/lc/d5lc00216h", None)],
    "11": [("https://www.sciencedirect.com/science/article/pii/S2211383526000010/pdfft", None),
           ("https://www.yxxb.com.cn/apsb/en/article/doi/10.1016/j.apsb.2026.01.001/pdf", None)],
}


def main():
    results = {}
    if os.path.exists(RESULTS):
        results = json.load(open(RESULTS, encoding="utf-8"))
    for pid, cands in TARGETS.items():
        p = PAPERS.get(pid)
        if not p:
            continue
        old = results.get(pid, {})
        if old.get("status") == "ok" and os.path.exists(old.get("file") or ""):
            print(f"[{pid}] already ok", flush=True)
            continue
        entry = {"id": pid, "doi": p.get("doi"), "pmid": p.get("pmid"),
                 "pmcid": p.get("pmcid"), "status": "failed", "attempts": [], "file": None}
        dest = os.path.join(OUT_DIR, f"{pid}_{dp.slugify(p['title'])}.pdf")
        for u, ref in cands:
            got, msg = dp.download(u, dest, referer=ref)
            entry["attempts"].append({"url": u, "msg": msg, "file": got if got else None})
            if got:
                entry["status"] = "ok"
                entry["file"] = dest
                entry["size"] = os.path.getsize(dest)
                print(f"[{pid}] OK via {u[:80]} ({entry['size']} bytes)", flush=True)
                break
            else:
                print(f"[{pid}] fail {msg} <- {u[:80]}", flush=True)
        results[pid] = entry
        json.dump(results, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("targeted done")


if __name__ == "__main__":
    main()
