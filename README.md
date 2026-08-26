# ML/AI × 微流控：SCI 论文精读调研

## 目标
调研 15 篇以上机器学习/人工智能在微流控领域的代表性 SCI 论文，
优先下载开放获取（OA）全文 PDF（用户允许第三方渠道补充获取），精读后产出：

- 读书报告 DOCX（中文为主，英文题名保留）
- 详细报告 PPT（每篇论文 2 页：内容讲解 + 论文 Scheme ／ 研究范式 + 研究框架解析；
  另加封面/目录/背景/领域全景/横向对比/范式总结/结论/参考文献）

## 覆盖的 8 类应用场景
1. 数字微流控（DMF）
2. 液滴/细胞图像识别与分类
3. 液滴/细胞分选与实时控制
4. 实验设计与参数优化（含逆向设计、LLM、数字孪生）
5. 器官芯片/生物传感/药物筛选
6. 疾病诊断与 POCT（CTC、外泌体 SERS、纸基微流控）
7. 单细胞分析与高通量成像
8. 综述与范式（方法学、可穿戴集成、多模态）

## 目录结构（运行后生成）
```
ml_microfluidics_review/
├── README.md
├── papers_meta.json          # 候选论文元数据（20篇，含DOI/PMid/分类）
├── papers_meta_verified.json # Crossref/OpenAlex 核验后的元数据（含OA状态）
├── papers/                   # 下载的 PDF + results.json
├── papers_txt/               # 每篇 PDF 逐页文本（===PAGE n=== 标记）
├── papers_figs/              # 每篇论文 Scheme 图（fig1 裁剪/回退整页）
├── summaries/                # 每篇论文结构化精读摘要 summary_XX.json
├── deliverables/             # 最终 DOCX / PPTX
└── scripts/
    ├── search_microfluidics.py # OpenAlex 检索候选（可选）
    ├── verify_meta.py          # 元数据核验（Crossref/OpenAlex/Unpaywall）
    ├── download_papers.py      # OA 解析 + PDF 下载（含第三方回退）
    ├── extract_text.py         # PyMuPDF 逐页文本提取
    ├── extract_figs.py         # Scheme 图启发式提取
    ├── init_summaries.py       # 精读摘要模板初始化
    ├── make_docx.py            # 生成读书报告 DOCX
    ├── make_pptx.py            # 生成研究报告 PPTX（每篇2页）
    └── verify_deliverables.py  # 交付物自检
```

## 工作流
1. 元数据核验（Crossref/OpenAlex）→ 生成 papers_meta_verified.json
2. 下载 PDF（PMC / Unpaywall / Semantic Scholar / 出版商 / 第三方回退）→ papers/
3. PyMuPDF 逐页提取全文 → papers_txt/*.txt
4. 提取 Scheme 图 → papers_figs/*.png
5. 精读：每篇独立文本文件 + 定向检索关键段落 → summaries/summary_XX.json
6. 生成 DOCX + PPTX → deliverables/
7. 自检（PDF 魔数/页数、摘要字段、DOCX/PPTX 可打开、图片数）→ check_report.json

## 说明
- 本环境未提供 subagent 工具；精读采用「每篇独立文本文件 + 定向检索 + 独立摘要文件」的
  隔离方式，避免全文冗余地占用主上下文（等价于“任务分发—并行读取—汇总”）。
- 优先合法可得的 OA 全文；非 OA 论文按用户意愿尝试第三方渠道，并在报告中标注获取情况。
- 论文任务与指标不可直接横向比较，报告中会明确区分「方法学严谨性」与「临床/工程可用性」。

## GitHub 仓库说明
- **论文 PDF 不随仓库上传**（`.gitignore` 已排除 `papers/*.pdf`，仓库更轻量）。
  需要复现下载时：
  ```bash
  python scripts/verify_meta.py           # 生成 papers_meta_verified.json
  python scripts/download_papers_fast.py  # OA 优先并发下载 → papers/
  ```
  下载结果记录在 `papers/results.json`；失败论文可用 `python scripts/retry_downloads.py` 重试。
- **`skills/paper-review-kit`**：本次调研沉淀的可复用技能包（检索→下载→提取→精读→DOCX/PPT 全流程脚本与模板）。
  使用方法见 `skills/paper-review-kit/SKILL.md`；以后做同类调研可直接复用，主题词用
  `scripts/retheme.py --topic <主题> --topic-en <英文>` 一键替换。
- **主要交付物**：`deliverables/机器学习与人工智能在微流控中的应用_读书报告.docx` 与
  `deliverables/机器学习与人工智能在微流控中的应用_研究报告.pptx`（每篇论文 2 页）。

## 许可证
本项目源码与脚本采用 [MIT License](LICENSE) 开源：允许任意使用、修改、再分发与商业使用，
仅需保留版权与许可声明，使用风险自负。
（说明：仓库不含论文 PDF 全文，论文版权归原出版商与作者所有。）
