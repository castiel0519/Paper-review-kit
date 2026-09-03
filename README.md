# Paper Review Kit

> 一套把「SCI 论文调研 → 元数据核验 → 合规下载 → 全文/图表提取 → 结构化精读 →
> DOCX 读书报告 + 每篇两页 PPT + 自然语言综述」全流程标准化、可复用的 **脚本包 + DSH 技能（Skill）**。

---

## 这套工具解决什么问题

调研一个学术方向时，通常要：

1. 选一批论文、核验元数据；
2. 尽量合法下载 PDF；
3. 提取全文和 Scheme 图；
4. 逐篇精读并结构化记录；
5. 生成读书报告 / PPT / 综述。

这个仓库把这些步骤固化成脚本和 DSH Skill，同时尽量控制 token 消耗。

---

## 核心特点

- **配置驱动**：主题、标题、范围、报告文案、下载策略都由 `project.yml` 控制，不修改源码。
- **合规下载**：默认只走 OA / PMC / 出版商等合法来源；Sci-Hub 等第三方默认关闭。
- **Token 分层**：主 Agent 只读 `brief.txt`，子 Agent 读结构化 digest，全文只按需 grep。
- **Scheme 提取 v2**：基于标题锚点 + 位图/矢量图检测裁剪，不再把整页文字当图。
- **主/子 Agent 协作**：主 Agent 只做分发和汇总，视觉精读交给子 Agent，要求先落盘再返回。
- **自然语言综述**：读书报告完成后，可基于素材包生成带引用编号的详细综述。

---

## 仓库结构

```
Paper-review-kit/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── scripts/                         # 兼容 wrapper（实现已收敛到 skill 内）
├── docs/
│   └── NEXT_PLAN.md                 # 后续改动清单/方案
├── examples/
│   └── microfluidics/               # 旧微流控专案完整样例归档
├── tests/                           # 本地回归测试
└── skills/paper-review-kit/         # 单一事实源，DSH 技能主体
    ├── SKILL.md                     # DSH/Agent 工作流说明
    ├── scripts/                     # 全部管线脚本（复制到新项目使用）
    └── templates/                   # project/papers_meta/summary/review 模板
```

> 新项目请复制 `skills/paper-review-kit/scripts/`，不要复制根目录 `scripts/`。

---

## 快速开始

### 1. 创建项目并复制脚本

```bash
mkdir my_review && cd my_review
cp -r <本仓库>/skills/paper-review-kit/scripts .
```

### 2. 初始化配置和论文清单

```bash
cp <本仓库>/skills/paper-review-kit/templates/project.example.yml project.yml
cp <本仓库>/skills/paper-review-kit/templates/papers_meta.example.json papers_meta.json
python scripts/retheme.py --topic 癌症早筛 --topic-en "Cancer Screening"
```

### 3. 编辑配置

**`project.yml`** 控制：

```yaml
project:
  title: 论文精读调研报告
  topic: 论文调研
  range: 2020-2026
compliance:
  allow_third_party: false   # 第三方渠道默认关闭
download:
  workers: 6
  max_mb: 60
report:
  kinds: { ... }
  narrative: { ... }
```

**`papers_meta.json`** 每篇论文可配置：

```json
{
  "id": "01",
  "title": "...",
  "title_zh": "...",
  "journal": "...",
  "year": 2024,
  "doi": "10.xxxx/xxx",
  "kind": "modeling",
  "kind_zh": "基础模型",
  "read_depth": "targeted",
  "manual_urls": ["https://.../paper.pdf"],
  "download_overrides": [
    { "url": "https://.../paper.pdf", "referer": null }
  ],
  "xml_pmcid": "PMC123456",
  "figure_overrides": {
    "page": 3,
    "bbox": [100, 200, 500, 600]
  }
}
```

### 4. 跑前半程

```bash
bash scripts/run_pipeline.sh
```

自动执行：核验 → 初始化摘要模板 → 下载 → 提取全文 → 提取 Scheme → 生成 digest → 压缩 keyfacts。

### 5. 精读

- 主 Agent **只读** `digests/brief.txt`（由 `make_brief.py` 生成）。
- 子 Agent 一次只精读一篇：
  - 输入：`digests/<id>.md`、可选 `papers_txt/<id>.txt`（只 grep）、`papers_figs/<id>_fig1_view.png`
  - 输出：`summaries/summary_<id>.json`

