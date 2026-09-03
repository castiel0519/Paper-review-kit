#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_review_material.py — 生成供“综述子 Agent”使用的紧凑综述素材包。

输入：summaries/summary_*.json
输出：digests/review_material.md

每篇保持 500 字符左右的字段抽取，带 [编号] 引用锚点。
综述子 Agent 只读这个文件，不读全文。
"""
import re

from prk_config import output_dir, parse_project_arg, read_json

MAX_FIELD = {
    "background_zh": 90,
    "problem_zh": 80,
    "data_zh": 70,
    "task_zh": 60,
    "method_zh": 180,
    "results_zh": 180,
    "innovation_zh": 90,
    "limitation_zh": 90,
    "framework_zh": 120,
    "lessons_zh": 90,
    "paradigm_zh": 100,
}


def clip(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[:n].rstrip() + "…"


def main():
    cfg, args = parse_project_arg()
    sum_dir = output_dir(cfg, "summaries")
    dig_dir = output_dir(cfg, "digests")
    if not sum_dir.is_dir():
        print("summaries/ 不存在，请先完成精读")
        return
    blocks = []
    for fn in sorted(sum_dir.glob("*.json")):
        s = read_json(fn, default={})
        if not isinstance(s, dict):
            continue
        if not (s.get("method_zh") and s.get("results_zh")):
            continue
        pid = str(s.get("id", ""))
        title = clip(s.get("title_zh") or s.get("title_en"), 60)
        lines = [
            f"\n## [{pid}] {title}",
            f"- 方向：{clip(s.get('kind_zh') or s.get('kind'), 40)}｜状态：{s.get('pdf_status','')}",
        ]
        mapping = [
            ("背景", "background_zh"),
            ("问题", "problem_zh"),
            ("数据/任务", None),
            ("方法", "method_zh"),
            ("结果", "results_zh"),
            ("指标", None),
            ("创新", "innovation_zh"),
            ("局限", "limitation_zh"),
            ("范式", "paradigm_zh"),
            ("框架", "framework_zh"),
            ("启示", "lessons_zh"),
        ]
        for label, field in mapping:
            if field == "数据/任务":
                vals = [clip(s.get("data_zh"), 60), clip(s.get("task_zh"), 60)]
                vals = [v for v in vals if v and v != "…"]
                if vals:
                    lines.append(f"- {label}：{'；'.join(vals)}")
                continue
            if field == "指标":
                ms = s.get("metrics_zh") or []
                if ms:
                    m0 = ms[0]
                    label = m0.get("label", "") if isinstance(m0, dict) else str(m0)
                    value = m0.get("value", "") if isinstance(m0, dict) else ""
                    lines.append(f"- 指标：{label}：{clip(value, 50)}")
                continue
            if field:
                lines.append(f"- {label}：{clip(s.get(field), MAX_FIELD.get(field, 80))}")
        # 每篇再加一行原始引用
        refs = s.get("figure_refs") or []
        pages = s.get("evidence_pages") or []
        if refs or pages:
            lines.append(f"- 图/证据：{', '.join(map(str, refs[:3])) if refs else '—'}；页码：{', '.join(map(str, pages[:5])) if pages else '—'}")
        blocks.append("\n".join(lines))
    out = dig_dir / "review_material.md"
    out.write_text("# 综述素材包\n\n本文由脚本从 summaries 生成，供综述写作引用；"
                   "所有数字/结论必须来自以下素材，禁止编造。\n" + "\n".join(blocks), encoding="utf-8")
    print("wrote", out, "chars", out.stat().st_size, "papers", len(blocks))


if __name__ == "__main__":
    main()
