#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_text.py — 对 papers/*.pdf 逐页提取文本与基础元数据：
  papers_txt/{id}.txt     逐页文本（带 ===PAGE n=== 标记，便于检索定位）
  papers_meta_extra.json  每篇的页数/首页标题/DOI/作者/摘要前500字符
papers/ 目录缺失或某篇没有 PDF 时只跳过，不中断整条流水线。
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

from prk_config import load_papers_meta, output_dir, parse_project_arg, project_path, write_json


def clean(text):
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def find_pdf(papers_dir, pid):
    if not papers_dir.is_dir():
        return None
    for fn in sorted(papers_dir.iterdir()):
        if fn.name.startswith(str(pid) + "_") and fn.suffix.lower() == ".pdf":
            return fn
    return None


def main():
    cfg, args = parse_project_arg()
    meta = load_papers_meta(cfg)
    papers_dir = output_dir(cfg, "papers")
    txt_dir = output_dir(cfg, "papers_txt")
    extra = {}
    found = 0
    for p in meta["papers"]:
        pid = str(p.get("id", ""))
        pdf = find_pdf(papers_dir, pid)
        if not pdf:
            print(f"[{pid}] no pdf, skip")
            continue
        doc = fitz.open(str(pdf))
        pages = []
        for i, page in enumerate(doc):
            pages.append(f"===PAGE {i+1}===\n" + clean(page.get_text()))
        txt = "\n\n".join(pages)
        first = clean(doc[0].get_text())
        m_title = first.splitlines()[:20]
        doi_m = re.search(r"10\.\d{4,9}/[^\s,;)\]]+", first)
        pmid_m = re.search(r"PMID:\s*(\d+)", first)
        extra[pid] = {
            "file": str(pdf),
            "pages": doc.page_count,
            "size": pdf.stat().st_size,
            "doi_reg": doi_m.group(0) if doi_m else None,
            "pmid_reg": pmid_m.group(1) if pmid_m else None,
            "first_page_head": "\n".join(m_title[:14]),
            "abstract_snippet": first[:900],
        }
        with open(txt_dir / f"{pid}.txt", "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"[{pid}] {doc.page_count} pages -> papers_txt/{pid}.txt")
        doc.close()
        found += 1
    write_json(project_path(cfg, "papers_meta_extra.json"), extra)
    print(f"done: extracted={found}/{len(meta['papers'])}")


if __name__ == "__main__":
    main()