推荐用 `save_summary.py` 落盘，避免 write/edit 工具回显全文：

```bash
python scripts/save_summary.py --id 01 <<'JSON'
{ "...": "..." }
JSON
```

`pdf_status` 只能填：

```text
pdf_read       已读全文
abstract_only  只有摘要
missing        未获取
```

`pdf_read` 必须同时写：

```json
"evidence_pages": ["p2", "p5"],
"figure_refs": ["Figure 1"]
```

### 6. 生成报告

```bash
python scripts/make_brief.py
python scripts/make_docx.py
python scripts/make_pptx.py
python scripts/verify_deliverables.py
python scripts/check_layout.py
```

### 7. 可选：生成自然语言综述

```bash
# 1. 生成综述素材包
python scripts/make_review_material.py

# 2. 让综述子 Agent 按 templates/review_template.md 写 Markdown
#    写到 deliverables/{title}_调研综述.md

# 3. 校验引用编号并转 DOCX
python scripts/verify_review.py
python scripts/make_review_docx.py
```

---

## Token 分层设计

| 层 | 文件 | 谁读 | 用途 |
|---|---|---|---|
| L0 路由层 | `digests/brief.txt` | 主 Agent | 每篇 ≤320 字符，任务分发和回收 |
| L1 精读层 | `digests/<id>.md` | 子 Agent | 结构化 digest，每篇 ≤2.6KB |
| L2 全文层 | `papers_txt/<id>.txt` | 子 Agent 按需 grep | 证据定位 |
| L3 视觉层 | `papers_figs/<id>_fig1_view.png` | 视觉子 Agent | ≤1024px 压缩图，报告仍用原图 |

---

## Scheme 提取说明

新版 `extract_figs.py` 不再把 Fig.1 标题上方的整页区域当图。

流程：

1. 找到 `Fig. 1` / `Scheme 1` 标题块作为锚点；
2. 收集页面上的位图和矢量图块；
3. 过滤小装饰/背景，合并多面板；
4. 按“贴合标题、水平对齐、面积、正文重叠”评分；
5. 只裁剪图块 bbox，输出：
   - `{id}_fig1.png`：报告用原图
   - `{id}_fig1_view.png`：Agent 视觉确认用
   - `{id}_altN.png`：备用候选
   - `figs_info.json`：候选/bbox/score/confidence

如果自动裁剪不正确，可以在 `papers_meta.json` 中写 `figure_overrides`，或由视觉子 Agent 选择候选并写入 `summary.scheme_image`。

---

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `retheme.py` | 写入 project.yml 主题 |
| `verify_meta.py` | 核验 DOI/期刊/OA/PDF 链接 |
| `init_summaries.py` | 初始化摘要模板 |
| `download_papers_fast.py` | 并发合规下载 |
| `retry_downloads.py` | 失败重试 |
| `download_targeted.py` | 定向补下载 |
| `fetch_xml.py` | Europe PMC XML 降级 |
| `extract_text.py` | PDF 逐页文本提取 |
| `extract_figs.py` | Scheme 图块检测/裁剪 |
| `digest_papers.py` | 结构化 digest |
| `condense_digests.py` | 压缩 keyfacts |
| `make_brief.py` | 主 Agent 路由 brief |
| `augment_summaries.py` | 回填英文摘要/题录 |
| `save_summary.py` | 子 Agent 落盘 summary |
| `make_docx.py` | 生成读书报告 DOCX |
| `make_pptx.py` | 生成每篇 2 页 PPT |
| `verify_deliverables.py` | 交付物自检 |
| `check_layout.py` | PPT 布局溢出检查 |
| `make_review_material.py` | 生成综述素材包 |
| `make_review_docx.py` | 综述 MD 转 DOCX |
| `verify_review.py` | 校验综述引用 |
| `ab_compare.py` | 两套 summaries A/B 对比 |
| `run_pipeline.sh` | 一键前半程 |

---

## 测试

```bash
python -m unittest discover -s tests -q
```

当前包含 M1 与 v3 功能回归测试。

---

## 依赖

```bash
pip install -r requirements.txt
```

需要 Python 3.9+，Windows 推荐 Git Bash 运行 `run_pipeline.sh`。

---

## 许可证

MIT License，详见 [LICENSE](LICENSE)。

## 链接

- 仓库：https://github.com/castiel0519/Paper-review-kit
- 方案：`docs/NEXT_PLAN.md`
