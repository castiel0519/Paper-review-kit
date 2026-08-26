# Paper Review Kit

> 一套把「SCI 论文检索 → 元数据核验 → PDF 下载 → 全文/图表提取 → 结构化精读 → DOCX 读书报告 +
> 每篇两页 PPT」全流程标准化、可复用的脚本包与可调用技能（Skill）。

本仓库**不是某一个具体调研任务的成果陈列**，而是一个通用工具包：
- `scripts/`：可直接复制到任意新项目中使用的完整管线脚本；
- `skills/paper-review-kit/`：可安装到 DSH 会话中的可复用技能（含 SKILL.md、脚本、模板）；
- 仓库内现有的 `papers_meta.json`、`summaries/`、`deliverables/` 等，只是「ML/AI × 微流控」主题的
  **示例产物**，用于展示工作流效果与作为新项目的模板参考。

---

## 仓库结构

```
Paper-review-kit/
├── README.md                     # 本文件
├── LICENSE                       # MIT 许可证
├── .gitignore                    # 忽略 PDF/日志/缓存等
├── scripts/                      # 项目级管线脚本（当前示例项目使用）
├── skills/paper-review-kit/      # 可复用技能包
│   ├── SKILL.md                  # 技能使用说明（会话中调用）
│   ├── scripts/                  # 与 scripts/ 同源的通用脚本 + retheme/run_pipeline
│   └── templates/                # papers_meta/summary 等模板样例
├── papers_meta.json              # 示例：候选论文元数据（DOI/期刊/年份/分类）
├── papers_meta_verified.json     # 示例：核验后的元数据（含 OA 状态）
├── summaries/                    # 示例：21 篇论文结构化精读摘要
├── digests/                      # 示例：每篇精读缓冲 + keyfacts.txt
├── papers_figs/                  # 示例：论文 Scheme 图
├── papers_txt/                   # 示例：PDF 逐页提取文本
├── deliverables/                 # 示例：最终 DOCX/PPTX 与预览图
└── papers/                       # 下载记录 results.json（PDF 不入库）
```

---

## 核心脚本速览

| 脚本 | 作用 | 流程阶段 |
|---|---|---|
| `verify_meta.py` | OpenAlex/Crossref/Europe PMC 核验 DOI、期刊、年份、OA 状态与 OA PDF | ① 检索核验 |
| `init_summaries.py` | 按元数据初始化每篇论文的精读摘要模板 | ② 建模板 |
| `download_papers_fast.py` | 6 线程并发下载（Europe PMC render → PMC → 出版商 → OA 链接），失败可重试 | ③ 下载 |
| `retry_downloads.py` | 只重试失败论文，支持手动指定仓库直链（含 Referer） | ③ 补下载 |
| `download_targeted.py` | 个别论文定向补下载 | ③ 补下载 |
| `fetch_xml.py` | 出版方拦截 PDF 时，用 Europe PMC 全文 XML 替代 | ③ 降级 |
| `extract_text.py` | PyMuPDF 逐页提取全文 → `papers_txt/*.txt` | ④ 提取 |
| `extract_figs.py` | 启发式提取论文 Scheme/框架图（Fig.1 题注裁剪或整页回退） | ④ 提取 |
| `digest_papers.py` | 生成本篇「首页+关键段落」精读缓冲 | ⑤ 精读准备 |
| `condense_digests.py` | 汇总成 `digests/keyfacts.txt`（每篇 3–6KB，主上下文只读这个） | ⑤ 精读准备 |
| `augment_summaries.py` | 回填英文摘要与权威题录，减少人工输入 | ⑤ 精读准备 |
| `make_docx.py` | 读书报告：十大维度精读 + 横向对比 + 范式总结 | ⑥ 生成 |
| `make_pptx.py` | 研究报告：封面/目录/背景/全景 + 每篇 2 页 + 对比/趋势/结论/参考文献 | ⑥ 生成 |
| `verify_deliverables.py` | PDF/摘要/DOCX/PPTX 完整性自检 | ⑦ 交付 |
| `check_layout.py` | PPT 文本溢出风险检查 | ⑦ 交付 |
| `retheme.py` | 一键把默认「微流控」主题替换为新主题 | 0 初始化 |
| `run_pipeline.sh` | 一键跑完 ①–⑤ 前半程 | 0→⑤ |

