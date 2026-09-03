#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容入口：真正的实现在 skills/paper-review-kit/scripts/ 下（单一事实源）。"""
import runpy
import sys
from pathlib import Path
impl = Path(__file__).resolve().parents[1] / "skills" / "paper-review-kit" / "scripts" / Path(__file__).name
if not impl.exists():
    raise SystemExit(f"canonical implementation missing: {impl}")
sys.path.insert(0, str(impl.parent))
runpy.run_path(str(impl), run_name="__main__")
