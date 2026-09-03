#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ab_compare.py — 两套 summaries 的 A/B 对比脚本。

用法：
    python scripts/ab_compare.py --old projects/old/summaries --new projects/new/summaries

对比字段：method_zh / results_zh / metrics_zh / evidence_pages / figure_refs /
pdf_status / scheme_image。输出 ab_report.json 并打印差异摘要。
"""
import argparse
import json
from pathlib import Path

from prk_config import read_json, write_json

FIELDS = ["pdf_status", "method_zh", "results_zh", "metrics_zh",
          "innovation_zh", "limitation_zh", "evidence_pages", "figure_refs",
          "scheme_image"]


def load_summaries(d):
    out = {}
    p = Path(d)
    if not p.is_dir():
        return out
    for fn in sorted(p.glob("*.json")):
        data = read_json(fn, default={})
        if isinstance(data, dict) and data.get("id"):
            out[str(data["id"])] = data
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, help="旧版 summaries 目录")
    parser.add_argument("--new", required=True, help="新版 summaries 目录")
    parser.add_argument("--out", default="ab_report.json", help="输出 JSON")
    args = parser.parse_args()

    old = load_summaries(args.old)
    new = load_summaries(args.new)
    ids = sorted(set(old) | set(new))
    rows = []
    for pid in ids:
        a, b = old.get(pid), new.get(pid)
        row = {"id": pid, "only_old": a is not None and b is None,
               "only_new": b is not None and a is None,
               "diffs": []}
        if a and b:
            for f in FIELDS:
                va, vb = a.get(f), b.get(f)
                if va != vb:
                    row["diffs"].append({"field": f,
                                         "old_len": len(str(va)) if va is not None else 0,
                                         "new_len": len(str(vb)) if vb is not None else 0})
        rows.append(row)
    report = {"papers": len(ids), "rows": rows,
              "changed": sum(1 for r in rows if r["diffs"]),
              "only_old": sum(1 for r in rows if r["only_old"]),
              "only_new": sum(1 for r in rows if r["only_new"])}
    out_path = Path(args.out)
    write_json(out_path, report)
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, ensure_ascii=False, indent=2))
    for r in rows:
        if r["diffs"] or r["only_old"] or r["only_new"]:
            print(r["id"], "diffs=", len(r["diffs"]), "old_only=", r["only_old"], "new_only=", r["only_new"])


if __name__ == "__main__":
    main()
