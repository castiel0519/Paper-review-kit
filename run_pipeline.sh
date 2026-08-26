#!/usr/bin/env bash
# run_pipeline.sh — 一条命令初始化脚本模板、核验元数据、下载PDF、提取文本/图、初始化摘要模板。
# 精读摘要后，再运行 make_docx.py / make_pptx.py / verify_deliverables.py。
set -e
cd "$(dirname "$0")/.."

echo "==> [1/6] prepare_scripts"
python scripts/prepare_scripts.py

echo "==> [2/6] verify_meta"
python scripts/verify_meta.py

echo "==> [3/6] download_papers"
python scripts/download_papers.py

echo "==> [4/6] extract_text"
python scripts/extract_text.py

echo "==> [5/6] extract_figs"
python scripts/extract_figs.py

echo "==> [6/6] init_summaries"
python scripts/init_summaries.py

echo "DONE. Now read papers_txt/*.txt and fill summaries/summary_*.json, then run:"
echo "  python scripts/make_docx.py && python scripts/make_pptx.py && python scripts/verify_deliverables.py"
