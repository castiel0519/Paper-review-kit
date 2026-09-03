#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_figs_new.py — Scheme/框架图提取 v2 候选实现。

不再把标题上方的整页区域当图。流程：
  1. 找 Fig.1/Scheme.1 标题块做锚点；
  2. 收集位图 get_image_info 与矢量图 get_drawings，过滤并聚类；
  3. 按贴合标题、水平对齐、面积和正文重叠评分；
  4. 只裁图块 bbox，输出最佳裁剪 + 压缩 view + 备用候选。
  5. 支持 papers_meta.json 的 figure_overrides 手工精确裁剪。
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    print("PyMuPDF not installed: pip install pymupdf")
    sys.exit(2)

from prk_config import (
    load_papers_meta, output_dir, parse_project_arg, write_json,
)

CAPTION_RE = re.compile(r"(?:fig(?:ure)?\.?|scheme)\s*1\b", re.I)
KEYWORD_RE = re.compile(r"\b(schematic|overview|workflow|pipeline|architecture|framework|process)\b", re.I)


def area(r):
    return max(0.0, (r[2] - r[0]) * (r[3] - r[1]))


def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def cluster(boxes, x_gap=20, y_gap=14):
    boxes = [b for b in boxes if b and area(b) > 0]
    if not boxes:
        return []
    boxes.sort(key=lambda b: (b[1], b[0]))
    clusters = []
    for b in boxes:
        placed = False
        for i, c in enumerate(clusters):
            h = min(c[2], b[2]) - max(c[0], b[0])
            v = max(c[1], b[1]) - min(c[3], b[3])
            if h > -x_gap and v < y_gap:
                clusters[i] = union([c, b])
                placed = True
                break
        if not placed:
            clusters.append(b)
    merged = []
    for b in clusters:
        placed = False
        for i, c in enumerate(merged):
            h = min(c[2], b[2]) - max(c[0], b[0])
            v = max(c[1], b[1]) - min(c[3], b[3])
            if h > -x_gap and v < y_gap * 2:
                merged[i] = union([c, b])
                placed = True
                break
        if not placed:
            merged.append(b)
    return merged


def text_blocks(page):
    out = []
    try:
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") == 0 and b.get("bbox"):
                out.append(b["bbox"])
    except Exception:
        pass
    return out


def text_overlap(box, blocks):
    if not blocks:
        return 0.0
    total = area(box)
    if total <= 0:
        return 0.0
    s = 0.0
    for tb in blocks:
        ox = max(0.0, min(box[2], tb[2]) - max(box[0], tb[0]))
        oy = max(0.0, min(box[3], tb[3]) - max(box[1], tb[1]))
        s += ox * oy
    return min(1.0, s / total)


def caption_anchors(page):
    anchors = []
    try:
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") != 0:
                continue
            text = " ".join("".join(s.get("text", "") for s in b.get("lines", [])).split())
            if CAPTION_RE.search(text):
                anchors.append((text.strip(), b.get("bbox")))
    except Exception:
        pass
    if not anchors:
        for tag in ("Fig. 1", "Figure 1", "FIG. 1", "Scheme 1"):
            for r in page.search_for(tag):
                anchors.append((tag, [r.x0, r.y0, r.x1, r.y1]))
    return anchors


def raster_boxes(page, page_rect):
    out = []
    try:
        page_area = page_rect.width * page_rect.height
        for img in page.get_image_info(xrefs=True):
            b = img.get("bbox") or []
            if len(b) != 4:
                continue
            w = b[2] - b[0]
            h = b[3] - b[1]
            if (w * h) < page_area * 0.003 or (w * h) > page_area * 0.9:
                continue
            if w < 30 or h < 30:
                continue
            out.append([b[0], b[1], b[2], b[3]])
    except Exception:
        pass
    return out


