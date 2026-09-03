#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
save_summary.py — 子 Agent 落盘 summary 的轻量 helper。

用法：
    python scripts/save_summary.py --id 01 <<'JSON'
    { ... }
    JSON

脚本会：
  1. 读 stdin JSON
  2. 校验必填字段与 pdf_status/evidence
  3. 写到 summaries/summary_<id>.json
  4. 只打印一行结果，避免 write/edit 工具回显全文。
"""
import argparse
import json
import sys

from prk_config import output_dir, parse_project_arg, write_json
from prk_schema import validate_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="论文 id，如 01")
    parser.add_argument("--allow-errors", action="store_true",
                        help="校验有错也落盘（默认拒绝并打印错误）")
    cfg, args = parse_project_arg(parser)
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"ERROR invalid json: {e}")
        sys.exit(1)
    if not isinstance(data, dict):
        print("ERROR summary must be object")
        sys.exit(1)
    data["id"] = str(args.id)
    errors, warnings = validate_summary(data)
    if errors and not args.allow_errors:
        print("ERROR " + "; ".join(errors))
        sys.exit(1)
    out_dir = output_dir(cfg, "summaries")
    path = out_dir / f"summary_{args.id}.json"
    write_json(path, data)
    msg = f"saved {path.name} ({len(raw)} chars)"
    if warnings:
        msg += " warnings=" + "; ".join(warnings[:3])
    if errors:
        msg += " errors=" + "; ".join(errors[:3])
    print(msg)


if __name__ == "__main__":
    main()
