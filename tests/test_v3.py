# -*- coding: utf-8 -*-
"""v3 新增功能的本地回归测试（CLI 级）。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = REPO / "skills" / "paper-review-kit" / "scripts"


def write_meta(root):
    meta = {"project": "test", "title": "测试", "papers": [
        {"id": "01", "title": "T1", "journal": "J", "year": 2024, "kind": "x", "kind_zh": "x"},
        {"id": "02", "title": "T2", "journal": "J", "year": 2024, "kind": "x", "kind_zh": "x"},
    ]}
    (Path(root) / "papers_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def run_script(root, name, args=None, stdin=None):
    cmd = [sys.executable, str(SKILL_SCRIPTS / name)] + (args or [])
    return subprocess.run(cmd, cwd=str(root), input=stdin, capture_output=True, text=True)


class TestSaveSummary(unittest.TestCase):
    def test_requires_evidence_for_pdf_read(self):
        from prk_schema import validate_summary
        data = {"pdf_status": "pdf_read", "method_zh": "m", "results_zh": "r"}
        errors, _ = validate_summary(data)
        self.assertTrue(any("evidence" in e for e in errors))

    def test_save_summary_writes(self):
        with tempfile.TemporaryDirectory() as td:
            write_meta(td)
            s = {"title_en": "x", "title_zh": "x", "journal": "J", "year": 2024,
                 "kind": "x", "kind_zh": "x", "pdf_status": "pdf_read",
                 "method_zh": "m", "results_zh": "r",
                 "evidence_pages": ["p1"], "figure_refs": ["Fig1"]}
            res = run_script(td, "save_summary.py", ["--id", "01"], stdin=json.dumps(s))
            self.assertIn("saved", res.stdout, res.stderr)
            self.assertTrue((Path(td) / "summaries" / "summary_01.json").exists())


class TestBrief(unittest.TestCase):
    def test_brief_generated(self):
        with tempfile.TemporaryDirectory() as td:
            write_meta(td)
            d = {"id": "01", "title_zh": "测试", "kind_zh": "方向", "pdf_status": "pdf_read",
                 "method_zh": "方法甲", "results_zh": "结果90%",
                 "metrics_zh": [{"label": "A", "value": "90"}], "innovation_zh": "创新"}
            (Path(td) / "summaries").mkdir()
            (Path(td) / "summaries" / "summary_01.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            res = run_script(td, "make_brief.py")
            self.assertEqual(res.returncode, 0, res.stderr)
            brief = Path(td) / "digests" / "brief.txt"
            self.assertTrue(brief.exists())
            self.assertIn("01", brief.read_text(encoding="utf-8"))


class TestVerifyReview(unittest.TestCase):
    def test_bad_citation(self):
        with tempfile.TemporaryDirectory() as td:
            write_meta(td)
            (Path(td) / "digests").mkdir()
            (Path(td) / "deliverables").mkdir()
            (Path(td) / "digests" / "review_material.md").write_text("## [01]\ncontent\n", encoding="utf-8")
            (Path(td) / "deliverables" / "bad.md").write_text("## [99] not exist\n", encoding="utf-8")
            res = run_script(td, "verify_review.py", ["--review", str(Path(td) / "deliverables" / "bad.md")])
            self.assertIn("FAIL", res.stdout, res.stderr)
            self.assertTrue((Path(td) / "review_check.json").exists())


if __name__ == "__main__":
    unittest.main()