def vector_boxes(page, page_rect):
    out = []
    try:
        page_area = page_rect.width * page_rect.height
        for d in page.get_drawings():
            r = d.get("rect")
            if r is None:
                continue
            a = r.width * r.height
            if a < page_area * 0.003:
                continue
            if r.width > page_rect.width * 0.95 and r.height > page_rect.height * 0.95:
                continue
            if r.width < 20 or r.height < 20:
                continue
            out.append([r.x0, r.y0, r.x1, r.y1])
    except Exception:
        pass
    return cluster(out)


def score(page_rect, caption, cand):
    cap = caption[1]
    v_gap = cap[1] - cand[3]
    prox = max(0.0, 1.0 - abs(v_gap - 40) / 300.0)
    h_overlap = max(0.0, min(cand[2], cap[2]) - max(cand[0], cap[0]))
    h_width = max(1.0, min(cand[2] - cand[0], cap[2] - cap[0]))
    align = h_overlap / h_width
    page_area = page_rect.width * page_rect.height
    area_score = min(1.0, (area(cand) / page_area) * 6.0)
    hr = (cand[3] - cand[1]) / page_rect.height
    height_penalty = 1.0 if hr > 0.72 else (0.6 if hr > 0.55 else 0.0)
    return 0.40 * prox + 0.30 * align + 0.20 * area_score - 0.25 * height_penalty


def candidates_for_caption(page, caption, page_rect):
    cap_name, cap = caption
    blocks = text_blocks(page)
    cands = []
    for box in raster_boxes(page, page_rect) + vector_boxes(page, page_rect):
        if box[3] > cap[1] + 25 or box[1] > cap[1] + 5:
            continue
        if cap[1] - box[3] > 220:
            continue
        if text_overlap(box, blocks) > 0.30:
            continue
        cands.append({
            "bbox": [round(v, 1) for v in box],
            "score": round(score(page_rect, caption, box), 3),
            "method": "geo-anchor",
            "caption": cap_name,
            "page": page.number + 1,
        })
    # 合并垂直相邻、同列的多面板小图
    merged = []
    used = set()
    ordered = sorted(cands, key=lambda c: c["bbox"][1])
    for i, c in enumerate(ordered):
        if i in used:
            continue
        group = [c]
        used.add(i)
        for j in range(i + 1, len(ordered)):
            if j in used:
                continue
            o = ordered[j]
            v = c["bbox"][3] - o["bbox"][1]
            h = min(c["bbox"][2], o["bbox"][2]) - max(c["bbox"][0], o["bbox"][0])
            if -5 <= v <= 30 and h > -20:
                group.append(o)
                used.add(j)
                c = o
        if len(group) > 1:
            merged.append({
                "bbox": [round(v, 1) for v in union([g["bbox"] for g in group])],
                "score": round(sum(g["score"] for g in group) / len(group), 3),
                "method": "geo-anchor-multipanel",
                "caption": cap_name,
                "page": page.number + 1,
                "children": len(group),
            })
    cands.extend(merged)
    seen = {}
    for c in cands:
        key = tuple(c["bbox"])
        if key not in seen or c["score"] > seen[key]["score"]:
            seen[key] = c
    return sorted(seen.values(), key=lambda c: -c["score"])


def render_crop(page, bbox, dest, zoom=2.0):
    pad = 6
    r = fitz.Rect(max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                  min(page.rect.x1, bbox[2] + pad), min(page.rect.y1, bbox[3] + pad))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=r)
    dest.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(dest))
    return str(dest), pix.width, pix.height


def make_view(src, dst, max_width=1024):
    try:
        from PIL import Image
        im = Image.open(src)
        if im.width > max_width:
            im = im.resize((max_width, int(im.height * max_width / im.width)), Image.LANCZOS)
        im.save(dst)
        return dst
    except Exception:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if Path(src).exists() and str(src) != str(dst):
            shutil.copy2(src, dst)
        return dst


