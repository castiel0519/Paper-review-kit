# -*- coding: utf-8 -*-
"""
condense_digests.py — 兼容脚本：从 digests/*.md 生成压缩版 keyfacts.txt。

v2 策略：每篇最多 1200 字符，只保留首页摘要和 method/results/discussion 片段，
不再收集数字行避免把页码/编号当事实。主 Agent 的精读路由请用 make_brief.py。
"""
import re

from prk_config import output_dir, parse_project_arg

MAX_PER_PAPER = 1200
KEYS = ["methods", "results", "discussion", "conclusion"]


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def main():
    cfg, args = parse_project_arg()
    dig_dir = output_dir(cfg, "digests")
    if not dig_dir.is_dir():
        print("digests/ 不存在，跳过")
        return
    chunks = []
    for fn in sorted(dig_dir.glob("*.md")):
        raw = fn.read_text(encoding="utf-8")
        pid = fn.stem
        head = ""
        m = re.search(r"## Page 1 \(head\)\n(.*?)(?=\n## |\Z)", raw, re.S)
        if m:
            head = clean(m.group(1))[:600]
        parts = [f"### {pid}\n摘要: {head}\n"]
        for key in KEYS:
            m = re.search(rf"## page \d+ \[{key}\]\n(.*?)(?=\n## |\Z)", raw, re.S)
            if m:
                seg = clean(m.group(1))[:400]
                parts.append(f"{key}: {seg}\n")
        text = "".join(parts)
        if len(text) > MAX_PER_PAPER:
            text = text[:MAX_PER_PAPER] + "\n...\n"
        chunks.append(text)
    out = dig_dir / "keyfacts.txt"
    out.write_text("\n".join(chunks), encoding="utf-8")
    print("wrote", out, "chars", sum(len(c) for c in chunks))


if __name__ == "__main__":
    main()
