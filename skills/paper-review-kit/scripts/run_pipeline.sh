#!/usr/bin/env bash
# run_pipeline.sh — paper-review-kit 一步管线（在项目根目录运行：bash scripts/run_pipeline.sh）
# 第三方下载默认关闭；确需开启：python scripts/download_papers_fast.py --allow-third-party
set -e
if [ -f "./project.yml" ] || [ -f "./papers_meta.json" ]; then
  PROJECT_ROOT="$(pwd)"
else
  PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
cd "$PROJECT_ROOT"

echo "==> [1/8] verify_meta (OpenAlex/Crossref/EuropePMC 核验 + OA 识别)"
python scripts/verify_meta.py

echo "==> [2/8] init_summaries (生成精读摘要模板)"
python scripts/init_summaries.py

echo "==> [3/8] download_papers_fast (合规来源优先；第三方默认关闭)"
python scripts/download_papers_fast.py

echo "==> [4/8] extract_text (PyMuPDF 逐页文本)"
python scripts/extract_text.py

echo "==> [5/8] extract_figs (Scheme 图启发式提取)"
python scripts/extract_figs.py

echo "==> [6/8] digest_papers (每篇生成精读缓冲)"
python scripts/digest_papers.py

echo "==> [7/8] condense_digests (汇总 keyfacts.txt 供定向精读)"
python scripts/condense_digests.py

echo "==> [8/8] augment_summaries (回填英文摘要/题录)"
python scripts/augment_summaries.py

echo
echo "DONE(前半程)。接下来："
echo "  1) 按 digests/<id>.md 精读，用 save_summary.py 写 summaries/summary_XX.json"
echo "     （pdf_status 只能填 pdf_read / abstract_only / missing）；"
echo "  2) python scripts/make_brief.py 生成主 Agent 路由 brief；"
echo "  3) python scripts/make_pptx.py 生成研究报告（每篇2页）；"
echo "  4) python scripts/verify_deliverables.py 自检；"
echo "  5) python scripts/check_layout.py 检查PPT布局。"
