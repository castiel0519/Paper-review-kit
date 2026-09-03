# Changelog

## v0.2.0 — M1 去专案化（2026-09）

### 核心变化

- **project.yml 配置驱动**：新增项目级配置，标题/主题/年份范围/报告叙事/下载参数/
  第三方下载开关全部从配置读取；新增 `templates/project.example.yml`。
- **单源脚本**：实现收敛到 `skills/paper-review-kit/scripts/`；根目录 `scripts/`
  保留同名兼容 wrapper，不再维护两份实现。
- **去除微流控专案硬编码**：报告渲染不再写死“微流控/21篇/2026-08”等内容；
  旧专案样例归档到 `examples/microfluidics/`。
- **补充下载 URL 配置化**：手动 URL / XML PMCID 迁入 `papers_meta.json` 的
  `manual_urls` / `download_overrides` / `xml_pmcid` 字段，删除脚本内
  `MANUAL_URLS` / `TARGETS` / `PMCID` 硬编码。

### 数据契约修复

- `pdf_status` 统一为 `pdf_read | abstract_only | missing`；
  `init_summaries.py` 默认写入 `missing`，校验器强制枚举。
- 新增 `papers_meta.json` 与 `summaries/*.json` 轻量 schema 校验
  （`prk_schema.py`，无外部依赖）。

### 合规修复

- 第三方渠道（Sci-Hub）默认关闭；只有 `project.yml` 的
  `compliance.allow_third_party: true` 或命令行 `--allow-third-party` 才启用。
- `retheme.py` 不再修改渲染脚本源码，只写 `project.yml`。

### 健壮性修复

- 修复 Crossref 年份始终为 `None`（解析 published-print/online 等字段）。
- 下载改为流式写 `.part` + 原子 rename，修复旧版整包读内存与 Windows 下魔数校验 bug。
- `papers/`、`papers_txt/`、`digests/` 等目录缺失时安全跳过，不再中断流水线。
- 报告渲染纳入所有已有 summary（不再静默丢弃未完成精读的论文），并标注全文状态。
- `verify_deliverables.py` 增加 `pdf_status` 枚举与“每篇 2 页”PPT 结构检查。
- 新增本地回归测试 `tests/test_m1.py`（不访问网络）。

### 兼容性

- 旧 `scripts/*.py` 文件名保留为 wrapper，旧命令仍可执行。
- 无 `project.yml` 的旧项目继续从 `papers_meta.json` 的 `title/range` 读取报告标题。

## v0.3.0 — Scheme v2 + Token 分层 + 综述（2026-09）

### Scheme 提取 v2
- 不再把 Fig.1 标题上方整页当图裁剪。
- 标题锚点 + 位图/矢量图块检测 + 评分，只裁真实图块。
- 输出 `figs_info.json` 候选集和 `_fig1_view.png` 压缩视图。
- 支持 `figure_overrides` 手工精确裁剪；渲染器优先读 `summary.scheme_image`。
- 视觉子 Agent 从候选中确认，报告保留原图。

### Token 分层与精读链路
- `digest_papers.py` 重构：定长、按 section、页码修正、去除数字噪声。
- `condense_digests.py` 改为压缩版（每篇 ≤1.2k 字符）。
- 新增 `make_brief.py`：主 Agent 只读 `brief.txt`，每篇 ≤320 字符。
- 新增 `save_summary.py`：子 Agent 经 stdin 落盘，避免 write/edit 全文回显。
- `papers_meta.json` 增加 `read_depth`；summary 强制 `evidence_pages` / `figure_refs`。
- Scheme/报表日志输出更精简。

### 自然语言综述
- 新增 `make_review_material.py`：生成带引用的综述素材包。
- 新增 `make_review_docx.py`：综述 MD 转 DOCX / 可追加读书报告。
- 新增 `verify_review.py`：校验综述引用编号。
- 新增 `templates/review_template.md` 综述骨架。

### 验证
- 新增 `tests/test_v3.py`、`ab_compare.py`，覆盖 save_summary、brief、引用校验。
