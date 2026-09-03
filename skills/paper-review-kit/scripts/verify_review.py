#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_review.py — 校验综述 Markdown 的引用来源。

检查：
  1. 综述中所有 [编号] 是否都在 review_material.md 中存在；
  2. 若综述没有任何引用，输出警告；
输出：deliverables/review_check.json 或打印单行结果。
"""
import argparse
import json
import re
from pathlib import Path

from prk_config import load_papers_meta, output_dir, parse_project_arg, project_path, project_title, write_json

CITE_RE = re.compile(r"\[([0-9A-Za-z_-]+)\]")
HEAD_RE = re.compile(r"^## \[([0-9A-Za-z_-]+)\]", re.M)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", default="", help="综述 MD 路径；缺省 deliverables/{title}_调研综述.md")
    cfg, args = parse_project_arg(parser)
    meta = load_papers_meta(cfg)
    title = project_title(cfg, meta)
    dig_dir = output_dir(cfg, "digests")
    del_dir = output_dir(cfg, "deliverables")
    material = dig_dir / "review_material.md"
    review = Path(args.review) if args.review else del_dir / f"{title}_调研综述.md"
    if not material.exists():
        print("FAIL review_material.md 不存在，请先运行 make_review_material.py")
        return
    if not review.exists():
        print("FAIL", review, "不存在")
        return
    material_text = material.read_text(encoding="utf-8")
    review_text = review.read_text(encoding="utf-8")
    valid_ids = set(HEAD_RE.findall(material_text))
    cited = set(CITE_RE.findall(review_text))
    invalid = sorted(cited - valid_ids)
    report = {
        "review": str(review), "material": str(material),
        "cited_papers": sorted(cited), "valid_papers": sorted(valid_ids),
        "invalid_citations": invalid,
        "total_citations": len(cited),
        "ok": not invalid and bool(cited),
    }
    out = project_path(cfg, "review_check.json")
    write_json(out, report)
    if invalid:
        print("FAIL invalid citations:", invalid)
    elif not cited:
        print("WARN no citations in review")
    else:
        print(f"OK review citations {len(cited)}/{len(valid_ids)} valid")
    print("review_check ->", out)


if __name__ == "__main__":
    main()
