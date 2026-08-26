# -*- coding: utf-8 -*-
"""
condense_digests.py — 从 digests/*.md 生成“关键事实”压缩文本 keyfacts.txt：
每篇包含：首页摘要(前1200字)、Results/Conclusion/Methods 段落(各前1000字)、
包含数字/百分比的句子(前20条)。供主上下文定向精读，避免全文占用。
"""
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIG_DIR = os.path.join(BASE, "digests")
OUT = os.path.join(DIG_DIR, "keyfacts.txt")


def clean(t):
    return re.sub(r"\s+", " ", t).strip()


def main():
    result = []
    for fn in sorted(os.listdir(DIG_DIR)):
        if not fn.endswith(".md"):
            continue
        pid = fn[:-3]
        with open(os.path.join(DIG_DIR, fn), encoding="utf-8") as f:
            raw = f.read()
        # 抽象：开头
        head = clean(raw.split("## Page 1")[1].split("##")[0]) if "## Page 1" in raw else clean(raw[:1500])
        result.append(f"\n{'='*90}\n### {pid}\nABSTRACT: {head[:1500]}")
        # 分段关键词
        for key in ["Results and Discussion", "Results", "Conclusion", "Methods", "Experimental"]:
            idx = raw.find(key)
            if idx >= 0 and key not in ("Results",):
                seg = clean(raw[idx:idx + 1800])
                result.append(f"\n-- {key} --\n{seg}")
        # 数字行
        nums = []
        for line in raw.split("\n"):
            if re.search(r"\d+(\.\d+)?\s*%|\d{2,}", line) and len(line) < 400:
                nums.append(clean(line))
            if len(nums) >= 20:
                break
        if nums:
            result.append("\n-- NUMBERS --\n" + "\n".join(nums[:20]))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(result))
    print("wrote", OUT, "chars", len("\n".join(result)))


if __name__ == "__main__":
    main()
