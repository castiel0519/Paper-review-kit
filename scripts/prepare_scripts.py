#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_scripts.py — 从 ../cell_morph_ai_review/scripts 复制通用脚本并做主题补丁：
- 复制 extract_text.py / extract_figs.py / init_summaries.py / make_docx.py / make_pptx.py / verify_deliverables.py
- 将「细胞形态学」主题统一替换为「微流控」主题
- 替换报告导读、领域全景、范式总结、结论等硬编码内容为微流控 8 类场景
运行后即可进入：verify_meta -> download -> extract -> figs -> init_summaries -> 精读 -> make_docx/make_pptx -> verify
"""
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = HERE
TEMPLATE_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "cell_morph_ai_review", "scripts"))
COPIED = ["extract_text.py", "extract_figs.py", "init_summaries.py",
          "make_docx.py", "make_pptx.py", "verify_deliverables.py"]

DOCX_OUT_NEW = "机器学习与人工智能在微流控中的应用_读书报告.docx"
PPTX_OUT_NEW = "机器学习与人工智能在微流控中的应用_研究报告.pptx"

# ---------- make_docx 补丁 ----------
DOCX_SIX_LINE_OLD = """    for line in [
        "① 血液细胞形态学（外周血涂片、白细胞分类、骨髓涂片、疟疾感染红细胞）",
        "② 肿瘤脱落细胞学（宫颈细胞学分级、尿液液基细胞学尿路上皮癌筛查）",
        "③ 循环肿瘤细胞（CTC）检测与病灶溯源",
        "④ 显微成像细胞分割（Cellpose 等通才分割算法）",
        "⑤ 形态学表型组学（Cell Painting、高内涵筛选、化合物性质预测）",
        "⑥ 基础模型（病理学通用基础模型、跨设备细胞相似性检索）",
    ]:"""
DOCX_SIX_LINE_NEW = """    for line in [
        "① 数字微流控（DMF：液滴操控、细胞分选、多态控制）",
        "② 液滴/细胞图像识别与分类（CNN、YOLO、成像流式、无标记液滴分类）",
        "③ 液滴/细胞分选与实时控制（FPGA 加速、无标记并行分选）",
        "④ 实验设计与参数优化（逆向设计、LLM 自主设计、数字孪生）",
        "⑤ 器官芯片/生物传感/药物筛选（digital twin 肝芯片、AI 药物筛选）",
        "⑥ 疾病诊断与 POCT（CTC 全息成像、外泌体 SERS、纸基微流控）",
        "⑦ 单细胞分析与高通量成像（机器人+AI、运动敏感干涉成像）",
        "⑧ 综述与范式（智能微流控、可穿戴集成、AI×微系统）",
    ]:"""

DOCX_TRENDS_OLD = """    trends = [
        ("范式一：传统机器学习 + 人工特征", "以定量相位成像(QPI)、形态学描述子（面积/圆度/纹理/几何矩）为输入，配合SVM、随机森林等分类器。优点是可解释性强、计算量小；缺点是特征工程依赖专家先验，泛化受成像设备影响。"),
        ("范式二：端到端深度学习（CNN/ViT）", "以细胞图像/WSI为直接输入，通过EfficientNet、ResNet、MobileNet、Vision Transformer等端到端学习形态学判别。是目前血液学与细胞学应用的主流范式，精度高但需要大量标注。"),
        ("范式三：迁移学习与领域自适应", "利用ImageNet预训练或病理预训练模型，通过微调迁移到细胞形态学任务（如CTC病灶溯源、跨设备细胞检索），显著降低标注与设备差异成本。"),
        ("范式四：自监督与表征学习", "在无标注的细胞图像上通过对比学习、重构、预测学任务学习形态表征（如亚细胞表型自监督分类、Cell Painting自监督基因功能推断），潜力大，是解决标注稀缺的方向。"),
        ("范式五：基础模型（Foundation Model）", "在超大规模病理/细胞图像上预训练的通用模型（UNI等），提供可迁移的表征与零样本/少样本能力；多模型集成（model zoo）可提升跨设备鲁棒性。"),
        ("范式六：生成式与表示学习结合", "条件GAN、风格迁移等生成式方法用于形态学受限的新分子设计、表征学习与数据增强。"),
    ]"""
DOCX_TRENDS_NEW = """    trends = [
        ("范式一：传统ML + 特征工程", "以物理/几何特征（液滴直径、频率、压力、图像纹理、光谱峰）为输入，配合SVM、随机森林、XGBoost、贝叶斯回归；可解释性强、算力低，适用于液滴尺寸预测、生物标志物回归等。"),
        ("范式二：端到端深度学习（CNN/YOLO/TrackNet）", "以液滴/细胞图像、流动显微视频为直接输入，完成检测、分类、分割与追踪；在液滴分类、成像流式、细胞分选中成为主流，精度高但依赖标注与算力。"),
        ("范式三：物理信息/控制驱动学习（RL、digital twin）", "将流体力学物理约束或仿真器/数字孪生嵌入学习环，用深度强化学习、贝叶斯优化、代理模型实现液滴生成、芯片参数、蒸发控制的闭环自适应优化。"),
        ("范式四：生成式与逆向设计（GAN/VAE/扩散模型、LLM）", "由目标功能/图案反向生成芯片结构与实验条件，大语言模型进一步把领域知识文本化，实现自主设计框架与自然语言交互设计。"),
        ("范式五：多模态集成（图像+光谱+组学+临床）", "微流控SERS、无标记定量成像、芯片传感与临床信息融合，实现外泌体肺癌分型、CTC检测、牙周炎纸基诊断等POCT多模态分析。"),
        ("范式六：综述集成与范式化系统", "智能微流控（Matter 2020）、AI×微系统（Micromachines 2023）、机器人+AI单细胞（Lab Chip 2025）等综述构建「数据-算法-硬件-应用」闭环方法学体系。"),
    ]"""

# ---------- make_pptx 补丁 ----------
PPTX_KIND_MAP_OLD = """    kind_en = {"hematology": "Hematology", "cytology": "Cytology", "ctc": "CTC",
               "segmentation": "Segmentation", "phenotype": "Phenotype",
               "foundation": "Foundation Model"}.get(s.get("kind"), "")"""
PPTX_KIND_MAP_NEW = """    kind_en = {"design_opt": "Design & Optimization", "dmf": "Digital Microfluidics",
               "image_cell": "Image Recognition", "droplet_class": "Classification & Sorting",
               "organ_chip": "Organ-on-Chip", "diagnostics": "Diagnostics",
               "single_cell": "Single-Cell Analytics", "review": "Review & Paradigm"}.get(s.get("kind"), "")"""

PPTX_BG_OLD = """        ("背景", "细胞形态学检验（血涂片/骨髓涂片/脱落细胞学/显微成像）是疾病诊断的金标准之一；人工阅片耗时、主观、依赖专家，AI可显著提升效率与一致性。"),
        ("范围", "聚焦 2020–2025 年 SCI 期刊论文，覆盖机器学习/深度学习/人工智能在细胞形态学分析中的代表性工作。"),
        ("方法", "PubMed / Europe PMC / Unpaywall / Semantic Scholar / 出版社官网检索并核验元数据；对开放获取(OA)论文下载PDF全文精读；按统一模板提取结构化信息。"),
        ("精读维度", "摘要 / 背景与问题 / 数据与任务 / 方法 / 关键结果 / 创新与局限 / 研究范式 / 研究框架解析 / Scheme解读 / 启示。"),"""
PPTX_BG_NEW = """        ("背景", "微流控芯片能精确操控微尺度流体、液滴与单细胞，是生物医学与材料合成的基础平台；实验参数空间庞大、反馈慢、成像数据海量，AI/ML正成为加速设计、提升自动化与智能决策的关键工具。"),
        ("范围", "聚焦 2020–2026 年 SCI 期刊论文，覆盖 ML/AI 在数字微流控、液滴/细胞图像识别与分类、智能分选、设计优化、器官芯片、疾病诊断、单细胞分析与综述范式8类场景。"),
        ("方法", "OpenAlex / Crossref / Europe PMC / Unpaywall / Semantic Scholar / 出版社官网检索核验元数据；优先OA并允许第三方渠道获取PDF全文；按统一模板提取结构化信息。"),
        ("精读维度", "摘要 / 背景与问题 / 数据与任务 / 方法 / 关键结果 / 创新与局限 / 研究范式 / 研究框架解析 / Scheme解读 / 启示。"),"""

PPTX_TRENDS_OLD = """    trends = [
        ("传统ML + 人工特征", "QPI/形态学描述子 + SVM/RF；可解释、轻量，但依赖先验与成像设备。"),
        ("端到端深度学习", "CNN / ViT 直接学习细胞图像；主流范式，精度高、需大量标注。"),
        ("迁移学习/领域自适应", "ImageNet或病理预训练 + 微调；降低标注与人机差异成本（CTC溯源、跨设备检索）。"),
        ("自监督与表征学习", "无标注对比/重构学习形态表征；解决标注稀缺（亚细胞表型、CRISPR基因功能推断）。"),
        ("基础模型", "大规模病理/细胞图像预训练（UNI、model zoo），零/少样本可迁移能力。"),
    ]"""
PPTX_TRENDS_NEW = """    trends = [
        ("传统ML + 特征工程", "液滴尺寸/压力/光谱峰等物理特征 + SVM/RF/XGBoost；可解释、轻量，依赖先验。"),
        ("端到端深度学习", "CNN / YOLO / 成像流式直接学习液滴与细胞图像；主流范式，精度高、需大量标注。"),
        ("物理信息/控制驱动学习", "RL + 数字孪生 + 贝叶斯优化实现液滴生成、蒸发、芯片参数的闭环自适应优化。"),
        ("生成式与逆向设计", "GAN/VAE/扩散模型/LLM将目标功能反向生成芯片结构与实验条件，实现自主设计。"),
        ("多模态集成与POCT", "图像+光谱+组学+临床信息融合，驱动CTC、外泌体、纸基POCT诊断落地。"),
    ]"""

PPTX_CONCL_OLD = """        ("① AI 已成为细胞形态学分析的核心工具", "从分割、分类到溯源与功能推断，覆盖血液学、细胞学、表型组学全链条。"),
        ("② 深度学习在精度上全面超越传统特征方法", "但标注成本与跨设备泛化仍是落地瓶颈；自监督与基础模型是主要突破口。"),
        ("③ 形态学分析正走向多模态", "细胞形态与基因、药理、空间信息的联合建模将带来新的生物学发现范式。"),
        ("④ 临床落地需要严谨验证", "多中心前瞻性研究、可解释性、AI辅助人工复核将是标准配置。"),
        ("⑤ 开放数据与模型生态", "Cellpose、Cell Painting数据资源、病理基础模型等开源生态加速研究转化。"),"""
PPTX_CONCL_NEW = """        ("① AI 已成为智能微流控的核心引擎", "从液滴图像识别、细胞分选到芯片设计优化、器官芯片预测，覆盖全链条。"),
        ("② 端到端深度学习与自主控制并行发展", "CNN/YOLO 提升识别精度，RL/数字孪生/LLM 实现设计-运行闭环，二者互补。"),
        ("③ 微流控+AI正在走向多模态与POCT", "图像+光谱+临床信息融合，驱动CTC、外泌体、纸基诊断等高通量低成本的现场检测。"),
        ("④ 工程落地需要可解释、可重复与低算力", "FPGA实时推理、轻量模型、开放数据集与标准化接口是转化关键。"),
        ("⑤ 综述构建方法学闭环", "智能微流控、AI×微系统、机器人+AI单细胞等综述推动「数据-算法-硬件-应用」范式化。"),"""

PPTX_REF_TITLE_OLD = 'add_title_bar(s, "07 参考文献（15篇）")'
PPTX_REF_TITLE_NEW = 'add_title_bar(s, "07 参考文献（21篇）")'

PPTX_COVER_TAGS_OLD = '("覆盖：血液学 ｜ 肿瘤细胞学 ｜ CTC ｜ 显微分割 ｜ 表型组学 ｜ 基础模型", 12, False, RGBColor(0xBF, 0xD7, 0xEE)),'
PPTX_COVER_TAGS_NEW = '("覆盖：数字微流控 ｜ 图像识别 ｜ 智能分选 ｜ 设计优化 ｜ 器官芯片 ｜ 诊断POCT ｜ 单细胞 ｜ 综述", 11.5, False, RGBColor(0xBF, 0xD7, 0xEE)),'

PPTX_TOC_OLD = """        ("01", "调研背景与选文标准", "2020–2025 SCI 论文，六类代表性应用"),
        ("02", "领域全景", "血液学 / 肿瘤细胞学 / CTC / 分割 / 表型组学 / 基础模型"),
        ("03", "论文精读（每篇2页）", "内容讲解 + Scheme ／ 研究范式 + 框架解析"),
        ("04", "横向对比", "数据规模 · 任务 · 方法 · 核心指标"),
        ("05", "范式总结与趋势", "传统ML → 深度学习 → 自监督 → 基础模型"),
        ("06", "结论与展望", "临床落地关键路径"),
        ("07", "参考文献", "15篇论文完整题录"),"""
PPTX_TOC_NEW = """        ("01", "调研背景与选文标准", "2020–2026 SCI 论文，8类代表性应用"),
        ("02", "领域全景", "数字微流控 / 图像识别 / 智能分选 / 设计优化 / 器官芯片 / 诊断POCT / 单细胞 / 综述"),
        ("03", "论文精读（每篇2页）", "内容讲解 + Scheme ／ 研究范式 + 框架解析"),
        ("04", "横向对比", "数据规模 · 任务 · 方法 · 核心指标"),
        ("05", "范式总结与趋势", "特征工程 → 深度学习 → 控制驱动/生成式/LLM → 多模态POCT"),
        ("06", "结论与展望", "智能微流控落地的关键路径"),
        ("07", "参考文献", "21篇论文完整题录"),"""


def patch_file(path, repls):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in repls:
        if old not in content:
            print(f"  !! warn: pattern not found in {os.path.basename(path)}: {old[:60]}")
        content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def patch_panorama(path):
    """替换 make_pptx 的 slide_panorama 函数为微流控 8 类场景（4列×2行）。"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    start = content.index("def slide_panorama(prs, summaries):")
    end = content.index("def slide_paper_a(prs, s):")
    new_fn = '''def slide_panorama(prs, summaries):
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


'''
    content = content[:start] + new_fn + content[end:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("  panorama patched")


def patch_docx_six(path):
    patch_file(path, [(DOCX_SIX_LINE_OLD, DOCX_SIX_LINE_NEW),
                      ("研究方向：血液学 / 肿瘤细胞学 / CTC / 显微分割 / 表型组学 / 基础模型",
                       "研究方向：数字微流控 / 图像识别 / 智能分选 / 设计优化 / 器官芯片 / 诊断POCT / 单细胞 / 综述"),
                      (DOCX_TRENDS_OLD, DOCX_TRENDS_NEW),
                      ("机器学习与人工智能在细胞形态学分析中的应用_读书报告.docx", DOCX_OUT_NEW),
                      ("机器学习与人工智能在细胞形态学分析中的应用", "机器学习与人工智能在微流控中的应用"),
                      ("在细胞形态学分析中的应用", "在微流控中的应用"),
                      ("细胞形态学", "微流控"),
                      ("Machine Learning & Artificial Intelligence in Cell Morphology Analysis",
                       "Machine Learning & Artificial Intelligence in Microfluidics"),
                      ("A Reading Report on Recent SCI Publications (2020–2025)",
                       "A Reading Report on Recent SCI Publications (2020–2026)")])


def patch_pptx(path):
    patch_file(path, [
        (PPTX_KIND_MAP_OLD, PPTX_KIND_MAP_NEW),
        (PPTX_BG_OLD, PPTX_BG_NEW),
        (PPTX_TRENDS_OLD, PPTX_TRENDS_NEW),
        (PPTX_CONCL_OLD, PPTX_CONCL_NEW),
        (PPTX_REF_TITLE_OLD, PPTX_REF_TITLE_NEW),
        (PPTX_COVER_TAGS_OLD, PPTX_COVER_TAGS_NEW),
        (PPTX_TOC_OLD, PPTX_TOC_NEW),
        ("机器学习与人工智能在细胞形态学分析中的应用_研究报告.pptx", PPTX_OUT_NEW),
        ("机器学习与人工智能在细胞形态学分析中的应用", "机器学习与人工智能在微流控中的应用"),
        ("在细胞形态学分析中的应用", "在微流控中的应用"),
        ("细胞形态学", "微流控"),
        ("Machine Learning & AI in Cell Morphology Analysis", "Machine Learning & AI in Microfluidics"),
        ("SCI 论文精读调研报告 ｜ 2020–2025 ｜ 共 15 篇 ｜ 中英双语", "SCI 论文精读调研报告 ｜ 2020–2026 ｜ 共 21 篇 ｜ 中文为主"),
        ("每篇论文 2 页：内容讲解+Scheme ／ 研究范式+框架解析", "每篇论文 2 页：内容讲解+Scheme ／ 研究范式+框架解析"),
    ])
    patch_panorama(path)


def main():
    for name in COPIED:
        src = os.path.join(TEMPLATE_DIR, name)
        dst = os.path.join(SCRIPTS, name)
        if not os.path.exists(src):
            print(f"  !! template missing: {src}")
            continue
        shutil.copy2(src, dst)
        print("copied", name)
    make_docx = os.path.join(SCRIPTS, "make_docx.py")
    make_pptx = os.path.join(SCRIPTS, "make_pptx.py")
    verify = os.path.join(SCRIPTS, "verify_deliverables.py")
    if os.path.exists(make_docx):
        patch_docx_six(make_docx)
    if os.path.exists(make_pptx):
        patch_pptx(make_pptx)
    if os.path.exists(verify):
        patch_file(verify, [
            ("机器学习与人工智能在细胞形态学分析中的应用_读书报告.docx", DOCX_OUT_NEW),
            ("机器学习与人工智能在细胞形态学分析中的应用_研究报告.pptx", PPTX_OUT_NEW),
            ("细胞形态学", "微流控"),
        ])
    print("prepare done ->", SCRIPTS)


if __name__ == "__main__":
    main()
