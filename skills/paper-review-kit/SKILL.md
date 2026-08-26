---
name: paper-review-kit
description: 用内置 Python 脚本完成 SCI 论文调研全流程：元数据核验→合规/多源 PDF 下载→全文与 Scheme 提取→隔离精读→DOCX 读书报告 + 每篇两页 PPT（内容讲解+Scheme；研究范式+框架解析）。
whenToUse: 当用户要求批量调研某方向 SCI 论文、尽可能下载/精读 PDF 并生成读书报告与详细 PPT（每篇两页、含 Scheme 与研究范式/框架解析）时使用。
metadata:
  version: 0.1.0
---

# paper-review-kit 工作流

## 一句话原则
主会话不读论文全文：脚本负责检索、元数据核验、下载与文本/图提取；精读采用
“每篇独立文本文件 + 定向关键词检索 + 结构化 JSON”隔离方式；报告由脚本直接渲染 JSON。
主 agent 只做选题、任务设计与最终汇总（与 `paper-watch` 精读 schema 兼容，可配合其 host 工具）。

## 资源
- Base：`C:\Users\samue\.dsh\skills\paper-review-kit`
- `scripts/`：全部管线脚本（角色见 `scripts/README.md`）
- `templates/`：`papers_meta.example.json`（选题元数据样例）、`summary.example.json`（精读摘要样例）、
  `summaries_manual.example.py`（人工精读填充样例）、`project-README.example.md`（项目README样例）

## 使用步骤
1. **建项目**：`mkdir <project>`，把本技能的 `scripts/` 复制进 `<project>/scripts/`；
   用 `templates/papers_meta.example.json` 为模板编写 `papers_meta.json`（id/title/title_zh/journal/year/doi/pmid/pmcid/kind/kind_zh/notes）。
2. **主题化**：`python scripts/retheme.py --topic 癌症早筛 --topic-en Cancer Screening`
   （只改 make_docx/make_pptx/verify_deliverables 中的“微流控”措辞；人工复核通顺性）。
3. **跑前半程**：`bash scripts/run_pipeline.sh`
   自动执行：verify_meta → init_summaries → download_papers_fast → extract_text → extract_figs → digest_papers → condense_digests → augment_summaries。
4. **精读**：主 agent 只读 `digests/keyfacts.txt`（每篇 3–6KB），必要时 `grep` 定位 `papers_txt/<id>.txt`；
   为每篇写 `summaries/summary_<id>.json`（字段与长度约束见下；无全文的用 `pdf_status: abstract_only`）。
5. **生成**：`python scripts/make_docx.py`（读书报告）→ `python scripts/make_pptx.py`（每篇 2 页的 PPT）。
6. **自检**：`python scripts/verify_deliverables.py`（PDF/摘要/DOCX/PPTX 完整性）+
   `python scripts/check_layout.py`（PPT 溢出风险）；导出 PNG 预览用 PowerPoint COM
   （`$pres.Export(dir,'PNG',1280,720)`）。

## 精读输出 schema（与 paper-watch 一致）
字段：`id/title_en/title_zh/journal/year/doi/pmid/pmcid/kind/kind_zh/pdf_status/
abstract_en/abstract_zh/background_zh/problem_zh/data_zh/task_zh/method_zh/
results_zh/metrics_zh/innovation_zh/limitation_zh/paradigm_tags/paradigm_zh/
framework_zh/framework_steps/scheme_zh/lessons_zh/evidence_pages/figure_refs`。

长度上限：`method_zh/results_zh/framework_zh/scheme_zh` ≤1200 字，其余文本 ≤600 字；
`metrics_zh` 最多 5 条；`paradigm_tags` 3–8 个；`framework_steps` 4–6 条；
`pdf_status ∈ pdf_read | abstract_only | missing`，无全文时不得编造。

## PPT 结构要求
封面 / 目录 / 背景与选文 / 领域全景 + **每篇论文恰好 2 页**：
- 第 1 页：内容讲解（背景/数据/方法/结果/创新点）+ 论文 Scheme 图
- 第 2 页：研究范式（范式标签+解析）+ 研究框架解析（数据流→模型→训练→评估/解读）
结尾：横向对比 / 范式总结与趋势 / 结论与展望 / 参考文献。

## 合规
默认只下载合法可得 PDF：OpenAlex OA、Unpaywall、Europe PMC/PMC render、Semantic Scholar OA、
出版商 OA、用户有权限的机构代理。第三方渠道（如 Sci-Hub）仅在用户显式授权后尝试，
且失败原因（DNS/证书/403）如实记录，不得在报告中声称已获取未获得的全文。
