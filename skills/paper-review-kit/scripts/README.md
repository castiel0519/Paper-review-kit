# paper-review-kit 脚本说明

所有脚本都从**当前项目根目录**读取 `project.yml`（或 `papers_meta.json`），
也可用 `--project <目录>` 显式指定。报告标题、年份范围、第三方下载开关等
统一由 `project.yml` 控制，不再修改脚本源码。

| 脚本 | 作用 | 何时运行 |
|---|---|---|
| `retheme.py` | 把主题写入 `project.yml`（不再改 make_docx/make_pptx 源码） | 建项目后 |
| `verify_meta.py` | OpenAlex/Crossref/Europe PMC/Unpaywall 核验 DOI、期刊、年份、OA 状态与 OA PDF 链接 → `papers_meta_verified.json` | 必跑 |
| `init_summaries.py` | 按 `papers_meta.json` 初始化 `summaries/summary_XX.json` 模板（含 `pdf_status: missing`） | 必跑 |
| `download_papers_fast.py` | 并发下载：manual_urls → Europe PMC render → PMC → 出版商 → OpenAlex OA → EPMC 全文；第三方渠道默认关闭 | 必跑 |
| `retry_downloads.py` | 只重试 `results.json` 中的失败论文；补充 URL 来自 `papers_meta.json` 的 manual_urls/download_overrides | 有失败论文时 |
| `download_targeted.py` | 用 papers_meta 中指定论文的 manual_urls/download_overrides 定向补下载 | 个别失败时 |
| `fetch_xml.py` | 对 `xml_pmcid` 非空的论文，用 Europe PMC fullTextXML 生成 `papers_txt/` 与 `digests/` | PDF 被出版方拦截时 |
| `extract_text.py` | PyMuPDF 逐页提取 `papers/*.pdf` → `papers_txt/*.txt`（`===PAGE n===` 标记） | 必跑 |
| `extract_figs.py` | “Fig.1 题注裁剪 / 关键词页”启发式提取 Scheme → `papers_figs/*.png` | 必跑 |
| `digest_papers.py` | 为每篇生成“首页+关键段落”精读缓冲 `digests/<id>.md` | 精读前 |
| `condense_digests.py` | 汇总所有 digest → `digests/keyfacts.txt`（主上下文只读这个） | 精读前 |
| `augment_summaries.py` | 从 Europe PMC/Crossref 回填英文摘要与题录到 summaries | 精读前 |
| `make_docx.py` | 依据 summaries 生成读书报告 DOCX（标题/文案由 project.yml 驱动） | 精读后 |
| `make_pptx.py` | 依据 summaries 生成 16:9 PPT（封面/目录/背景/全景 + 每篇2页 + 对比/趋势/结论/文献） | 精读后 |
| `verify_deliverables.py` | 自检：PDF 魔数/页数、摘要必填字段与 `pdf_status` 枚举、DOCX/PPTX 可打开、每篇2页结构 | 交付前 |
| `check_layout.py` | python-pptx 近似估算文本溢出 → `layout_report.json` | 交付前 |
| `save_summary.py` | 子 Agent 用 stdin 落盘 summary JSON，只打印一行日志 | 精读时 |
| `make_brief.py` | 从 summaries 生成主 Agent 路由层 brief.txt | 生成报告前 |
| `make_review_material.py` | 从 summaries 生成综述素材包 | 可选综述 |
| `make_review_docx.py` | 综述 MD 转 DOCX / 追加读书报告 | 可选综述 |
| `verify_review.py` | 校验综述引用编号 | 可选综述 |
| `ab_compare.py` | 两套 summaries A/B 对比 | 验证 |
| `run_pipeline.sh` | 一键跑前半程（verify→init→download→extract→figs→digest→condense→augment） | 建项目后 |

## 配置速览（project.yml）

```yaml
project:
  title: 论文精读调研报告
  topic: 论文调研
  topic_en: Paper Review
  range: 2020-2026
compliance:
  allow_third_party: false   # Sci-Hub 等第三方渠道默认关闭
report:
  kinds:
    modeling: { en: Modeling, group: 基础模型, color: BLUE }
  narrative:
    trends: ["……"]
```

## 依赖
`python3` + `requests` + `pymupdf` + `python-docx` + `python-pptx` + `pyyaml`
（可选 `Pillow`）。Windows：Git Bash 运行 `run_pipeline.sh`；PowerShell COM 可导出 PPT 预览 PNG。

## 典型失败处理
- 403/出版商拦截 → 优先 Europe PMC render（`https://europepmc.org/articles/<PMCID>?pdf=render`）；
  再在 `papers_meta.json` 对应论文加 `manual_urls` 后跑 `retry_downloads.py`；
  最后在 summary 中标记 `pdf_status: abstract_only`。
- DOI 解析失败 → 用 OpenAlex 标题搜索补 DOI（见 `verify_meta.py`）。
- PPT 无 Scheme 图 → 自动显示占位框，报告中说明“未获取全文/未提取图”。
