#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_figs.py — 启发式提取每篇论文的 Scheme/框架图：
  优先策略：定位 "Fig. 1"/"Figure 1" 题注，裁剪其上方区域渲染为 PNG。
  回退策略：在含 schematic/overview/workflow/pipeline/architecture 关键词页中，
            选取图片面积最大的页整页渲染。
输出：papers_figs/{id}_fig1.png（或 {id}_page{n}.png），并写 figs_info.json。
"""
import json
import os
import re
import sys

try:
    import fitz
except ImportError:
    print("PyMuPDF not installed: pip install pymupdf")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
PAPER_DIR = os.path.join(BASE, "papers")
FIG_DIR = os.path.join(BASE, "papers_figs")
os.makedirs(FIG_DIR, exist_ok=True)

KEYWORDS = re.compile(r"\b(schematic|overview|workflow|pipeline|architecture|framework|process)\b",
                      re.I)


def render_page(page, rect, zoom=2.0, dest=None):
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect)
    path = dest or os.path.join(FIG_DIR, "tmp.png")
    pix.save(path)
    return path, pix.width, pix.height


def figure_area(page):
    """估计页面图片总面积（像素）"""
    total = 0
    try:
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                w, h = doc_dims.get(xref, (0, 0))
            except Exception:
                w, h = 0, 0
            total += w * h
    except Exception:
        pass
    # 用绘图命令近似
    try:
        for d in page.get_drawings():
            r = d["rect"]
            total += max(int(r.width * r.height), 0)
    except Exception:
        pass
    return total


doc_dims = {}


def main():
    meta = json.load(open(os.path.join(BASE, "papers_meta.json"), encoding="utf-8"))
    info = {}
    for p in meta["papers"]:
        pid = p["id"]
        pdf = None
        for fn in sorted(os.listdir(PAPER_DIR)):
            if fn.startswith(pid + "_") and fn.lower().endswith(".pdf"):
                pdf = os.path.join(PAPER_DIR, fn)
                break
        if not pdf:
            print(f"[{pid}] no pdf, skip")
            continue
        doc = fitz.open(pdf)
        for img in doc.get_page_images(0):
            doc_dims[img[0]] = (img[2], img[3])
        # 收集图1题注候选
        best = None  # (page_no, y0, page)
        for pno in range(min(doc.page_count, 10)):
            page = doc[pno]
            hits = []
            for tag in ("Fig. 1", "Figure 1", "FIG. 1", "Figure1"):
                for r in page.search_for(tag):
                    hits.append(r)
            h = page.rect.height
            hits = [r for r in hits if r.y0 > 0.20 * h and r.y0 < 0.90 * h]
            if hits:
                cand = max(hits, key=lambda r: r.y0)  # 最靠下的题注起点
                best = (pno, cand.y0, page)
                break
        out = None
        if best:
            pno, y0, page = best
            w, h = page.rect.width, page.rect.height
            rect = fitz.Rect(0, 0.04 * h, w, y0 - 4)
            if rect.height > 50:
                out = os.path.join(FIG_DIR, f"{pid}_fig1.png")
                path, pw, ph = render_page(page, rect, zoom=2.0, dest=out)
                info[pid] = {"method": "caption-fig1", "page": pno + 1, "file": out,
                             "w": pw, "h": ph}
                print(f"[{pid}] fig1 from page {pno+1} -> {out} ({pw}x{ph})")
        if not out:
            # 回退：关键词页整页渲染，选取图片命令面积最大页
            cands = []
            for pno in range(min(doc.page_count, 6)):
                page = doc[pno]
                if KEYWORDS.search(page.get_text()):
                    cands.append((figure_area(page), pno, page))
            if cands:
                _, pno, page = max(cands, key=lambda t: t[0])
                out = os.path.join(FIG_DIR, f"{pid}_page{pno+1}.png")
                path, pw, ph = render_page(page, page.rect, zoom=1.6, dest=out)
                info[pid] = {"method": "keyword-page", "page": pno + 1, "file": out,
                             "w": pw, "h": ph}
                print(f"[{pid}] fallback page {pno+1} -> {out} ({pw}x{ph})")
            else:
                out = os.path.join(FIG_DIR, f"{pid}_page1.png")
                path, pw, ph = render_page(doc[0], doc[0].rect, zoom=1.6, dest=out)
                info[pid] = {"method": "page1-fallback", "page": 1, "file": out,
                             "w": pw, "h": ph}
                print(f"[{pid}] page1 fallback -> {out}")
        doc.close()
    with open(os.path.join(FIG_DIR, "figs_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
