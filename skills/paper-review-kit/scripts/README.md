# paper-review-kit 脚本说明

| 脚本 | 作用 | 何时运行 |
|---|---|---|
| `retheme.py` | 把默认“微流控”主题换成新主题（改 make_docx/make_pptx/verify_deliverables 里的主题词） | 建项目后、生成报告前 |
| `verify_meta.py` | OpenAlex/Crossref/Europe PMC 核验 DOI、期刊、年份、OA 状态与 OA PDF 链接 → `papers_meta_verified.json` | 必跑 |
| `init_summaries.py` | 按 `papers_meta.json` 初始化 `summaries/summary_XX.json` 模板 | 必跑 |
| `download_papers_fast.py` | 并发(6线程)下载：Europe PMC render → PMC → 出版商 → OpenAlex OA → EPMC 全文 →（授权后）Sci-Hub 回退；输出 `papers/results.json` | 必跑 |
| `retry_downloads.py` | 只重试 `results.json` 中的失败论文；支持手动核验 URL（含 Referer） | 有失败论文时 |
| `download_targeted.py` | 定向补下载个别论文（如大文件、仓库直链） | 个别失败时 |
| `fetch_xml.py` | 出版方拦截 PDF 时，用 Europe PMC fullTextXML 生成 `papers_txt/` 与 `digests/` | 02 类场景 |
| `extract_text.py` | PyMuPDF 逐页提取 `papers/*.pdf` → `papers_txt/*.txt`（`===PAGE n===` 标记） | 必跑 |
| `extract_figs.py` | “Fig.1 题注裁剪 / 关键词页”启发式提取 Scheme → `papers_figs/*.png` | 必跑 |
| `digest_papers.py` | 为每篇生成“首页+关键段落”精读缓冲 `digests/<id>.md` | 精读前 |
| `condense_digests.py` | 汇总所有 digest → `digests/keyfacts.txt`（每篇约3–6KB，主上下文只读这个） | 精读前 |
| `augment_summaries.py` | 从 Europe PMC/Crossref 回填英文摘要与题录到 summaries | 精读前 |
| `make_docx.py` | 依据 summaries 生成读书报告 DOCX（十大维度+横向对比+范式总结） | 精读后 |
| `make_pptx.py` | 依据 summaries 生成 16:9 PPT（封面/目录/背景/全景 + 每篇2页 + 对比/趋势/结论/文献） | 精读后 |
| `verify_deliverables.py` | 自检：PDF 魔数/页数、摘要字段、DOCX/PPTX 可打开、图片数 → `check_report.json` | 交付前 |
| `check_layout.py` | python-pptx 近似估算文本溢出 → `layout_report.json` | 交付前 |
| `run_pipeline.sh` | 一键跑前半程（verify→init→download→extract→figs→digest→condense→augment） | 建项目后 |

## 依赖
`python3` + `requests` + `pymupdf` + `python-docx` + `python-pptx`（可选 `Pillow`）。
Windows：`bash`（Git Bash）运行 `run_pipeline.sh`；PowerShell COM 可用时导出 PPT 预览 PNG。

## 典型失败处理
- 403/出版商拦截 → 优先 Europe PMC render（`https://europepmc.org/articles/<PMCID>?pdf=render`）；
  再试 `retry_downloads.py` 手动仓库链接；最后记录 `pdf_status=abstract_only`。
- DOI 解析失败 → 用 OpenAlex 标题搜索补 DOI（见 `verify_meta.py` 的 openalex_title_lookup）。
- PPT 无 Scheme 图 → 自动显示占位框，报告中说明“未获取全文/未提取图”。
