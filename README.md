# Paper Review Kit

> 一套把「SCI 论文检索 → 元数据核验 → PDF 下载 → 全文/图表提取 → 结构化精读 →
> DOCX 读书报告 + 每篇两页 PPT」全流程标准化、可复用的**脚本包 + 会话技能（Skill）**。

本仓库只保留「工具本身」：自动化脚本与可复用的 `paper-review-kit` 技能。
运行管线后生成的 `papers/`、`summaries/`、`digests/`、`deliverables/` 等
属于**运行时产物**，默认不提交（见 `.gitignore`），模板样例见 `skills/paper-review-kit/templates/`。

---

## 仓库结构

```
Paper-review-kit/
├── README.md                        # 本文件
├── LICENSE                          # MIT 许可证
├── .gitignore                       # 忽略运行时产物/PDF/日志/缓存
├── scripts/                         # 可复制到任意新项目的管线脚本（与技能内脚本同源）
│   ├── verify_meta.py               # 元数据核验 + OA 识别
│   ├── download_papers_fast.py      # 并发下载（OA 优先）
│   ├── extract_text.py / extract_figs.py / digest_papers.py / condense_digests.py
│   ├── make_docx.py / make_pptx.py / verify_deliverables.py / check_layout.py
│   ├── retheme.py                   # 主题一键替换
│   ├── run_pipeline.sh              # 一键前半程
│   └── README.md                    # 脚本角色速览
└── skills/paper-review-kit/         # 可复用技能
    ├── SKILL.md                     # 技能使用说明
    ├── scripts/                     # 与根 scripts/ 同源的脚本
    └── templates/                   # papers_meta.example.json / summary.example.json
```

---

## 核心脚本速览

| 脚本 | 作用 | 阶段 |
|---|---|---|
| `verify_meta.py` | OpenAlex/Crossref/Europe PMC 核验 DOI、期刊、年份、OA 状态 | ① 核验 |
| `init_summaries.py` | 初始化每篇论文的精读摘要模板 | ② 建模板 |
| `download_papers_fast.py` | 6 线程并发下载（Europe PMC render → PMC → 出版商 → OA 链接） | ③ 下载 |
| `retry_downloads.py` / `download_targeted.py` | 失败重试 / 定向补下载（支持手动仓库直链） | ③ 补下载 |
| `fetch_xml.py` | 出版方拦截 PDF 时，用 Europe PMC 全文 XML 替代 | ③ 降级 |
| `extract_text.py` | PyMuPDF 逐页提取全文 | ④ 提取 |
| `extract_figs.py` | 启发式提取论文 Scheme/框架图 | ④ 提取 |
| `digest_papers.py` / `condense_digests.py` | 生成 `digests/keyfacts.txt` 精读缓冲（主上下文只读这个） | ⑤ 精读准备 |
| `augment_summaries.py` | 回填英文摘要与题录 | ⑤ 精读准备 |
| `make_docx.py` | 读书报告：十大维度精读 + 横向对比 + 范式总结 | ⑥ 生成 |
| `make_pptx.py` | 研究报告：封面/目录/背景/全景 + 每篇 2 页 + 对比/趋势/结论/文献 | ⑥ 生成 |
| `verify_deliverables.py` / `check_layout.py` | 完整性自检 / PPT 溢出检查 | ⑦ 交付 |
| `retheme.py` | 把默认主题词一键替换为新主题 | 0 初始化 |
| `run_pipeline.sh` | 一键跑完 ①–⑤ 前半程 | 0→⑤ |

---

## 快速开始（新主题）

```bash
# 1) 建项目并复制脚本
mkdir my_review && cd my_review
cp -r <本仓库>/skills/paper-review-kit/scripts .

# 2) 换成你的主题（默认是“微流控”）
python scripts/retheme.py --topic 癌症早筛 --topic-en "Cancer Screening"

# 3) 编辑论文清单（模板见 skills/paper-review-kit/templates/papers_meta.example.json）
#    填 id/title/title_zh/journal/year/doi/kind...

# 4) 一键前半程：核验→建模板→下载→提取→建精读缓冲
bash scripts/run_pipeline.sh

# 5) 读 digests/keyfacts.txt，按 schema 填写 summaries/summary_XX.json
#    （字段参考 templates/summary.example.json）

# 6) 生成报告并自检
python scripts/make_docx.py
python scripts/make_pptx.py
python scripts/verify_deliverables.py
python scripts/check_layout.py
```

---

## 技能 `skills/paper-review-kit/`

- **安装**：把 `skills/paper-review-kit/` 放到 `~/.dsh/skills/paper-review-kit/`；
- **调用**：新会话中说 *“用 paper-review-kit 调研《某主题》”* 即可自动加载；
- **精读 schema**（与 `paper-watch` 宿主工具一致）：
  `id/title_en/title_zh/journal/year/doi/pmid/pmcid/kind/kind_zh/pdf_status/abstract_en/
  abstract_zh/background_zh/problem_zh/data_zh/task_zh/method_zh/results_zh/metrics_zh/
  innovation_zh/limitation_zh/paradigm_tags/paradigm_zh/framework_zh/framework_steps/
  scheme_zh/lessons_zh/evidence_pages/figure_refs`；
- **PPT 约定**：每篇论文恰好 2 页——第 1 页「内容讲解 + 论文 Scheme」，
  第 2 页「研究范式 + 研究框架解析（数据流→模型→训练→评估）」；结尾附对比/趋势/结论/文献；
- **合规**：默认只下载合法可得 OA PDF；第三方渠道仅在用户显式授权后尝试，失败原因如实记录。

---

## 依赖与环境

- Python 3.9+（仓库脚本已在 3.13 验证）
- `pip install requests pymupdf python-docx python-pptx`（可选 `Pillow`）
- Windows 下用 Git Bash 运行 `run_pipeline.sh`；PowerShell 亦可逐条执行

---

## 许可证

本项目源码、脚本与技能采用 [MIT License](LICENSE)：允许自由使用、修改、再分发与商业使用，
仅需保留版权与许可声明，使用风险自负。
