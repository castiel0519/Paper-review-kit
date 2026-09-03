---
name: paper-review-kit
description: 用内置 Python 脚本完成 SCI 论文调研全流程：元数据核验→合规/多源 PDF 下载→全文与 Scheme 提取→隔离精读→DOCX 读书报告 + 每篇两页 PPT + 可选的调研综述。配置由 project.yml 驱动。
whenToUse: 当用户要求批量调研某方向 SCI 论文、下载/精读 PDF、生成读书报告与详细 PPT，或后续需要自然语言综述时使用。
metadata:
  version: 0.3.0
---

# paper-review-kit 工作流

## 一句话原则
主 Agent 不读论文全文，也不读超大 digest；只读 `digests/brief.txt`。
子 Agent 读 `digests/<id>.md` + 定向 grep + 压缩 Scheme view，用 `save_summary.py` 落盘。

## 项目脚本
复制 `scripts/` 到项目，配置 `project.yml` 与 `papers_meta.json`。
关键字段：
- `read_depth`: `brief | targeted（默认） | full`
- `figure_overrides`: 手工指定 Scheme 页与 bbox
- `manual_urls` / `download_overrides` / `xml_pmcid`: 下载与 XML 降级

## 执行步骤
1. `bash scripts/run_pipeline.sh`：核验 → 建模板 → 下载 → 提取 → digest。
2. 精读：主 Agent 只读 `digests/brief.txt`（由 `make_brief.py` 从 summaries 生成）。
3. 子 Agent 任务卡：一次一篇，输入 `digests/<id>.md`、可选 `papers_txt/<id>.txt`（仅 grep）、`papers_figs/<id>_fig1_view.png`；输出写 `summaries/summary_<id>.json`。
4. 写 summary 用 `python scripts/save_summary.py --id <id>`（stdin JSON），不要用 write/edit 回显全文。
5. Scheme 确认：视觉子 Agent 看 `papers_figs/figs_info.json`，若默认 `_fig1.png` 不是框架图，把选中的图写入 summary `scheme_image`。
6. `python scripts/make_brief.py` → `make_docx.py` → `make_pptx.py`。
7. 自检：`verify_deliverables.py` + `check_layout.py`。
8. 可选综述：`make_review_material.py` → 综述子 Agent 使用 `templates/review_template.md` 写 `deliverables/{title}_调研综述.md` → `make_review_docx.py` → `verify_review.py`。

## 主/子 Agent 协作
- 每次只派一篇；子 Agent 必须先写 `summary_<id>.json` 再返回。
- 主 Agent 按文件存在性回收；失败只重试该篇。
- `pdf_read` 必须给 `evidence_pages` / `figure_refs`，否则不能算完成。

## 输出 schema 要点
- `pdf_status`: `pdf_read | abstract_only | missing`
- `pdf_read` 必填：`evidence_pages`、`figure_refs`
- 长度上限：method/results/framework/scheme ≤1200 字，其余 ≤600 字
- `metrics_zh` ≤5 条；`paradigm_tags` 3–8；`framework_steps` 4–6

## PPT 要求
每篇 2 页；第 1 页内容讲解 + Scheme，第 2 页研究范式 + 框架解析。

## 合规
第三方渠道默认关闭；仅 `allow_third_party: true` 或命令行允许时尝试。
