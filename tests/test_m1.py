# -*- coding: utf-8 -*-
"""M1 回归测试：不访问网络，全部本地运行。"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = REPO / "skills" / "paper-review-kit" / "scripts"
ROOT_SCRIPTS = REPO / "scripts"


if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSingleSource(unittest.TestCase):
    def test_root_scripts_are_wrappers(self):
        for fn in SKILL_SCRIPTS.glob("*.py"):
            if fn.name in ("prk_config.py", "prk_schema.py"):
                continue
            root = ROOT_SCRIPTS / fn.name
            self.assertTrue(root.exists(), f"缺 wrapper: {root}")
            text = root.read_text(encoding="utf-8")
            self.assertIn("兼容入口", text, root)
            self.assertLess(len(text), 2000, f"{root} 不是薄 wrapper")

    def test_shared_modules_exist_in_skill(self):
        for name in ("prk_config.py", "prk_schema.py"):
            self.assertTrue((SKILL_SCRIPTS / name).exists(), name)


class TestConfig(unittest.TestCase):
    def test_legacy_meta_title_fallback(self):
        cfg_mod = load_module("prk_config", SKILL_SCRIPTS / "prk_config.py")
        with tempfile.TemporaryDirectory() as td:
            Path(td, "papers_meta.json").write_text(
                json.dumps({"project": "legacy", "title": "旧项目标题", "papers": []}),
                encoding="utf-8")
            cfg = cfg_mod.load_config(td)
            self.assertIn("旧项目标题", cfg_mod.project_title(cfg, {"title": "旧项目标题"}))

    def test_default_third_party_off(self):
        cfg_mod = load_module("prk_config", SKILL_SCRIPTS / "prk_config.py")
        cfg = cfg_mod.load_config(REPO)
        self.assertFalse(cfg_mod.cfg_get(cfg, "compliance", "allow_third_party", default=False))


class TestSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module("prk_schema", SKILL_SCRIPTS / "prk_schema.py")

    def test_meta_templates_valid(self):
        for rel in (
            "skills/paper-review-kit/templates/papers_meta.example.json",
            "examples/microfluidics/papers_meta.json",
        ):
            data = json.loads((REPO / rel).read_text(encoding="utf-8"))
            errors, _ = self.mod.validate_meta(data)
            self.assertEqual(errors, [], rel)

    def test_summary_template_valid(self):
        data = json.loads(
            (REPO / "skills/paper-review-kit/templates/summary.example.json").read_text(encoding="utf-8"))
        errors, _ = self.mod.validate_summary(data)
        self.assertEqual(errors, [])

    def test_pdf_status_enum(self):
        errors, _ = self.mod.validate_summary({"pdf_status": "已获取PDF全文精读"})
        self.assertTrue(any("pdf_status" in e for e in errors))
        errors, _ = self.mod.validate_summary({"pdf_status": "missing"})
        self.assertTrue(errors)  # 还缺其他必填字段，但不含 pdf_status 非法错误
        self.assertFalse(any("pdf_status 非法" in e for e in errors))


class TestCrossrefYear(unittest.TestCase):
    def test_year_extraction(self):
        vm = load_module("verify_meta", SKILL_SCRIPTS / "verify_meta.py")
        m = {"published-print": {"date-parts": [[2023, 5, 1]]}}
        self.assertEqual(vm._year_from_crossref(m), 2023)
        self.assertEqual(vm._year_from_crossref({"published-online": {"date-parts": [[2022]]}}), 2022)
        self.assertIsNone(vm._year_from_crossref({}))


class TestFetchXml(unittest.TestCase):
    def test_xml_to_text(self):
        fx = load_module("fetch_xml", SKILL_SCRIPTS / "fetch_xml.py")
        text = fx.xml_to_text(
            "<article><title>T</title><p>Hello &amp; bye</p><fig-caption>Fig 1</fig-caption></article>")
        self.assertIn("T", text)
        self.assertIn("Hello & bye", text)
        self.assertIn("Fig 1", text)


if __name__ == "__main__":
    unittest.main()
