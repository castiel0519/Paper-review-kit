#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prk_schema.py — papers_meta.json 与 summaries/*.json 的轻量校验（无外部依赖）。

原则：M1 只做“拦住会炸流水线的错误 + 统一数据契约”，不做过度严格校验。
"""
import json
import os
from pathlib import Path

PDF_STATUSES = ("pdf_read", "abstract_only", "missing")

PAPER_REQUIRED = ["id", "title"]
PAPER_OPTIONAL = [
    "title_zh", "authors", "doi", "pmid", "pmcid", "kind", "kind_zh", "journal",
    "year", "notes", "manual_urls", "xml_pmcid", "download_overrides",
    "figure_overrides", "read_depth",
]

SUMMARY_FIELDS = [
    "id", "title_en", "title_zh", "journal", "year", "doi", "pmid", "pmcid",
    "kind", "kind_zh", "pdf_status",
    "abstract_en", "abstract_zh", "background_zh", "problem_zh", "data_zh",
    "task_zh", "method_zh", "results_zh", "metrics_zh", "innovation_zh",
    "limitation_zh", "paradigm_tags", "paradigm_zh", "framework_zh",
    "framework_steps", "scheme_zh", "lessons_zh",
    "scheme_image", "evidence_pages", "figure_refs", "reviewed",
]

SUMMARY_REQUIRED = [
    "id", "title_en", "title_zh", "journal", "year", "kind", "kind_zh",
    "pdf_status", "method_zh", "results_zh",
]

# 与 SKILL.md 的长度契约保持一致
SUMMARY_MAX_LEN = {
    "method_zh": 1200,
    "results_zh": 1200,
    "framework_zh": 1200,
    "scheme_zh": 1200,
}
SUMMARY_DEFAULT_MAX = 600


def _str_errors(errors):
    return "; ".join(errors)


def validate_meta(data):
    """返回 (errors, warnings)。只检查结构，不修改数据。"""
    errors, warnings = [], []
    if not isinstance(data, dict) or not isinstance(data.get("papers"), list):
        return ["papers_meta.json 必须是对象且含 papers 列表"], warnings
    papers = data["papers"]
    if not papers:
        errors.append("papers 列表为空")
    seen_ids = set()
    for idx, p in enumerate(papers):
        where = f"papers[{idx}]"
        if not isinstance(p, dict):
            errors.append(f"{where} 不是对象")
            continue
        pid = p.get("id")
        if pid is None or str(pid).strip() == "":
            errors.append(f"{where} 缺少 id")
        elif pid in seen_ids:
            errors.append(f"{where} id={pid} 重复")
        else:
            seen_ids.add(pid)
        for key in PAPER_REQUIRED:
            val = p.get(key)
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(f"{where} 缺少必填字段 {key}")
        for key in PAPER_OPTIONAL:
            val = p.get(key)
            if val is not None and key == "year" and not isinstance(val, int):
                errors.append(f"{where} year 应为整数，当前为 {val!r}")
            if key == "manual_urls" and val is not None:
                if not isinstance(val, list):
                    errors.append(f"{where} manual_urls 应为列表")
                else:
                    for ui, u in enumerate(val):
                        if isinstance(u, str):
                            continue
                        if not (isinstance(u, dict) and isinstance(u.get("url"), str) and u["url"]):
                            errors.append(f"{where} manual_urls[{ui}] 非法：需字符串或 {{url, referer}}")
            if key == "download_overrides" and val is not None:
                if not isinstance(val, list):
                    errors.append(f"{where} download_overrides 应为列表")
        if p.get("doi") is not None and not isinstance(p.get("doi"), str):
            errors.append(f"{where} doi 应为字符串")
        if p.get("read_depth") is not None and p.get("read_depth") not in ("brief", "targeted", "full"):
            errors.append(f"{where} read_depth 非法：应简为 brief/targeted/full")
        fo = p.get("figure_overrides")
        if fo is not None:
            if not isinstance(fo, dict):
                errors.append(f"{where} figure_overrides 应为对象")
            else:
                if not isinstance(fo.get("page"), int):
                    errors.append(f"{where} figure_overrides.page 应为整数")
                bb = fo.get("bbox")
                if not (isinstance(bb, list) and len(bb) == 4):
                    errors.append(f"{where} figure_overrides.bbox 应为 [x0,y0,x1,y1]")
    return errors, warnings


def validate_summary(s):
    """返回 (errors, warnings)。errors 会阻止正常交付，warnings 只是提示。"""
    errors, warnings = [], []
    if not isinstance(s, dict):
        return ["summary 不是对象"], []
    for key in SUMMARY_REQUIRED:
        val = s.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"缺少字段 {key}")
    status = s.get("pdf_status")
    if status is not None and status not in PDF_STATUSES:
        errors.append(f"pdf_status 非法：{status!r}，允许值 {PDF_STATUSES}")
    if status == "pdf_read":
        for field in ("evidence_pages", "figure_refs"):
            val = s.get(field)
            if not val or (isinstance(val, list) and len(val) == 0):
                errors.append(f"{field} 缺失：pdf_read 论文必须给出证据链")
    if errors:
        return errors, warnings
    for key, limit in SUMMARY_MAX_LEN.items():
        val = s.get(key)
        if isinstance(val, str) and len(val) > limit:
            warnings.append(f"{key} 超长 {len(val)}/{limit}")
    for key in SUMMARY_FIELDS:
        if key in SUMMARY_MAX_LEN or key in SUMMARY_REQUIRED:
            continue
        val = s.get(key)
        if isinstance(val, str) and len(val) > SUMMARY_DEFAULT_MAX:
            warnings.append(f"{key} 超长 {len(val)}/{SUMMARY_DEFAULT_MAX}")
    metrics = s.get("metrics_zh")
    if isinstance(metrics, list) and len(metrics) > 5:
        warnings.append(f"metrics_zh 超过 5 条（当前 {len(metrics)}）")
    tags = s.get("paradigm_tags")
    if isinstance(tags, list) and not (3 <= len(tags) <= 8):
        warnings.append(f"paradigm_tags 应为 3-8 个（当前 {len(tags)}）")
    steps = s.get("framework_steps")
    if isinstance(steps, list) and not (4 <= len(steps) <= 6):
        warnings.append(f"framework_steps 应为 4-6 条（当前 {len(steps)}）")
    return errors, warnings


def load_and_validate_meta(path):
    """读并校验 papers_meta.json；失败抛 ValueError，附带可读信息。"""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    errors, _ = validate_meta(data)
    if errors:
        raise ValueError(f"{path} 校验失败：{_str_errors(errors)}")
    return data


def validate_summaries_dir(sum_dir):
    """批量校验 summaries 目录，返回 {id: (errors, warnings)}。"""
    out = {}
    if not os.path.isdir(sum_dir):
        return out
    for fn in sorted(os.listdir(sum_dir)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(sum_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            out[fn] = validate_summary(data)
        except Exception as e:
            out[fn] = ([f"无法读取/解析：{e}"], [])
    return out


def first_error(result):
    return result[0][0] if result and result[0] else ""


if __name__ == "__main__":
    import sys
    cfg_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(validate_summaries_dir(cfg_dir), ensure_ascii=False, indent=2))
