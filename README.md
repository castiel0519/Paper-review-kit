# Paper Review Kit

> 一套把「SCI 论文检索 → 元数据核验 → PDF 下载 → 全文/图表提取 → 结构化精读 →
> DOCX 读书报告 + 每篇两页 PPT」全流程标准化、可复用的**脚本包 + 会话技能（Skill）**。

本仓库只保留「工具本身」：自动化脚本与可复用的 `paper-review-kit` 技能。
运行管线后生成的 `papers/`、`summaries/`、`digests/`、`deliverables/` 等
属于**运行时产物**，默认不提交（见 `.gitignore`）。

当前主线（v0.2.0 / M1）：**去专案化 + project.yml 配置驱动**。报告标题、年份范围、
研究方向、第三方下载开关与叙事文案都在项目配置里，不再把“微流控”等具体主题写死在源码里。

---

## 仓库结构

```
Paper-review-kit/
├── README.md
├── LICENSE
├── .gitignore
├── scripts/                         # 兼容 wrapper（实现已收敛到 skill 内）
├── examples/
│   └── microfluidics/               # 旧微流控专案样例归档（可参考，不再作为默认模板）
└── skills/paper-review-kit/         # 单一事实源
    ├── SKILL.md                     # DSH/Agent 工作流
    ├── scripts/                     # 全部管线脚本（复制到新项目使用）
    └── templates/                   # project.example.yml / papers_meta / summary 模板
```

---

## 核心脚本速览

| 脚本 | 作用 | 阶段 |
|---|---|---|
| `retheme.py` | 把主题写入 `project.yml`（不再改渲染源码） | 0 初始化 |
| `verify_meta.py` | OpenAlex/Crossref/Europe PMC/Unpaywall 核验 DOI、期刊、年份、OA 状态 | ① 核验 |
| `init_summaries.py` | 初始化每篇论文的精读摘要模板（`pdf_status` 默认 `missing`） | ② 建模板 |
| `download_papers_fast.py` | 并发下载：manual_urls → Europe PMC → PMC → 出版商 → OA 链接 | ③ 下载 |
| `retry_downloads.py` / `download_targeted.py` | 失败重试 / 定向补下载（URL 在 papers_meta.json 中配置） | ③ 补下载 |
| `fetch_xml.py` | 对 `xml_pmcid` 非空论文用 Europe PMC fullTextXML 降级 | ③ 降级 |
| `extract_text.py` | PyMuPDF 逐页提取全文 | ④ 提取 |
| `extract_figs.py` | 标题锚点+图块检测，输出候选与 `_fig1_view.png` | ④ 提取 |
| `digest_papers.py` / `condense_digests.py` | 生成结构化 `digests/<id>.md` 与压缩版 keyfacts | ⑤ 精读准备 |
| `make_brief.py` | 从 summaries 生成主 Agent 路由层 `digests/brief.txt` | ⑤ 精读准备 |
| `augment_summaries.py` | 回填英文摘要与题录 | ⑤ 精读准备 |
| `make_docx.py` | 读书报告：十大维度精读 + 横向对比 + 范式总结 | ⑥ 生成 |
| `make_review_material.py` | 生成综述素材包 | ⑧ 综述 |
| `make_review_docx.py` | 综述 Markdown 转 DOCX | ⑧ 综述 |
| `verify_review.py` | 校验综述引用编号 | ⑧ 综述 |
| `make_pptx.py` | 研究报告：封面/目录/背景/全景 + 每篇 2 页 + 对比/趋势/结论/文献 | ⑥ 生成 |
| `verify_deliverables.py` / `check_layout.py` | 完整性自检 / PPT 溢出检查 | ⑦ 交付 |
| `run_pipeline.sh` | 一键跑完 ①–⑤ 前半程 | 0→⑤ |

---

## 快速开始（新主题）

```bash
# 1) 建项目并复制“技能内”脚本（单一事实源）
mkdir my_review && cd my_review
cp -r <本仓库>/skills/paper-review-kit/scripts .

# 2) 初始化配置与论文清单
cp <本仓库>/skills/paper-review-kit/templates/project.example.yml project.yml
cp <本仓库>/skills/paper-review-kit/templates/papers_meta.example.json papers_meta.json
python scripts/retheme.py --topic 癌症早筛 --topic-en "Cancer Screening"

# 3) 编辑 project.yml / papers_meta.json：
#    - project.yml：标题、范围、compliance.allow_third_party（默认 false）、报告文案
#    - papers_meta.json：id/title/title_zh/journal/year/doi/kind...
#    - 补充下载 URL 用 manual_urls / download_overrides；XML 降级用 xml_pmcid

# 4) 一键前半程：核验→建模板→下载→提取→建精读缓冲
bash scripts/run_pipeline.sh

# 5) 子 Agent 逐篇精读并写 summaries/summary_XX.json
#    用 scripts/save_summary.py 落盘；pdf_status 只允许：pdf_read / abstract_only / missing
#    主 Agent 只读 digests/brief.txt（先运行 make_brief.py）

# 6) 生成 brief/报告并自检
python scripts/make_brief.py
python scripts/make_docx.py
python scripts/make_pptx.py
python scripts/verify_deliverables.py
python scripts/check_layout.py

# 7) 可选：生成自然语言调研综述
python scripts/make_review_material.py
# 综述子 Agent 使用 templates/review_template.md 写 deliverables/{title}_调研综述.md
python scripts/verify_review.py
python scripts/make_review_docx.py
```

---

## 技能 `skills/paper-review-kit/`

- **安装**：把 `skills/paper-review-kit/` 放到 DSH 的 skills 目录（如 `~/.dsh/skills/`）；
- **调用**：新会话中说 *“用 paper-review-kit 调研《某主题》”* 即可自动加载；
- **主/子 Agent 协作**：主 Agent 只做分发与汇总；视觉精读交给子 Agent，子 Agent
  必须先写完 `summaries/summary_<id>.json` 再返回，主 Agent 按文件存在性回收和重试；
- **合规**：默认只下载合法可得 OA PDF；第三方渠道仅在 `allow_third_party: true`
  或 `--allow-third-party` 显式授权后尝试，失败原因如实记录。

---

## 依赖与环境

- Python 3.9+（仓库脚本已在 3.12 验证）
- `pip install -r requirements.txt`（包含 `requests/pymupdf/python-docx/python-pptx/pyyaml/Pillow`）
- Windows 下用 Git Bash 运行 `run_pipeline.sh`；PowerShell 亦可逐条执行

---

## 许可证

本项目源码、脚本与技能采用 [MIT License](LICENSE)：允许自由使用、修改、再分发与商业使用，
仅需保留版权与许可声明，使用风险自负。
