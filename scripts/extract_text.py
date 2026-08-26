#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_text.py — 对 papers/*.pdf 逐页提取文本与基础元数据：
  papers_txt/{id}.txt     逐页文本（带 ===PAGE n=== 标记，便于检索定位）
  papers_meta_extra.json  每篇的页数/首页标题/DOI/作者/摘要前500字符
"""
import json
import os
import re
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not installed: pip install pymupdf")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
PAPER_DIR = os.path.join(BASE, "papers")
TXT_DIR = os.path.join(BASE, "papers_txt")
os.makedirs(TXT_DIR, exist_ok=True)


def clean(text):
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    meta = json.load(open(os.path.join(BASE, "papers_meta.json"), encoding="utf-8"))
    extra = {}
    for p in meta["papers"]:
        pid = p["id"]
        # find pdf by id
        pdf = None
        for fn in sorted(os.listdir(PAPER_DIR)):
            if fn.startswith(pid + "_") and fn.lower().endswith(".pdf"):
                pdf = os.path.join(PAPER_DIR, fn)
                break
        if not pdf:
            print(f"[{pid}] no pdf, skip")
            continue
        doc = fitz.open(pdf)
        pages = []
        for i, page in enumerate(doc):
            pages.append(f"===PAGE {i+1}===\n" + clean(page.get_text()))
        txt = "\n\n".join(pages)
        first = clean(doc[0].get_text())
        # 简单解析首页头部
        m_title = first.splitlines()[:20]
        doi_m = re.search(r"10\.\d{4,9}/[^\s,;)\]]+", first)
        pmid_m = re.search(r"PMID:\s*(\d+)", first)
        extra[pid] = {
            "file": pdf,
            "pages": doc.page_count,
            "size": os.path.getsize(pdf),
            "doi_reg": doi_m.group(0) if doi_m else None,
            "pmid_reg": pmid_m.group(1) if pmid_m else None,
            "first_page_head": "\n".join(m_title[:14]),
            "abstract_snippet": first[:900],
        }
        with open(os.path.join(TXT_DIR, f"{pid}.txt"), "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"[{pid}] {doc.page_count} pages -> papers_txt/{pid}.txt")
        doc.close()
    with open(os.path.join(BASE, "papers_meta_extra.json"), "w", encoding="utf-8") as f:
        json.dump(extra, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
