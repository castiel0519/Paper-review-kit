#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retheme.py — 设置/切换调研主题（兼容旧命令名）。

M1 起不再修改 make_docx.py / make_pptx.py 源码，而是写入项目根目录的
project.yml（已存在则合并更新，不覆盖其他配置）。报告渲染器会读取这些字段。

用法：
    python scripts/retheme.py --topic 癌症早筛 --topic-en "Cancer Screening"
    python scripts/retheme.py --project D:/some/project --topic 材料发现
"""
import argparse
import json
from pathlib import Path

from prk_config import DEFAULT_CONFIG, add_project_arg, find_project_root, load_config


def load_raw(path):
    if path.suffix.lower() == ".json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    try:
        import yaml
    except ImportError as e:
        raise SystemExit("写 project.yml 需要 PyYAML：pip install pyyaml") from e
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def write_raw(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    else:
        try:
            import yaml
        except ImportError as e:
            raise SystemExit("写 project.yml 需要 PyYAML：pip install pyyaml") from e
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_project_arg(parser)
    parser.add_argument("--topic", required=True, help="新主题中文名，如：癌症早筛")
    parser.add_argument("--topic-en", default=None, help="新主题英文名")
    parser.add_argument("--title", default=None, help="报告完整中文标题（缺省自动生成）")
    parser.add_argument("--title-en", default=None, help="报告完整英文标题（缺省自动生成）")
    args = parser.parse_args()

    root = find_project_root(args.project)
    path = root / "project.yml"
    if path.exists():
        data = load_raw(path)
    else:
        path = root / "project.json"
        if path.exists():
            data = load_raw(path)
        else:
            path = root / "project.yml"
            data = {}
    data.setdefault("project", {})
    proj = data["project"]
    proj["topic"] = args.topic
    if args.topic_en:
        proj["topic_en"] = args.topic_en
    if args.title:
        proj["title"] = args.title
    else:
        proj["title"] = f"机器学习与人工智能在{args.topic}中的应用"
    if args.title_en:
        proj["title_en"] = args.title_en
    elif args.topic_en:
        proj["title_en"] = f"Machine Learning and AI in {args.topic_en}"
    write_raw(path, data)
    print(f"theme updated -> {path}")
    print(json.dumps(data.get("project", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
