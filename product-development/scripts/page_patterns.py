#!/usr/bin/env python3
"""List and validate the backend page-pattern catalog without external packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = SKILL_ROOT / "references/page-patterns/catalog.json"
REQUIRED_FIELDS = {
    "id",
    "title",
    "appliesWhen",
    "reference",
    "section",
    "requiredConcerns",
}


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        catalog = json.load(file)
    validate_catalog(catalog, path.parent.parent.parent)
    return catalog


def validate_catalog(catalog: dict[str, Any], skill_root: Path = SKILL_ROOT) -> None:
    if catalog.get("schemaVersion") != 1:
        raise ValueError("catalog.json 的 schemaVersion 必须为 1")
    patterns = catalog.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        raise ValueError("catalog.json 必须包含非空 patterns 数组")

    seen: set[str] = set()
    for index, pattern in enumerate(patterns):
        if not isinstance(pattern, dict):
            raise ValueError(f"patterns[{index}] 必须是对象")
        missing = REQUIRED_FIELDS - pattern.keys()
        if missing:
            raise ValueError(f"patterns[{index}] 缺少字段: {', '.join(sorted(missing))}")
        pattern_id = pattern["id"]
        if not isinstance(pattern_id, str) or not pattern_id:
            raise ValueError(f"patterns[{index}].id 必须是非空字符串")
        if pattern_id in seen:
            raise ValueError(f"存在重复模式 ID: {pattern_id}")
        seen.add(pattern_id)
        concerns = pattern["requiredConcerns"]
        if not isinstance(concerns, list) or not concerns or not all(isinstance(item, str) and item for item in concerns):
            raise ValueError(f"模式 {pattern_id} 的 requiredConcerns 必须是非空字符串数组")
        reference = skill_root / pattern["reference"]
        if not reference.is_file():
            raise ValueError(f"模式 {pattern_id} 的参考文件不存在: {pattern['reference']}")


def find_pattern(catalog: dict[str, Any], pattern_id: str) -> dict[str, Any]:
    for pattern in catalog["patterns"]:
        if pattern["id"] == pattern_id:
            return pattern
    available = ", ".join(pattern["id"] for pattern in catalog["patterns"])
    raise ValueError(f"未知模式 {pattern_id}；可用值: {available}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="后台页面模式目录工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="校验目录结构和参考文件")
    list_parser = subparsers.add_parser("list", help="列出全部模式")
    list_parser.add_argument("--json", action="store_true", help="输出 JSON")
    show_parser = subparsers.add_parser("show", help="查看一个模式")
    show_parser.add_argument("pattern_id")
    show_parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        catalog = load_catalog()
        if args.command == "validate":
            print(f"OK: {len(catalog['patterns'])} 个页面模式，参考文件均存在")
            return 0
        if args.command == "list":
            if args.json:
                print(json.dumps(catalog["patterns"], ensure_ascii=False, indent=2))
            else:
                for pattern in catalog["patterns"]:
                    print(f"{pattern['id']}\t{pattern['title']}\t{pattern['appliesWhen']}")
            return 0
        pattern = find_pattern(catalog, args.pattern_id)
        if args.json:
            print(json.dumps(pattern, ensure_ascii=False, indent=2))
        else:
            print(f"{pattern['id']} · {pattern['title']}")
            print(f"适用：{pattern['appliesWhen']}")
            print(f"读取：{pattern['reference']}（{pattern['section']}）")
            print("必须处理：" + "、".join(pattern["requiredConcerns"]))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
