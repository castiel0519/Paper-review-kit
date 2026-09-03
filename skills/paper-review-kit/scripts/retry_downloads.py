#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retry_downloads.py — 只重试 results.json 中的失败论文。
人工核验的补充 URL 现在放在 papers_meta.json 的 manual_urls /
download_overrides 字段里，不再硬编码在脚本中。
第三方回退同样遵守 compliance.allow_third_party / --allow-third-party。
"""
import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import download_papers_fast as dp

from prk_config import (
    cfg_get, load_papers_meta, output_dir, parse_project_arg, project_path, read_json, write_json,
)
from prk_schema import validate_meta


def process(cfg, p, allow_third_party):
    pid = p["id"]
    print(f"[{pid}] retry start", flush=True)
    entry = {"id": pid, "doi": p.get("doi"), "pmid": p.get("pmid"),
             "pmcid": p.get("pmcid"), "status": "failed", "attempts": [], "file": None}
    cands = dp.candidates_for(cfg, p)
    papers_dir = output_dir(cfg, "papers")
    dest = str(papers_dir / f"{pid}_{dp.slugify(str(p.get('title', '')))}.pdf")
    for url, ref in cands:
        got, msg = dp.download(cfg, url, dest, referer=ref)
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
        got, msg = dp.try_scihub(cfg, p.get("doi"), dest)
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
                        help="显式授权尝试第三方渠道")
    cfg, args = parse_project_arg(parser)
    allow = bool(args.allow_third_party or cfg_get(cfg, "compliance", "allow_third_party", default=False))
    meta = load_papers_meta(cfg, verified=True, required=False)
    if meta is None:
        meta = load_papers_meta(cfg, verified=False)
    errors, _ = validate_meta(meta)
    if errors:
        raise SystemExit("papers_meta 校验失败：\n  - " + "\n  - ".join(errors))

    results_path = project_path(cfg, "papers", "results.json")
    results = read_json(results_path, default={})
    papers = {str(p["id"]): p for p in meta["papers"]}
    if results:
        failed = [k for k, v in results.items() if v.get("status") != "ok"]
    else:
        failed = list(papers.keys())
    if not failed:
        print("no failed papers")
        return
    print("retry failed:", failed, flush=True)
    workers = int(cfg_get(cfg, "download", "workers", default=4))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(process, cfg, papers[k], allow): k for k in failed if k in papers}
        for fut in as_completed(futs):
            entry = fut.result()
            results[entry["id"]] = entry
            write_json(results_path, results)
    ok = sum(1 for v in results.values() if v.get("status") == "ok")
    print(f"DONE: {ok}/{len(results)}")


if __name__ == "__main__":
    main()
