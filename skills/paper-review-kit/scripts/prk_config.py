#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prk_config.py — paper-review-kit 共享配置/IO 工具。

项目根定位优先级：
  1. 环境变量 PRK_PROJECT
  2. 命令行 --project 参数（各脚本自行解析后传入）
  3. 从当前目录向上查找第一个含 project.yml / papers_meta.json 的目录
  4. 当前工作目录

配置优先级：项目 project.yml > 内置默认值；若 project.yml 缺失则继续用
papers_meta.json 里的 project/title/range 兼容旧项目。
"""
import argparse
import copy
import json
import os
from pathlib import Path

CONFIG_FILENAMES = ("project.yml", "project.yaml", "project.json")

# 通用默认值：不再包含任何“微流控”专案内容。
DEFAULT_CONFIG = {
    "project": {
        "slug": "paper_review",
        "topic": "论文调研",
        "topic_en": "Paper Review",
        "title": "论文精读调研报告",
        "title_en": "Paper Review Report",
        "range": "2020-2026",
    },
    "compliance": {
        "allow_third_party": False,
    },
    "download": {
        "workers": 6,
        "max_mb": 60,
        "timeout": 45,
    },
    "apis": {
        "mailto": "researcher@example.com",
        "user_agent": "paper-review-kit/1.0 (mailto:researcher@example.com)",
    },
    "report": {
        "cover_subtitle": "SCI 论文精读调研报告",
        "default_kind_zh": "综合",
        "default_kind_en": "General",
    },
    "paths": {
        "papers": "papers",
        "papers_txt": "papers_txt",
        "papers_figs": "papers_figs",
        "summaries": "summaries",
        "digests": "digests",
        "deliverables": "deliverables",
    },
}


def _deep_merge(base, override):
    """返回新 dict：override 递归覆盖 base，不修改入参。"""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def add_project_arg(parser):
    """给脚本的 argparse 增加统一的 --project 参数。"""
    parser.add_argument(
        "--project",
        default=None,
        help="项目根目录（默认：PRK_PROJECT 或从当前目录向上自动查找）",
    )


def find_project_root(explicit=None):
    """定位项目根目录；找不到配置时退回当前目录（兼容只复制脚本的老项目）。"""
    env = os.environ.get("PRK_PROJECT")
    start = Path(explicit or env or os.getcwd()).expanduser().resolve()
    candidates = [start, *start.parents]
    for cand in candidates:
        if any((cand / name).exists() for name in CONFIG_FILENAMES):
            return cand
        if (cand / "papers_meta.json").exists():
            return cand
    return start


def load_config(explicit=None):
    """读取 project.yml（或 .yaml/.json），合并默认值，并附上项目根路径。"""
    root = find_project_root(explicit)
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg_file = None
    for name in CONFIG_FILENAMES:
        p = root / name
        if p.exists():
            cfg_file = p
            break
    if cfg_file is not None:
        raw = _read_config_file(cfg_file)
        if raw:
            cfg = _deep_merge(cfg, raw)
    cfg["_project_root"] = str(root)
    return cfg


def _read_config_file(path):
    path = Path(path)
    try:
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            import yaml  # PyYAML
        except ImportError as e:
            raise RuntimeError(
                "读取 project.yml 需要 PyYAML：pip install pyyaml；"
                "或者改用 project.json。"
            ) from e
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else None
    except Exception as e:
        raise RuntimeError(f"读取配置失败 {path}: {e}") from e


def project_path(cfg, *parts):
    """cfg['_project_root'] 下的相对路径。"""
    root = Path(cfg.get("_project_root", os.getcwd()))
    return root.joinpath(*parts)


def output_dir(cfg, key):
    """按配置里的 paths.<key> 返回项目下的输出目录（自动创建）。"""
    rel = cfg.get("paths", {}).get(key, key)
    path = project_path(cfg, rel)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path, default=None):
    """读 JSON；文件不存在时返回 default，语法错误直接抛出。"""
    path = Path(path)
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    """原子写 JSON（临时文件 + rename），保证中断不留下半截文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return path


def load_papers_meta(cfg, verified=False, required=True):
    """读 papers_meta(.json)；未核验项目可传 verified=True 读取核验结果。"""
    root = Path(cfg["_project_root"])
    name = "papers_meta_verified.json" if verified else "papers_meta.json"
    path = root / name
    data = read_json(path)
    if data is None:
        if required:
            raise FileNotFoundError(f"缺少 {path}")
        return None
    if isinstance(data, dict) and "papers" in data:
        return data
    if isinstance(data, list):
        return {"papers": data}
    raise ValueError(f"{path} 结构非法：需要对象且含 papers 列表")


def cfg_get(cfg, *keys, default=None):
    """按路径取配置项，任意层缺失返回 default。"""
    cur = cfg
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def project_title(cfg, meta=None):
    """报告主标题：project.yml 优先，否则退回 papers_meta.json 的 title。"""
    title = cfg_get(cfg, "project", "title")
    if title and title != DEFAULT_CONFIG["project"]["title"]:
        return title
    if isinstance(meta, dict) and meta.get("title"):
        return meta["title"]
    return title


def project_topic(cfg, meta=None):
    """报告主题词：project.yml 优先，否则从 title 或 meta 兜底。"""
    topic = cfg_get(cfg, "project", "topic")
    if topic and topic != DEFAULT_CONFIG["project"]["topic"]:
        return topic
    if isinstance(meta, dict) and meta.get("topic"):
        return meta["topic"]
    return topic


def project_range(cfg, meta=None):
    """论文年份范围：project.yml 优先，否则 meta.range，最后默认值。"""
    rng = cfg_get(cfg, "project", "range")
    if isinstance(meta, dict) and meta.get("range"):
        rng = meta["range"]
    return rng


def parse_project_arg(parser=None):
    """脚本入口的常见三行：构造 parser、加 --project、返回 (cfg, args)。"""
    if parser is None:
        parser = argparse.ArgumentParser()
    add_project_arg(parser)
    args = parser.parse_args()
    return load_config(args.project), args


if __name__ == "__main__":
    cfg = load_config()
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
