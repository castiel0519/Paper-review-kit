#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_targeted.py — 定向补下载个别论文。
补充 URL 从 papers_meta.json 的 download_overrides / manual_urls 读取，
不再硬编码论文 ID。可指定 --ids 01,02，默认处理所有带 override 的论文。
"""
import argparse
import os

import download_papers_fast as dp

from prk_config import (
    load_papers_meta, output_dir, parse_project_arg, project_path, read_json, write_json,
)
from prk_schema import validate_meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", default="",
                        help="逗号分隔的论文 ID，如 01,02；缺省为全部带 override 的论文")
    cfg, args = parse_project_arg(parser)
    meta = load_papers_meta(cfg, verified=True, required=False)
    if meta is None:
        meta = load_papers_meta(cfg, verified=False)
    errors, _ = validate_meta(meta)
    if errors:
        raise SystemExit("papers_meta 校验失败：\n  - " + "\n  - ".join(errors))

    papers = {str(p["id"]): p for p in meta["papers"]}
    selected = [i.strip() for i in args.ids.split(",") if i.strip()]
    if not selected:
        selected = [pid for pid, p in papers.items() if p.get("download_overrides") or p.get("manual_urls")]

    results_path = project_path(cfg, "papers", "results.json")
    results = read_json(results_path, default={})
    papers_dir = output_dir(cfg, "papers")
    for pid in selected:
        p = papers.get(pid)
        if not p:
            print(f"[{pid}] not found in papers_meta, skip")
            continue
        old = results.get(pid, {})
        if old.get("status") == "ok" and os.path.exists(old.get("file") or ""):
            print(f"[{pid}] already ok", flush=True)
            continue
        cands = dp.manual_candidates(p)
        entry = {"id": pid, "doi": p.get("doi"), "pmid": p.get("pmid"),
                 "pmcid": p.get("pmcid"), "status": "failed", "attempts": [], "file": None}
        dest = str(papers_dir / f"{pid}_{dp.slugify(str(p.get('title', '')))}.pdf")
        for u, ref in cands:
            got, msg = dp.download(cfg, u, dest, referer=ref)
            entry["attempts"].append({"url": u, "msg": msg, "file": got if got else None})
            if got:
                entry["status"] = "ok"
                entry["file"] = dest
                entry["size"] = os.path.getsize(dest)
                print(f"[{pid}] OK via {u[:80]} ({entry['size']} bytes)", flush=True)
                break
            print(f"[{pid}] fail {msg} <- {u[:80]}", flush=True)
        results[pid] = entry
        write_json(results_path, results)
    print("targeted done")


if __name__ == "__main__":
    main()
