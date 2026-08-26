#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_pptx.py — 依据 summaries/summary_*.json 生成详细研究报告 PPT（16:9）。
结构（每个论文2页）：
  Page A：论文信息 + 内容讲解（背景/数据/方法/结果/创新点） + 论文 Scheme 图
  Page B：研究范式（范式标签 + 解析） + 研究框架解析（数据流 → 模型 → 训练 → 评估）
另加：封面 / 目录 / 背景与方法 / 领域全景 / 横向对比 / 趋势 / 结论 / 参考文献。
输出：deliverables/机器学习与人工智能在微流控中的应用_研究报告.pptx
"""
import json
import math
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SUM_DIR = os.path.join(BASE, "summaries")
FIG_DIR = os.path.join(BASE, "papers_figs")
DELIVER_DIR = os.path.join(BASE, "deliverables")
OUT = os.path.join(DELIVER_DIR, "机器学习与人工智能在微流控中的应用_研究报告.pptx")

NAVY = RGBColor(0x1F, 0x38, 0x64)
BLUE = RGBColor(0x2E, 0x74, 0xB5)
LIGHT = RGBColor(0xEA, 0xF0, 0xF7)
GRAY = RGBColor(0x59, 0x59, 0x59)
DARK = RGBColor(0x26, 0x26, 0x26)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GOLD = RGBColor(0xC5, 0x8F, 0x1B)
GREEN = RGBColor(0x2E, 0x7D, 0x5B)

FONT = "微软雅黑"
SW, SH = 13.333, 7.5

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except Exception:
    HAS_PIL = False


def set_font(run, size=11, bold=False, color=DARK, name=FONT, italic=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    f.name = name
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", name)


def add_box(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, shadow=False):
    sp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1.0)
    sp.shadow.inherit = False
    return sp


def add_text(slide, x, y, w, h, items, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             line_spacing=1.0, space_after=4):
    """items: list of (text, size, bold, color) 或 (text, size, bold)"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, it in enumerate(items):
        text, size, bold = it[0], it[1], it[2]
        color = it[3] if len(it) > 3 else DARK
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = text
        set_font(r, size=size, bold=bold, color=color)
    return tb


def est_lines(text, width_in, font_pt):
    cpl = max(1, int(width_in * 72 / (font_pt * 1.02)))
    n = 0
    for seg in str(text).split("\n"):
        n += max(1, math.ceil(len(seg) / cpl))
    return n


def fit_size(text, width_in, height_in, base=11.5, floor=8.0):
    s = base
    while s > floor and est_lines(text, width_in, s) * (s * 1.42) / 72 > height_in:
        s -= 0.5
    return max(s, floor)


def add_bullets(slide, x, y, w, h, bullets, base=11.5, lead_color=BLUE, body_color=DARK):
    """bullets: list of (lead, body) —— lead 加粗，body 跟随"""
    size = fit_size("".join([b[0] + b[1] for b in bullets]), w, h, base=base)
    items = []
    for lead, body in bullets:
        items.append((f"▪ {lead}   ", size, True, lead_color))
        # body 与 lead 在同一段落较长时拆段
        if body:
            items.append((body, size, False, body_color))
    add_text(slide, x, y, w, h, items, line_spacing=0.92, space_after=3)