def override_bbox(p, page):
    ov = p.get("figure_overrides") or {}
    if not ov:
        return None
    if int(ov.get("page") or page.number + 1) != page.number + 1:
        return None
    b = ov.get("bbox")
    if isinstance(b, list) and len(b) == 4:
        return [float(x) for x in b]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", default="", help="逗号分隔论文 ID")
    parser.add_argument("--rebuild", action="store_true")
    cfg, args = parse_project_arg(parser)
    meta = load_papers_meta(cfg)
    papers_dir = output_dir(cfg, "papers")
    fig_dir = output_dir(cfg, "papers_figs")
    selected = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None
    info = {}
    for p in meta["papers"]:
        pid = str(p.get("id", ""))
        if selected is not None and pid not in selected:
            continue
        if not papers_dir.is_dir():
            continue
        pdf = next((f for f in sorted(papers_dir.iterdir())
                    if f.name.startswith(pid + "_") and f.suffix.lower() == ".pdf"), None)
        if not pdf:
            print(f"[{pid}] no pdf, skip")
            continue
        doc = fitz.open(str(pdf))
        best = None
        all_c = []
        for pno in range(min(doc.page_count, 12)):
            page = doc[pno]
            for cap in caption_anchors(page):
                cs = candidates_for_caption(page, cap, page.rect)
                all_c.extend(cs)
                if cs and (best is None or cs[0]["score"] > best[0]["score"]):
                    best = (cs[0], pno, page, cap)
        if best is None and doc.page_count:
            fb = None
            for pno in range(min(doc.page_count, 6)):
                page = doc[pno]
                if KEYWORD_RE.search(page.get_text()):
                    fb = (pno, page)
                    break
            if fb is None:
                fb = (0, doc[0])
            pno, page = fb
            best = ({
                "bbox": [0, 0, page.rect.width, page.rect.height],
                "score": 0.0, "method": "page-fallback", "caption": "",
                "page": pno + 1, "confidence": "low",
            }, pno, page, None)
        if best:
            cand, pno, page, cap = best
            primary = fig_dir / f"{pid}_fig1.png"
            ov = override_bbox(p, page)
            if ov:
                cand = {**cand, "bbox": ov, "method": "manual-override", "score": 1.0}
            path, pw, ph = render_crop(page, cand["bbox"], primary)
            view = fig_dir / f"{pid}_fig1_view.png"
            make_view(path, view)
            record = {
                "file": str(primary), "view": str(view),
                "page": cand.get("page", pno + 1), "bbox": cand.get("bbox"),
                "method": cand.get("method", "geo-anchor"), "score": cand.get("score"),
                "confidence": cand.get("confidence", "high" if (cand.get("score") or 0) > 0.55 else "medium"),
                "caption": cand.get("caption", ""), "w": pw, "h": ph,
            }
            info[pid] = record
            print(f"[{pid}] {record['method']} page {record['page']} score={record['score']} -> {primary.name} ({pw}x{ph})")
            scored = sorted(all_c, key=lambda c: -c["score"])
            alt_i = 0
            for alt in scored:
                if alt.get("page") != record["page"] or alt.get("bbox") == cand["bbox"]:
                    continue
                alt_i += 1
                alt_path = fig_dir / f"{pid}_alt{alt_i}.png"
                render_crop(doc[alt["page"] - 1], alt["bbox"], alt_path, zoom=1.8)
                record.setdefault("alternatives", []).append({
                    "file": str(alt_path), "page": alt["page"], "bbox": alt["bbox"],
                    "score": alt.get("score"), "method": alt.get("method"),
                })
                if alt_i >= 2:
                    break
        else:
            info[pid] = {"method": "none", "confidence": "none"}
            print(f"[{pid}] no candidate")
        doc.close()
    write_json(fig_dir / "figs_info.json", info)
    print(f"done: extracted={sum(1 for v in info.values() if v.get('file'))}/{len(meta['papers'])}")


if __name__ == "__main__":
    main()