---

## 技能包 `skills/paper-review-kit`

### 它是什么
一个 DSH 会话技能：把上述管线拆成「脚本负责数据处理、结构化 JSON 负责精读结果、
脚本负责渲染报告」的分工。主会话永远不用读论文全文。

### 如何使用
1. **安装**：把 `skills/paper-review-kit/` 放到 `~/.dsh/skills/paper-review-kit/`
   （仓库内已自带一份，也可以直接复制使用）。
2. **调用**：在新会话里说 *“用 paper-review-kit 调研《某主题》”*，技能会自动加载；
   也可以直接按其 `SKILL.md` 手动执行。
3. **新主题接入**：
   ```bash
   python scripts/retheme.py --topic 癌症早筛 --topic-en "Cancer Screening"
   ```
   将脚本里的默认主题词一键换成新主题。
4. **精读 JSON schema**（与 `paper-watch` 宿主工具一致）：
   `id/title_en/title_zh/journal/year/doi/pmid/pmcid/kind/kind_zh/pdf_status/abstract_en/
   abstract_zh/background_zh/problem_zh/data_zh/task_zh/method_zh/results_zh/metrics_zh/
   innovation_zh/limitation_zh/paradigm_tags/paradigm_zh/framework_zh/framework_steps/
   scheme_zh/lessons_zh/evidence_pages/figure_refs`。
5. **PPT 约定**：每篇论文恰好 2 页——第 1 页「内容讲解 + 论文 Scheme 图」，
   第 2 页「研究范式 + 研究框架解析（数据流→模型→训练→评估）」；
   结尾附横向对比、范式总结与趋势、结论、参考文献。

---

## 快速开始（新主题）

```bash
# 1) 建项目并复制脚本
mkdir my_review && cd my_review
cp -r <本仓库>/skills/paper-review-kit/scripts .

# 2) 换成你的主题（默认是“微流控”）
python scripts/retheme.py --topic 癌症早筛 --topic-en "Cancer Screening"

# 3) 编辑论文清单（模板见 skills/paper-review-kit/templates/papers_meta.example.json）
#    编辑 papers_meta.json：填 id/title/title_zh/journal/year/doi/kind...

# 4) 一键前半程：核验→建模板→下载→提取→建精读缓冲
bash scripts/run_pipeline.sh

# 5) 读 digests/keyfacts.txt，按 schema 填写 summaries/summary_XX.json

# 6) 生成报告并自检
python scripts/make_docx.py
python scripts/make_pptx.py
python scripts/verify_deliverables.py
python scripts/check_layout.py
```

---

## 依赖与运行环境

- Python 3.9+，建议 3.13（本仓库脚本已在 3.13 验证）
- `pip install requests pymupdf python-docx python-pptx`（可选 `Pillow`；导出 PNG 预览可用 PowerPoint COM）
- Windows 下用 Git Bash 运行 `run_pipeline.sh`；PowerShell 亦可逐条执行

---

## 数据与合规

- **论文 PDF 不入库**：`.gitignore` 已排除 `papers/*.pdf`。复现下载：
  ```bash
  python scripts/verify_meta.py           # 生成 papers_meta_verified.json
  python scripts/download_papers_fast.py  # OA 优先并发下载 → papers/
  ```
- 默认只下载**合法可得**的开放获取（OA）PDF；
  第三方渠道仅在用户显式授权后尝试，且失败原因（DNS/证书/403）会如实记录。
- 论文全文版权归原出版商与作者所有；本仓库只包含脚本、结构化摘要与报告。

---

## 许可证

本项目源码、脚本与技能采用 [MIT License](LICENSE)：允许自由使用、修改、再分发与商业使用，
仅需保留版权与许可声明，使用风险自负。
