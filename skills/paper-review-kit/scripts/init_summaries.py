#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_summaries.py — 从 papers_meta.json 初始化每篇论文的结构化摘要模板
（summaries/summary_{id}.json），再人工/半自动填充精读内容。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SUM_DIR = os.path.join(BASE, "summaries")
os.makedirs(SUM_DIR, exist_ok=True)

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
    "lessons_zh": ""
}


def main():
    meta = json.load(open(os.path.join(BASE, "papers_meta.json"), encoding="utf-8"))
    for p in meta["papers"]:
        path = os.path.join(SUM_DIR, f"summary_{p['id']}.json")
        d = dict(TEMPLATE)
        d["id"] = p["id"]
        d["title_en"] = p["title"]
        d["title_zh"] = p["title_zh"]
        d["journal"] = p["journal"]
        d["year"] = p["year"]
        d["doi"] = p["doi"]
        d["pmid"] = p.get("pmid")
        d["pmcid"] = p.get("pmcid")
        d["kind"] = p["kind"]
        d["kind_zh"] = p["kind_zh"]
        d["scheme_image"] = f"papers_figs/{p['id']}_fig1.png"
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
            print("init", path)


if __name__ == "__main__":
    main()
