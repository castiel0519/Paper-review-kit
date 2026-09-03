# Paper-Review-Kit 下一阶段改动清单

> 状态：M1 已完成。本文件汇总已确认、待实施的改动。

## 已完成（M1 v0.2.0）

- project.yml 配置驱动
- 去微流控专案硬编码
- 单一事实源：实现收敛到 `skills/paper-review-kit/scripts/`
- `pdf_status` 枚举统一：`pdf_read | abstract_only | missing`
- 第三方下载默认关闭，`allow_third_party` 开关
- manual_urls / download_overrides / xml_pmcid 配置化
- Crossref 年份修复、目录缺失容错、流式下载 + 原子写入
- 旧微流控样例归档到 `examples/microfluidics/`
- 回归测试 `tests/test_m1.py`

---

## 待实施

### A. Scheme 提取 v2（已确认）

**问题**：旧算法把 Fig.1 标题以上的整页宽度区域当图裁剪，导致裁到
空条、正文大段文字或随机图片。

**改动**：

1. 新增 `extract_figs_v2.py`（或重写 `extract_figs.py`）：
   - 用 Fig.1 / Scheme 1 标题 bbox 做锚点
   - `get_image_info` 找位图 + `get_drawings` 找矢量图
   - 过滤 logo/背景/小碎片，矢量图聚类成图块
   - 按“贴合标题、水平对齐、面积合理、少包正文”评分
   - 只裁候选 bbox + padding，不再裁整页宽度
   - 输出 `{id}_fig1.png` + 候选 `{id}_altN.png` + `figs_info.json`
2. 支持人工精确覆盖：`papers_meta.json` 的
   `figure_overrides: {page, bbox}`，检测到就按 bbox 裁。
3. 渲染器 `make_docx.py` / `make_pptx.py` 优先读
   `summary.scheme_image`，不再无脑用 `{id}_fig1.png`。
4. SKILL 增加视觉子 Agent 裁决步骤：从 `figs_info.json` 候选里选真正的
   Scheme，把选择写回 summary。
5. `verify_deliverables.py` 检查 `scheme_image` 存在、候选来源、低置信度
   图片是否已视觉确认。

**验证**：用本地 3 篇真实 PDF（AML / Sickle Cell / Holotomography）做
before/after 对比。

### B. Token 优化（已确认，先做无损项 + 分级读取）

**问题**：主 Agent 读超大 keyfacts.txt；子 Agent 全文读 PDF；write/edit
回显全文；视觉输入未分级。

**改动**：

1. 重构 `digest_papers.py` / `condense_digests.py`：
   - digest 定长、按 section 结构化
   - 修页码错位、大小写不匹配、摘要重复、数字行噪声
   - 默认每篇 digest ≤ 2KB，供子 Agent 使用
2. 新增 `make_brief.py`：从 `summaries/*.json` 生成
   `digests/brief.txt`（每篇 ≤150 token 的路由信息）；主 Agent 只读 brief。
3. 新增 `save_summary.py`：子 Agent 用 stdin 落盘 JSON，脚本校验后只打印
   一行结果，避免 write/edit 全文回显。
4. `papers_meta.json` 增加 `read_depth`：
   `brief | targeted（默认）| full`；默认子 Agent 读 digest + 图 + 定向 grep。
5. 证据强制：summary 必须填 `evidence_pages` / `figure_refs`；
   `prk_schema.py` 校验非空。
6. 视觉输入只给 ≤1024px 的 `_fig1_view.png`，报告保留原图。
7. 日志瘦身：`verify_deliverables.py` / `check_layout.py` 只打印
   OK/FAIL 单行，不打印完整 JSON。
8. SKILL.md 瘦身，只保留命令表和主/子 Agent 读取边界。

**验证**：5 篇论文 A/B 对照：
事实错误、遗漏指标、方法还原度、Scheme 判读、证据链、幻觉计数。

### C. 子 Agent 交接硬化（部分在 SKILL，完整版留到 DSH 薄插件）

**问题**：主 Agent 分发视觉精读任务时偶尔卡在 subagent。

**改动**：

1. SKILL 层：任务卡必须小（一次一篇）、子 Agent 必须先写
   `summary_<id>.json` 再返回、主 Agent 按文件存在性回收、失败只重试该篇。
2. 后续 DSH 薄插件层（M4）：
   - `prk` 工具 + 任务状态落盘
   - 子 Agent 超时/重试/结果回收协议
   - 精读子 Agent 使用窄工具 preset

### D. 流程级校验增强（配合 A/B 验证）

- `prk_schema.py` 增加长度、枚举、证据字段检查
- `verify_deliverables.py` 增加 scheme 来源与视觉确认检查
- 新增 5 篇 A/B 验证脚本，输出对比表

---


### E. 调研方向自然语言综述（新增需求）

**目标**：在 DOCX/PPTX 读书报告完成后，追加生成一份“平顺、自然、详细”的
方向综述，覆盖背景、方法范式、主要发现、趋势、局限与未来方向。

**推荐流程**：

1. `make_review_material.py`：从 `summaries/*.json` 生成
   `digests/review_material.md`（每篇只保留综述所需字段的紧凑摘要，
   带论文引用编号；目标 5–10k token）。
2. 主 Agent 只派一个“综述子 Agent”：
   - 输入：`review_material.md` + 空模板
   - 输出：`deliverables/{title}_调研综述.md`
   - 要求：所有结论用 `[编号]` 或 `（[01][03]）` 标注来源；不得编造
     material 中不存在的数字。
3. `make_review_docx.py`：把综述 Markdown 转成 DOCX，并可选择：
   - 独立输出 `{title}_调研综述.docx`
   - 或作为“第 8 章”追加到已有读书报告 DOCX 中
4. `verify_review.py`：校验引用的论文编号在 material 中存在；
   低置信度或未标注来源的段落给出警告。

**章节结构建议**：

- 1. 研究背景与问题定义
- 2. 领域全景与研究方向分类
- 3. 代表性方法与技术路线
- 4. 主要发现与性能趋势
- 5. 研究范式演进
- 6. 现有局限与挑战
- 7. 未来方向与开放问题
- 8. 对本领域/本人研究的启示
- 9. 参考文献映射

**精度与 token 控制**：

- 综述子 Agent 不读全文，只读 `review_material.md`，必要时按引用号
  grep 对应 summary。
- 素材包由脚本从 summaries 生成，字段可追溯；Agent 只负责组织语言，
  不负责发明事实。
- 可选两档：
  - 快速版：脚本生成结构化骨架 + Agent 润色
  - 详细版：Agent 直接基于素材包写完整自然语言综述

## 建议实施顺序

1. **第一批：Scheme 提取 v2**（独立、当前最痛）
2. **第二批：Token 无损项**
   - save_summary.py、make_brief.py、日志瘦身、图片 view 副本
3. **第三批：digest 重构 + read_depth + 证据规则**
4. **第四批：5 篇 A/B 验证，按结果决定 `full` 比例**
5. **第五批：SKILL 瘦身与子 Agent 交接硬化**
