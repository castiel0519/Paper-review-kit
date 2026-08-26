#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retheme.py — 把 paper-review-kit 的默认“微流控”主题重命名成新主题。
用法（在项目根目录）：
    python scripts/retheme.py --topic 癌症早筛 --topic-en Cancer Screening
    python scripts/retheme.py --project D:/some/project --topic 材料发现
只重写 scripts/make_docx.py / make_pptx.py / verify_deliverables.py 的主题词，
请人工检查替换结果（尤其“微流控”被替换成新词后的通顺性）。
"""
import argparse
import os
import sys

TOPIC_OLD = "微流控"
TITLE_OLD = "机器学习与人工智能在微流控中的应用"
SUB_OLD = "在微流控中的应用"
EN_OLD = "Microfluidics"


def patch(path, pairs):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    n = 0
    for old, new in pairs:
        c = content.count(old)
        if c:
            content = content.replace(old, new)
            n += c
            print(f"  {os.path.basename(path)}: {old!r} -> {new!r}  x{c}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".", help="项目根目录（含 scripts/）")
    ap.add_argument("--topic", required=True, help="新主题中文名，如：癌症早筛")
    ap.add_argument("--topic-en", default="Automated Topic", help="新主题英文名")
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    if not os.path.isdir(os.path.join(root, "scripts")):
        print(f"ERROR: no scripts/ under {root}")
        sys.exit(1)
    topic = args.topic
    title_new = f"机器学习与人工智能在{topic}中的应用"
    sub_new = f"在{topic}中的应用"
    pairs = [
        (TITLE_OLD, title_new),
        (SUB_OLD, sub_new),
        (EN_OLD, args.topic_en),
        (TOPIC_OLD, topic),
    ]
    for fname in ["make_docx.py", "make_pptx.py", "verify_deliverables.py"]:
        p = os.path.join(root, "scripts", fname)
        if os.path.exists(p):
            patch(p, pairs)
    print("done. 请人工检查 make_docx.py/make_pptx.py 中替换后的措辞。")


if __name__ == "__main__":
    main()