def add_title_bar(slide, title, subtitle=None):
    add_box(slide, 0, 0, SW, 0.95, fill=NAVY)
    add_text(slide, 0.45, 0.10, 10.6, 0.78, [(title, 21, True, WHITE)],
             anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        add_text(slide, 11.0, 0.10, 2.05, 0.78, [(subtitle, 11, True, RGBColor(0xBF, 0xD7, 0xEE))],
                 align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def add_pic_fit(slide, path, x, y, w, h):
    """在 box 内按比例放入图片，返回 (ix, iy, iw, ih)"""
    if not (path and os.path.exists(path)):
        add_box(slide, x, y, w, h, fill=LIGHT, line=BLUE)
        add_text(slide, x, y, w, h, [("Scheme 图暂缺（非OA或未下载PDF）", 11, True, GRAY)],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        return None
    try:
        if HAS_PIL:
            iw, ih = PILImage.open(path).size
        else:
            iw, ih = 4, 3
    except Exception:
        iw, ih = 4, 3
    scale = min(w / iw, h / ih)
    nw, nh = iw * scale * 96, ih * scale * 96  # 96dpi -> inches
    ix = x + (w - nw / 96) / 2
    iy = y + (h - nh / 96) / 2
    slide.shapes.add_picture(path, Inches(ix), Inches(iy), Inches(nw / 96), Inches(nh / 96))
    return (ix, iy, nw / 96, nh / 96)


def slide_cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_box(s, 0, 0, SW, SH, fill=NAVY)
    add_box(s, 0.55, 1.35, 3.1, 0.14, fill=GOLD)
    add_text(s, 0.55, 1.75, 11.5, 1.2, [("机器学习与人工智能", 40, True, WHITE)], space_after=0)
    add_text(s, 0.55, 2.75, 11.5, 1.2, [("在微流控中的应用", 40, True, WHITE)], space_after=0)
    add_text(s, 0.55, 4.05, 11.5, 0.5, [("Machine Learning & AI in Microfluidics", 17, False, RGBColor(0xBF, 0xD7, 0xEE))])
    add_text(s, 0.55, 4.65, 11.5, 0.9, [
        ("SCI 论文精读调研报告 ｜ 2020–2026 ｜ 共 21 篇 ｜ 中文为主", 15, True, GOLD),
        ("覆盖：数字微流控 ｜ 图像识别 ｜ 智能分选 ｜ 设计优化 ｜ 器官芯片 ｜ 诊断POCT ｜ 单细胞 ｜ 综述", 11.5, False, RGBColor(0xBF, 0xD7, 0xEE)),
    ], space_after=8)
    add_text(s, 0.55, 6.6, 11.5, 0.5, [("每篇论文 2 页：内容讲解+Scheme ／ 研究范式+框架解析", 12, False, WHITE)])
    return s


def slide_toc(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title_bar(s, "目录  Contents")
    items = [
        ("01", "调研背景与选文标准", "2020–2026 SCI 论文，8类代表性应用"),
        ("02", "领域全景", "数字微流控 / 图像识别 / 智能分选 / 设计优化 / 器官芯片 / 诊断POCT / 单细胞 / 综述"),
        ("03", "论文精读（每篇2页）", "内容讲解 + Scheme ／ 研究范式 + 框架解析"),
        ("04", "横向对比", "数据规模 · 任务 · 方法 · 核心指标"),
        ("05", "范式总结与趋势", "特征工程 → 深度学习 → 控制驱动/生成式/LLM → 多模态POCT"),
        ("06", "结论与展望", "智能微流控落地的关键路径"),
        ("07", "参考文献", "21篇论文完整题录"),
    ]
    y = 1.35
    for num, t1, t2 in items:
        add_box(s, 0.8, y, 0.62, 0.62, fill=BLUE)
        add_text(s, 0.8, y, 0.62, 0.62, [(num, 15, True, WHITE)], align=PP_ALIGN.CENTER,
                 anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, 1.6, y - 0.03, 10.6, 0.75, [
            (t1, 15, True, NAVY),
            (t2, 10.5, False, GRAY),
        ], space_after=1)
        y += 0.82
    return s


def slide_bg(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title_bar(s, "01 调研背景与选文标准")
    add_bullets(s, 0.7, 1.25, 6.2, 5.6, [
        ("背景", "微流控芯片能精确操控微尺度流体、液滴与单细胞，是生物医学与材料合成的基础平台；实验参数空间庞大、反馈慢、成像数据海量，AI/ML正成为加速设计、提升自动化与智能决策的关键工具。"),
        ("范围", "聚焦 2020–2026 年 SCI 期刊论文，覆盖 ML/AI 在数字微流控、液滴/细胞图像识别与分类、智能分选、设计优化、器官芯片、疾病诊断、单细胞分析与综述范式8类场景。"),
        ("方法", "OpenAlex / Crossref / Europe PMC / Unpaywall / Semantic Scholar / 出版社官网检索核验元数据；优先OA并允许第三方渠道获取PDF全文；按统一模板提取结构化信息。"),
        ("精读维度", "摘要 / 背景与问题 / 数据与任务 / 方法 / 关键结果 / 创新与局限 / 研究范式 / 研究框架解析 / Scheme解读 / 启示。"),
    ], base=12)
    add_box(s, 7.2, 1.25, 5.5, 5.6, fill=LIGHT, line=BLUE)
    add_text(s, 7.45, 1.45, 5.0, 0.5, [("选文标准", 14, True, NAVY)])
    add_bullets(s, 7.45, 2.0, 5.0, 4.6, [
        ("①", "SCI 收录期刊（Nature系 / Springer / Elsevier / MDPI / Frontiers 等）"),
        ("②", "主题为 ML/AI × 微流控或细胞图像分析"),
        ("③", "优先开放获取，保证PDF全文精读"),
        ("④", "覆盖多维度应用与方法学多样性"),
        ("⑤", "方法代表性：CNN / ViT / 自监督 / 迁移学习 / 基础模型 / 传统ML"),
    ], base=11, lead_color=NAVY)
    return s


def slide_panorama(prs, summaries):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title_bar(s, "02 领域全景：ML/AI × 微流控八大应用方向")
    groups = [
        ("设计优化", "液滴/芯片设计 · 参数优化 · LLM · 数字孪生", ["design_opt"], BLUE),
        ("数字微流控", "DMF 液滴操控 · 多态控制 · 无标记分选", ["dmf"], BLUE),
        ("图像识别", "液滴/细胞图像 · 成像流式 · 无标记", ["image_cell"], GREEN),
        ("智能分选", "实时分选 · FPGA 加速 · 液滴分类", ["droplet_class"], GREEN),
        ("器官芯片/单细胞", "药物筛选 · 器官芯片 · 机器人+AI", ["organ_chip", "single_cell"], GOLD),
        ("诊断/POCT", "CTC · 外泌体SERS · 纸基微流控", ["diagnostics"], GOLD),
        ("综述与范式", "智能微流控 · 可穿戴集成 · AI×微系统", ["review"], GOLD),
        ("合成制造", "钙钛矿量子点 · 材料合成优化", ["synthesis"], GOLD),
    ]
    w, h = 3.05, 2.35
    pos = [(0.45, 1.35), (3.68, 1.35), (6.91, 1.35), (10.14, 1.35),
           (0.45, 4.05), (3.68, 4.05), (6.91, 4.05), (10.14, 4.05)]
    for (k, desc, kinds, col), (x, y) in zip(groups, pos):
        add_box(s, x, y, w, h, fill=LIGHT, line=col)
        add_box(s, x, y, w, 0.5, fill=col)
        add_text(s, x, y, w, 0.5, [(k, 12.5, True, WHITE)], align=PP_ALIGN.CENTER,
                 anchor=MSO_ANCHOR.MIDDLE)
        cnt = sum(1 for sm in summaries if sm.get("kind") in kinds)
        add_text(s, x + 0.12, y + 0.6, w - 0.24, 1.6, [
            (f"代表论文 {cnt} 篇", 11, True, col),
            (desc, 9.5, False, DARK),
        ], space_after=5)
    return s


def slide_paper_a(prs, s):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    kind_en = {"design_opt": "Design & Optimization", "dmf": "Digital Microfluidics",
               "image_cell": "Image Recognition", "droplet_class": "Classification & Sorting",
               "organ_chip": "Organ-on-Chip", "diagnostics": "Diagnostics",
               "single_cell": "Single-Cell Analytics", "review": "Review & Paradigm"}.get(s.get("kind"), "")
    add_title_bar(slide, f"论文 {s['id']} ｜ {s.get('title_zh', '')[:26]}",
                  f"{kind_en} · {s.get('kind_zh', '')}")
    # 元数据条
    add_text(slide, 0.55, 1.02, 12.2, 0.4, [
        (f"{s.get('journal', '')} · {s.get('year', '')} ｜ DOI: {s.get('doi', '')} ｜ 英文题名：{s.get('title_en', '')[:70]}",
         9.5, False, GRAY)])
    # 左列讲解
    add_bullets(slide, 0.5, 1.5, 6.55, 5.4, [
        ("背景与问题：", s.get("background_zh", "") + (" " + s.get("problem_zh", "") if s.get("problem_zh") else "")),
        ("数据与任务：", s.get("data_zh", "") + (" " + s.get("task_zh", "") if s.get("task_zh") else "")),
        ("方法要点：", s.get("method_zh", "")),
        ("关键结果：", s.get("results_zh", "")),
        ("创新点：", s.get("innovation_zh", "")),
    ], base=11.5)
    # 底部指标条
    y = 6.92
    ms = (s.get("metrics_zh") or [])[:3]
    x = 0.5
    for m in ms:
        label = m.get("label", "") if isinstance(m, dict) else str(m)
        value = m.get("value", "") if isinstance(m, dict) else ""
        w = 2.1
        add_box(slide, x, y, w, 0.5, fill=LIGHT, line=BLUE)
        add_text(slide, x, y, w, 0.5, [(f"{label}  {value}", 9.5, True, NAVY)],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += w + 0.12
    # 右列 Scheme
    add_text(slide, 7.25, 1.5, 5.6, 0.35, [("论文 Scheme", 13, True, NAVY)])
    add_pic_fit(slide, os.path.join(FIG_DIR, f"{s['id']}_fig1.png"), 7.25, 1.88, 5.6, 3.9)
    add_text(slide, 7.25, 5.85, 5.6, 1.5, [
        ("Scheme 解读：" + (s.get("scheme_zh", "") or "见报告正文"), 10, False, DARK),
    ], space_after=2)
    return slide


def chip_row(slide, y, tags, x0=0.55, w=2.45):
    x = x0
    for t in tags[:5]:
        bw = max(1.0, min(2.4, 0.3 + 0.24 * len(t)))
        add_box(slide, x, y, bw, 0.45, fill=BLUE if t else LIGHT)
        add_text(slide, x, y, bw, 0.45, [(t, 10, True, WHITE)], align=PP_ALIGN.CENTER,
                 anchor=MSO_ANCHOR.MIDDLE)
        x += bw + 0.15
        if x > 12.8:
            break


def slide_paper_b(prs, s):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title_bar(slide, f"论文 {s['id']} ｜ {s.get('title_zh', '')[:22]}",
                  "研究范式 Research Paradigm")
    tags = s.get("paradigm_tags") or []
    add_text(slide, 0.55, 1.05, 3.0, 0.4, [("范式标签", 11, True, NAVY)])
    chip_row(slide, 1.5, tags)
    # 范式解析
    add_box(slide, 0.55, 2.12, 12.2, 1.15, fill=LIGHT, line=BLUE)
    add_text(slide, 0.75, 2.22, 11.8, 0.35, [("研究范式解析", 12, True, NAVY)])
    add_text(slide, 0.75, 2.58, 11.8, 0.65, [(s.get("paradigm_zh", ""), 10.5, False, DARK)])
    # 框架步骤
    add_text(slide, 0.55, 3.42, 6.0, 0.35, [("研究框架解析：数据流 → 模型 → 训练 → 评估 / 解读", 12, True, NAVY)])
    steps = s.get("framework_steps") or ["数据与预处理", "模型设计", "训练策略", "评估与解读"]
    bw, gap = 2.75, 0.35
    x0 = 0.55
    for i, st in enumerate(steps):
        x = x0 + i * (bw + gap)
        add_box(slide, x, 3.82, bw, 1.7, fill=LIGHT, line=BLUE)
        head = st[:14]
        body = st[14:] if len(st) > 14 else ""
        add_text(slide, x + 0.08, 3.92, bw - 0.16, 1.5, [
            (f"STEP {i+1} {head}", 10.5, True, NAVY),
            (body, 9.5, False, DARK),
        ], space_after=3)
        if i < len(steps) - 1:
            add_text(slide, x + bw + 0.02, 4.35, gap + 0.05, 0.5, [("▶", 12, True, BLUE)],
                     align=PP_ALIGN.CENTER)
    # 框架总评 + 启示
    add_box(slide, 0.55, 5.72, 6.0, 1.5, fill=RGBColor(0xEF, 0xF5, 0xEA), line=GREEN)
    add_text(slide, 0.72, 5.82, 5.6, 0.3, [("框架总评", 11.5, True, GREEN)])
    add_text(slide, 0.72, 6.12, 5.66, 1.0, [(s.get("framework_zh", ""), 9.5, False, DARK)])
    add_box(slide, 6.75, 5.72, 6.0, 1.5, fill=RGBColor(0xFB, 0xF1, 0xE2), line=GOLD)
    add_text(slide, 6.92, 5.82, 5.6, 0.3, [("对本领域研究的启示", 11.5, True, GOLD)])
    add_text(slide, 6.92, 6.12, 5.66, 1.0, [(s.get("lessons_zh", ""), 9.5, False, DARK)])
    return slide


def slide_compare(prs, summaries):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title_bar(slide, "04 横向对比：任务 · 数据 · 方法 · 核心指标")
    rows, cols = len(summaries) + 1, 5
    tbl_shape = slide.shapes.add_table(rows, cols, Inches(0.4), Inches(1.1),
                                       Inches(12.5), Inches(6.0))
    tbl = tbl_shape.table
    widths = [1.6, 1.9, 2.8, 3.2, 3.0]
    for j, w in enumerate(widths):
        tbl.columns[j].width = Inches(w)
    heads = ["论文", "方向", "数据与任务", "方法", "核心指标"]
    for j, h in enumerate(heads):
        c = tbl.cell(0, j)
        c.text = h
        for p in c.text_frame.paragraphs:
            for r in p.runs:
                set_font(r, size=10, bold=True, color=WHITE)
        c.fill.solid(); c.fill.fore_color.rgb = NAVY
    tbl.rows[0].height = Inches(0.32)
    for i, s in enumerate(summaries, start=1):
        m0 = (s.get("metrics_zh") or [{}])[0]
        vals = [
            f"{s['id']} {s.get('title_zh','')[:14]}",
            s.get("kind_zh", "")[:12],
            (s.get("data_zh", "") + " / " + s.get("task_zh", ""))[:55],
            s.get("method_zh", "")[:72],
            f"{m0.get('label','') if isinstance(m0,dict) else ''}: {m0.get('value','') if isinstance(m0,dict) else ''}"[:30],
        ]
        for j, v in enumerate(vals):
            c = tbl.cell(i, j)
            c.text = str(v)
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    set_font(r, size=7.5, bold=(j == 0), color=DARK)
            if i % 2 == 0:
                c.fill.solid(); c.fill.fore_color.rgb = LIGHT
        tbl.rows[i].height = Inches(0.36)
    return slide


def slide_trends(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title_bar(s, "05 研究范式总结与发展趋势")
    trends = [
        ("传统ML + 特征工程", "液滴尺寸/压力/光谱峰等物理特征 + SVM/RF/XGBoost；可解释、轻量，依赖先验。"),
        ("端到端深度学习", "CNN / YOLO / 成像流式直接学习液滴与细胞图像；主流范式，精度高、需大量标注。"),
        ("物理信息/控制驱动学习", "RL + 数字孪生 + 贝叶斯优化实现液滴生成、蒸发、芯片参数的闭环自适应优化。"),
        ("生成式与逆向设计", "GAN/VAE/扩散模型/LLM将目标功能反向生成芯片结构与实验条件，实现自主设计。"),
        ("多模态集成与POCT", "图像+光谱+组学+临床信息融合，驱动CTC、外泌体、纸基POCT诊断落地。"),
    ]
    y = 1.25
    for i, (k, v) in enumerate(trends):
        col = BLUE if i % 2 == 0 else GREEN
        add_box(s, 0.55, y, 12.2, 1.05, fill=LIGHT, line=col)
        add_text(s, 0.75, y + 0.06, 3.0, 0.9, [(k, 12.5, True, col)], anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, 3.85, y + 0.06, 8.7, 0.9, [(v, 10.5, False, DARK)], anchor=MSO_ANCHOR.MIDDLE)
        y += 1.14
    add_text(s, 0.55, 6.6, 12.2, 0.6, [
        ("趋势：多中心跨设备验证 ｜ 自监督/基础模型降标注 ｜ 从分类分割走向溯源与功能推断 ｜ 可解释性与临床前瞻性研究并重", 11, True, NAVY)])
    return s


def slide_conclusion(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title_bar(s, "06 结论与展望")
    add_bullets(s, 0.7, 1.3, 12.0, 5.5, [
        ("① AI 已成为智能微流控的核心引擎", "从液滴图像识别、细胞分选到芯片设计优化、器官芯片预测，覆盖全链条。"),
        ("② 端到端深度学习与自主控制并行发展", "CNN/YOLO 提升识别精度，RL/数字孪生/LLM 实现设计-运行闭环，二者互补。"),
        ("③ 微流控+AI正在走向多模态与POCT", "图像+光谱+临床信息融合，驱动CTC、外泌体、纸基诊断等高通量低成本的现场检测。"),
        ("④ 工程落地需要可解释、可重复与低算力", "FPGA实时推理、轻量模型、开放数据集与标准化接口是转化关键。"),
        ("⑤ 综述构建方法学闭环", "智能微流控、AI×微系统、机器人+AI单细胞等综述推动「数据-算法-硬件-应用」范式化。"),
    ], base=13, lead_color=NAVY)
    return s


def slide_refs(prs, summaries):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title_bar(s, "07 参考文献（21篇）")
    half = (len(summaries) + 1) // 2
    for i, sm in enumerate(summaries):
        col = 0 if i < half else 1
        x = 0.55 + col * 6.3
        yy = 1.15 + (i % half) * 0.62
        add_text(s, x, yy, 6.0, 0.6, [
            (f"[{i+1}] {sm.get('title_en','')[:60]}…  {sm.get('journal','')} {sm.get('year','')}",
             7.5, False, DARK)], space_after=0)
    return s


def main():
    os.makedirs(DELIVER_DIR, exist_ok=True)
    summaries = []
    for fn in sorted(os.listdir(SUM_DIR)):
        if not fn.endswith(".json"):
            continue
        s = json.load(open(os.path.join(SUM_DIR, fn), encoding="utf-8"))
        if s.get("method_zh"):
            summaries.append(s)
    summaries.sort(key=lambda s: s["id"])

    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    slide_cover(prs)
    slide_toc(prs)
    slide_bg(prs)
    slide_panorama(prs, summaries)
    for s in summaries:
        slide_paper_a(prs, s)
        slide_paper_b(prs, s)
    slide_compare(prs, summaries)
    slide_trends(prs)
    slide_conclusion(prs)
    slide_refs(prs, summaries)
    prs.save(OUT)
    print("PPTX written:", OUT, "slides:", len(prs.slides._sldIdLst), "papers:", len(summaries))


if __name__ == "__main__":
    main()
