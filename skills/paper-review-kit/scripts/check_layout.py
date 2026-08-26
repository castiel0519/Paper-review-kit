# -*- coding: utf-8 -*-
"""
check_layout.py — 用 python-pptx 检查每页文本是否可能溢出文本框/幻灯片边界（近似字符宽度估算）。
输出 layout_report.json：每个违约的 shape 记录。
"""
import json
import math
import os

from pptx import Presentation
from pptx.util import Emu

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PPTX = os.path.join(BASE, "deliverables", "机器学习与人工智能在微流控中的应用_研究报告.pptx")


def est_overflow(slide_no, shape):
    tf = shape.text_frame
    w_in = shape.width / 914400.0 if shape.width else 1
    h_in = shape.height / 914400.0 if shape.height else 1
    total_lines = 0
    overflow = False
    for para in tf.paragraphs:
        text = "".join(r.text for r in para.runs)
        if not text:
            total_lines += 0.3
            continue
        size = 12.0
        for r in para.runs:
            if r.font.size:
                size = r.font.size.pt
                break
        cpl = max(1, int(w_in * 72 / (size * 1.02)))
        lines = max(1, math.ceil(len(text) / cpl))
        total_lines += lines * (size * 1.35) / 72.0
    est_h = total_lines
    if est_h > h_in * 1.15 + 0.05:
        overflow = True
    return overflow, round(est_h, 2), round(h_in, 2)


def main():
    prs = Presentation(PPTX)
    issues = []
    total_shapes = 0
    for i, slide in enumerate(prs.slides, start=1):
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            total_shapes += 1
            try:
                overflow, est, box = est_overflow(i, sh)
            except Exception:
                continue
            if overflow and est > box * 1.35:
                issues.append({"slide": i, "shape": sh.name,
                               "est_in": est, "box_in": box,
                               "text": sh.text_frame.text[:60]})
    report = {"slides": len(prs.slides._sldIdLst), "total_text_shapes": total_shapes,
              "probable_overflows": len(issues), "issues": issues[:20]}
    with open(os.path.join(BASE, "layout_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
