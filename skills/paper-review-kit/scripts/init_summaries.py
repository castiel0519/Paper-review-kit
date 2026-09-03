#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_summaries.py — 从 papers_meta.json 初始化每篇论文的精读摘要模板。
只创建缺失的 summary 文件，已存在的内容绝不覆盖。
"""
import argparse
import os

from prk_config import load_config, load_papers_meta, output_dir, parse_project_arg, write_json
from prk_schema import validate_meta

TEMPLATE = {
    "abstract_en": "",
    "abstract_zh": "",
    "background_zh": "",
    "problem_zh": "",
    "data_zh": "",
    "task_zh": "",
    "method_zh": "",
    "results_zh": "",
    "metrics_zh": [],
    "innovation_zh": "",
    "limitation_zh": "",
    "paradigm_zh": "",
    "paradigm_tags": [],
    "framework_zh": "",
    "framework_steps": ["数据与预处理", "模型设计", "训练策略", "评估与解读"],
    "scheme_zh": "",
    "lessons_zh": "",
    "pdf_status": "missing",
    "scheme_image": "",
    "evidence_pages": [],
    "figure_refs": [],
    "reviewed": False,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    cfg, args = parse_project_arg(parser)
    meta = load_papers_meta(cfg)
    errors, _ = validate_meta(meta)
    if errors:
        raise SystemExit("papers_meta.json 校验失败：\n  - " + "\n  - ".join(errors))
    sum_dir = output_dir(cfg, "summaries")
    created = 0
    skipped = 0
    for p in meta["papers"]:
        pid = str(p.get("id", "")).strip()
        if not pid:
            continue
        path = sum_dir / f"summary_{pid}.json"
        if path.exists():
            skipped += 1
            continue
        d = dict(TEMPLATE)
        d.update({
            "id": pid,
            "title_en": p.get("title", ""),
            "title_zh": p.get("title_zh", "") or p.get("title", ""),
            "journal": p.get("journal", ""),
            "year": p.get("year"),
            "doi": p.get("doi") or "",
            "pmid": p.get("pmid"),
            "pmcid": p.get("pmcid"),
            "kind": p.get("kind", ""),
            "kind_zh": p.get("kind_zh", "") or p.get("kind", ""),
            "scheme_image": f"papers_figs/{pid}_fig1.png",
        })
        write_json(path, d)
        created += 1
        print(f"init {path.name}")
    print(f"done: created={created}, kept_existing={skipped}")


if __name__ == "__main__":
    main()
