#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
digest_papers.py — 为每篇论文生成“精读摘要缓冲”：
从 papers_txt/*.txt 中抽取 首页(摘要) + 方法/结果/讨论关键段落 + 图表标题，
写入 digests/{id}.txt（每篇约 4-6KB），供主上下文定向精读，
避免把 21 篇全文一次性载入上下文。
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
TXT_DIR = os.path.join(BASE, "papers_txt")
DIG_DIR = os.path.join(BASE, "digests")
os.makedirs(DIG_DIR, exist_ok=True)

HEAD_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)?\s*([A-Z][^\n]{0,60}(?:[A-Za-z\s\-–+/&(),.]{0,40}))\s*$")
SECTION_KEYS = ["abstract", "introduction", "material", "method", "experiment",
                "result", "discussion", "conclusion", "fig", "table"]


def split_pages(text):
    return re.split(r"===PAGE \d+===", text)


def clean(t):
    return re.sub(r"\s+", " ", t).strip()


def head_tail(text, head=900, tail=0):
    t = clean(text)
    return t[:head] + (" ... " + t[-tail:] if tail else "")


def main():
    files = sorted(f for f in os.listdir(TXT_DIR) if f.endswith(".txt"))
    for fn in files:
        pid = fn[:-4]
        with open(os.path.join(TXT_DIR, fn), encoding="utf-8") as f:
            raw = f.read()
        pages = split_pages(raw)
        page1 = clean(pages[1]) if len(pages) > 1 else clean(raw)
        # 摘取首页前 1800 字符（含标题/作者/摘要）
        first = page1[:1800]
        # 关键词段落：找 methods / results / discussion
        hits = []
        for i, pg in enumerate(pages[1:], start=2):
            body = clean(pg)
            low = body.lower()
            for key in ["abstract", "introduction", "methods", "results",
                        "discussion", "conclusion", "fig. 1", "table 1"]:
                if key in low:
                    idx = low.find(key)
                    hits.append((i, key, body[idx:idx + 1400]))
        # 去重：每个 key 只保留最先出现的两段
        seen = set()
        digest_parts = [f"### {pid} digest\n\n## Page 1 (head)\n{first}\n"]
        for pg_no, key, seg in hits:
            k = key
            if k in seen:
                continue
            seen.add(k)
            digest_parts.append(f"\n## p{pg_no} [{key}]\n{seg}\n")
        digest = "".join(digest_parts)
        with open(os.path.join(DIG_DIR, f"{pid}.md"), "w", encoding="utf-8") as f:
            f.write(digest)
        print(f"[{pid}] digest {len(digest)} chars")


if __name__ == "__main__":
    main()
