#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_brief.py — 从 summaries/*.json 生成主 Agent 使用的路由层 brief。

每篇只保留：
  - id / pdf_status / 中文题名 / 方向
  - 方法一句话、结果一句话、代表性指标、创新/局限一句话
输出：digests/brief.txt，每篇 ≤ 320 字符，替代旧版超大 keyfacts.txt。
"""
import re

from prk_config import load_papers_meta, output_dir, parse_project_arg, read_json

MAX_PER_PAPER = 320


def clip(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "…"


def one_sentence(s, keys):
    for k in keys:
        v = clip(s.get(k), 70)
        if v:
            return v
    return "—"


def main():
    cfg, args = parse_project_arg()
    meta = load_papers_meta(cfg)
    sum_dir = output_dir(cfg, "summaries")
    dig_dir = output_dir(cfg, "digests")
    papers = {str(p.get("id")): p for p in meta["papers"]}
    lines = []
    if sum_dir.is_dir():
        for fn in sorted(sum_dir.glob("*.json")):
            s = read_json(fn, default={})
            if not isinstance(s, dict):
                continue
            pid = str(s.get("id", ""))
            status = s.get("pdf_status") or papers.get(pid, {}).get("pdf_status") or "missing"
            title_zh = clip(s.get("title_zh") or papers.get(pid, {}).get("title_zh") or s.get("title_en"), 40)
            kind = clip(s.get("kind_zh") or papers.get(pid, {}).get("kind_zh"), 16)
            method = one_sentence(s, ["method_zh"])
            result = one_sentence(s, ["results_zh"])
            # 指标只取第一条
            metrics = s.get("metrics_zh") or []
            metric = "—"
            if metrics:
                m0 = metrics[0]
                metric = clip((m0.get("label", "") if isinstance(m0, dict) else str(m0))
                              + ": "
                              + (m0.get("value", "") if isinstance(m0, dict) else ""), 40)
            innovation = one_sentence(s, ["innovation_zh", "limitation_zh"])
            block = f"[{pid}|{status}] {title_zh} · {kind}\n方法: {method}\n结果: {result}\n指标: {metric}\n价值: {innovation}\n"
            if len(block) > MAX_PER_PAPER:
                block = block[:MAX_PER_PAPER].rstrip() + "\n…\n"
            lines.append(block)
    out = dig_dir / "brief.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", out, "papers", len(lines))


if __name__ == "__main__":
    main()
