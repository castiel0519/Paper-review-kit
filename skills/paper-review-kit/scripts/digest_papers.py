#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
digest_papers.py — 生成结构化精读缓冲（v2）。

从 papers_txt/{id}.txt 中：
  - 首页摘要前 1200 字符
  - 每个关键 section 首次命中后 700 字符
  - 输出 digests/{id}.md，默认整篇 ≤ 2600 字符
供子 Agent 精读使用；主 Agent 请用 make_brief.py 生成的 brief。
"""
import re

from prk_config import output_dir, parse_project_arg

PAGE_RE = re.compile(r"===PAGE (\d+)===(.*?)(?===PAGE \d+===|\Z)", re.S)
SECTION_KEYS = [
    ("abstract", ["abstract"]),
    ("introduction", ["introduction"]),
    ("methods", ["methods", "material and methods", "method"]),
    ("results", ["results", "result"]),
    ("discussion", ["discussion"]),
    ("conclusion", ["conclusion"]),
    ("figures", ["fig. 1", "figure 1", "fig 1"]),
    ("tables", ["table 1"]),
]
MAX_TOTAL = 2600
MAX_SECTION = 700


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def main():
    cfg, args = parse_project_arg()
    txt_dir = output_dir(cfg, "papers_txt")
    dig_dir = output_dir(cfg, "digests")
    if not txt_dir.is_dir():
        print("papers_txt/ 不存在，跳过")
        return
    for fn in sorted(txt_dir.glob("*.txt")):
        pid = fn.stem
        raw = fn.read_text(encoding="utf-8")
        pages = []
        for m in PAGE_RE.finditer(raw):
            pno = int(m.group(1))
            body = clean(m.group(2))
            pages.append((pno, body))
        if not pages:
            continue
        head = (pages[0][1] or raw)[:1200]
        parts = [f"### {pid} digest\n", f"\n## Page 1 (head)\n{head}\n"]
        seen = set()
        for section, keys in SECTION_KEYS:
            if section in seen:
                continue
            for pno, body in pages[1:]:
                low = body.lower()
                hit = None
                for key in keys:
                    idx = low.find(key)
                    if idx >= 0:
                        hit = (key, idx)
                        break
                if hit is not None:
                    seg = body[hit[1]:hit[1] + MAX_SECTION]
                    parts.append(f"\n## page {pno} [{section}]\n{seg}\n")
                    seen.add(section)
                    break
        digest = "".join(parts)
        if len(digest) > MAX_TOTAL:
            # 保留开头和后面的 section，删除中间溢出
            head_part = digest[:MAX_TOTAL]
            digest = head_part + "\n## (truncated)\n"
        (dig_dir / f"{pid}.md").write_text(digest, encoding="utf-8")
        print(f"[{pid}] digest {len(digest)} chars")


if __name__ == "__main__":
    main()
