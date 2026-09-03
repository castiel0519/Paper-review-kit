#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_xml.py — 出版方拦截 PDF 时，用 Europe PMC fullTextXML 生成
papers_txt/{id}.txt 与 digests/{id}.md。

PMCID 不再硬编码：从 papers_meta.json 的 xml_pmcid 字段读取。
默认处理所有 xml_pmcid 非空的论文，也可用 --ids 01,02 指定。
"""
import argparse
import re

import requests

from prk_config import (
    cfg_get, load_papers_meta, output_dir, parse_project_arg,
)
from prk_schema import validate_meta

TAGS_TO_NEWLINE = re.compile(r"<(title|h[1-6]|p|fig-caption|[a-z]+-caption)\b[^>]*>", re.I)
TAG_STRIP = re.compile(r"<[^>]+>")


def xml_to_text(xml_text):
    text = TAGS_TO_NEWLINE.sub("\n", xml_text)
    text = TAG_STRIP.sub(" ", text)
    for entity, char in (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"),
                         ("&#x000A;", "\n"), ("&#10;", "\n")):
        text = text.replace(entity, char)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def fetch_fulltext_xml(cfg, pmcid):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    headers = {
        "User-Agent": cfg_get(cfg, "apis", "user_agent",
                              default="paper-review-kit/1.0 (mailto:researcher@example.com)"),
        "Accept": "application/xml",
    }
    r = requests.get(url, timeout=cfg_get(cfg, "download", "timeout", default=60),
                     headers=headers)
    r.raise_for_status()
    return r.text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", default="",
                        help="逗号分隔的论文 ID，如 02；缺省为全部 xml_pmcid 非空的论文")
    cfg, args = parse_project_arg(parser)
    meta = load_papers_meta(cfg)
    errors, _ = validate_meta(meta)
    if errors:
        raise SystemExit("papers_meta 校验失败：\n  - " + "\n  - ".join(errors))

    selected = [i.strip() for i in args.ids.split(",") if i.strip()]
    if selected:
        papers = [p for p in meta["papers"] if str(p.get("id")) in selected]
    else:
        papers = [p for p in meta["papers"] if p.get("xml_pmcid")]
    if not papers:
        print("no papers with xml_pmcid / matching --ids")
        return

    txt_dir = output_dir(cfg, "papers_txt")
    dig_dir = output_dir(cfg, "digests")
    for p in papers:
        pid = str(p.get("id"))
        pmcid = p.get("xml_pmcid") or p.get("pmcid")
        if not pmcid:
            print(f"[{pid}] no PMCID, skip")
            continue
        print(f"[{pid}] fetch XML {pmcid}")
        xml_text = fetch_fulltext_xml(cfg, pmcid)
        text = xml_to_text(xml_text)
        if not text:
            print(f"[{pid}] empty text, skip")
            continue
        txt_path = txt_dir / f"{pid}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("===PAGE 1===\n" + text + "\n")
        dig_path = dig_dir / f"{pid}.md"
        with open(dig_path, "w", encoding="utf-8") as f:
            f.write(f"### {pid} digest\n\n## XML full text (Europe PMC)\n{text[:12000]}\n")
        print(f"[{pid}] wrote {txt_path.name} ({len(text)} chars) and digest")


if __name__ == "__main__":
    main()
