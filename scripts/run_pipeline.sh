#!/usr/bin/env bash
# run_pipeline.sh — paper-review-kit 一步管线（在项目根目录运行：bash scripts/run_pipeline.sh）
set -e
cd "$(dirname "$0")/.."

echo "==> [1/8] verify_meta (OpenAlex/Crossref/EuropePMC 核验 + OA 识别)"
python -u scripts/verify_meta.py

echo "==> [2/8] init_summaries (生成精读摘要模板)"
python -u scripts/init_summaries.py

echo "==> [3/8] download_papers_fast (OA 优先，6 并发；失败可跑 retry_downloads.py)"
python -u scripts/download_papers_fast.py

echo "==> [4/8] extract_text (PyMuPDF 逐页文本)"
python -u scripts/extract_text.py

echo "==> [5/8] extract_figs (Scheme 图启发式提取)"
python -u scripts/extract_figs.py

echo "==> [6/8] digest_papers (每篇生成精读缓冲)"
python -u scripts/digest_papers.py

echo "==> [7/8] condense_digests (汇总 keyfacts.txt 供定向精读)"
python -u scripts/condense_digests.py

echo "==> [8/8] augment_summaries (回填英文摘要/题录)"
python -u scripts/augment_summaries.py

echo
echo "DONE(前半程)。接下来："
echo "  1) 读 digests/keyfacts.txt（每篇 3-6KB），按 schema 填写 summaries/summary_XX.json"
echo "     （字段参考 templates/summary.example.json，按 SKILL.md 的 schema 填写）；"
echo "  2) 未下载全文的论文在 summary 的 pdf_status 标注 abstract_only/missing，不得编造；"
echo "  3) python scripts/make_docx.py 生成读书报告；"
echo "  4) python scripts/make_pptx.py 生成研究报告（每篇2页）；"
echo "  5) python scripts/verify_deliverables.py 自检；python scripts/check_layout.py 检查PPT布局。"
