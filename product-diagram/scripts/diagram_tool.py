#!/usr/bin/env python3
"""Render registered Mermaid blocks and verify that diagram artifacts are current."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


SCHEMA_VERSION = 1
STAGES = {
    "requirement", "design", "architecture", "module",
    "development", "test", "diagnosis", "delivery",
}
TYPES = {
    "current-target-flow", "user-journey", "business-flow", "swimlane",
    "state", "navigation", "system-context", "deployment", "data-flow",
    "er", "sequence", "module-dependency", "test-coverage",
    "failure-sequence", "cause-tree", "impact-map", "delivery-overview",
}
ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{2,63}$")
FENCE_RE = re.compile(r"^\s*```mermaid\s*\n(.*?)^\s*```\s*$", re.MULTILINE | re.DOTALL)


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def digest_text(content: str) -> str:
    return digest_bytes(content.encode("utf-8"))


def project_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("路径必须是非空项目相对路径: %r" % relative)
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise ValueError("路径不可越出项目根: %s" % relative)
    return path


def relative_path(root: Path, value: str) -> tuple[Path, str]:
    candidate = Path(value)
    path = candidate.resolve() if candidate.is_absolute() else project_path(root, value)
    if path != root and root not in path.parents:
        raise ValueError("路径不可越出项目根: %s" % value)
    return path, path.relative_to(root).as_posix()


def mermaid_blocks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".mmd", ".mermaid"}:
        return [text.strip()]
    return [match.group(1).strip() for match in FENCE_RE.finditer(text)]


def select_block(path: Path, index: int) -> str:
    blocks = mermaid_blocks(path)
    if not blocks:
        raise ValueError("来源文件没有 Mermaid 代码块: %s" % path)
    if index < 0 or index >= len(blocks):
        raise ValueError("Mermaid 块序号越界: %d，可用范围 0..%d" % (index, len(blocks) - 1))
    return blocks[index]


def runtime_script() -> Path:
    script = Path(__file__).resolve().parents[1] / "validators" / "mermaid.mjs"
    if not script.is_file():
        raise ValueError("缺少图表渲染运行时，请重新安装 product-diagram")
    return script


def render_svg(diagram_id: str, title: str, description: str, source: str) -> str:
    request = {
        "action": "render", "id": diagram_id.lower(), "title": title,
        "description": description, "text": source,
    }
    try:
        run = subprocess.run(
            ["node", str(runtime_script())],
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=90,
            cwd=runtime_script().parent,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("Mermaid 渲染运行时不可用: %s" % error) from error
    try:
        result = json.loads(run.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("Mermaid 渲染器返回异常: %s" % (run.stderr or run.stdout)[:500]) from error
    if run.returncode or not result.get("ok"):
        raise ValueError("Mermaid 渲染失败: %s" % result.get("error", run.stderr[:500]))
    svg = result.get("svg")
    if not isinstance(svg, str) or "<svg" not in svg or "<title" not in svg or "<desc" not in svg:
        raise ValueError("Mermaid 渲染结果缺少可访问 SVG")
    return svg


def html_document(title: str, description: str, svg: str) -> str:
    safe_title = html.escape(title)
    safe_description = html.escape(description)
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 32px; color: #172033; background: #fff; font-family: Arial, "PingFang SC", "Microsoft YaHei", sans-serif; }}
    main {{ max-width: 1280px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    p {{ margin: 0 0 24px; color: #526078; line-height: 1.6; }}
    figure {{ margin: 0; overflow-x: auto; }}
    svg {{ display: block; min-width: 720px; max-width: 100%; height: auto; }}
    @media print {{ body {{ padding: 0; }} figure {{ overflow: visible; }} }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>{description}</p>
    <figure>{svg}</figure>
  </main>
</body>
</html>
""".format(title=safe_title, description=safe_description, svg=svg)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".%s-" % path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "diagrams": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("diagrams"), list):
        raise ValueError("图表清单格式不受支持: %s" % path)
    return data


def artifact_entry(root: Path, path: Path) -> dict:
    return {"path": path.relative_to(root).as_posix(), "sha256": digest_bytes(path.read_bytes())}


def render(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    if not root.is_dir():
        raise ValueError("项目根目录不存在: %s" % root)
    if not ID_RE.fullmatch(args.id):
        raise ValueError("图表 ID 必须为 3–64 位大写字母、数字、连字符或下划线")
    source_path, source_relative = relative_path(root, args.source)
    if not source_path.is_file():
        raise ValueError("来源文件不存在: %s" % source_path)
    block = select_block(source_path, args.diagram_index)
    svg = render_svg(args.id, args.title, args.description, block)
    html_text = html_document(args.title, args.description, svg)

    output_root = project_path(root, args.output_dir)
    diagram_dir = output_root / args.id
    mmd_path = diagram_dir / "source.mmd"
    svg_path = diagram_dir / (args.id + ".svg")
    html_path = diagram_dir / (args.id + ".html")
    atomic_write(mmd_path, block.rstrip() + "\n")
    atomic_write(svg_path, svg.rstrip() + "\n")
    atomic_write(html_path, html_text)

    manifest_path = output_root / "manifest.json"
    manifest = load_manifest(manifest_path)
    entry = {
        "id": args.id,
        "stage": args.stage,
        "type": args.type,
        "title": args.title,
        "description": args.description,
        "source": {
            "path": source_relative,
            "diagram_index": args.diagram_index,
            "sha256": digest_text(block),
        },
        "artifacts": {
            "mmd": artifact_entry(root, mmd_path),
            "svg": artifact_entry(root, svg_path),
            "html": artifact_entry(root, html_path),
        },
    }
    rows = [row for row in manifest["diagrams"] if row.get("id") != args.id]
    rows.append(entry)
    manifest["diagrams"] = sorted(rows, key=lambda row: row["id"])
    atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("已生成图表 %s：%s" % (args.id, html_path))
    print("来源与产物清单：%s" % manifest_path)
    return 0


def check_entry(root: Path, row: dict) -> list[str]:
    errors = []
    diagram_id = row.get("id", "<unknown>")
    if not isinstance(diagram_id, str) or not ID_RE.fullmatch(diagram_id):
        return ["图表 ID 非法: %r" % diagram_id]
    if row.get("stage") not in STAGES:
        errors.append("%s: stage 非法" % diagram_id)
    if row.get("type") not in TYPES:
        errors.append("%s: type 非法" % diagram_id)
    if not isinstance(row.get("title"), str) or not row["title"].strip():
        errors.append("%s: title 为空" % diagram_id)
    source = row.get("source")
    if not isinstance(source, dict):
        return errors + ["%s: source 缺失" % diagram_id]
    try:
        source_path = project_path(root, source["path"])
        block = select_block(source_path, source["diagram_index"])
        if source.get("sha256") != digest_text(block):
            errors.append("%s: 来源 Mermaid 块已变化" % diagram_id)
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append("%s: 来源不可验证: %s" % (diagram_id, error))
        block = None

    artifacts = row.get("artifacts")
    if not isinstance(artifacts, dict):
        return errors + ["%s: artifacts 缺失" % diagram_id]
    contents = {}
    for name in ("mmd", "svg", "html"):
        item = artifacts.get(name)
        try:
            path = project_path(root, item["path"])
            content = path.read_bytes()
            contents[name] = content
            if item.get("sha256") != digest_bytes(content):
                errors.append("%s: %s 产物已被修改" % (diagram_id, name))
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append("%s: %s 产物不可验证: %s" % (diagram_id, name, error))
    if block is not None and contents.get("mmd", b"").decode("utf-8", "replace").strip() != block.strip():
        errors.append("%s: source.mmd 与权威来源不一致" % diagram_id)
    svg = contents.get("svg", b"").decode("utf-8", "replace")
    if svg and not all(token in svg for token in ("<svg", 'role="img"', "<title", "<desc")):
        errors.append("%s: SVG 缺少可访问标题或描述" % diagram_id)
    html_text = contents.get("html", b"").decode("utf-8", "replace")
    if html_text and not all(token in html_text for token in ("<!doctype html>", '<meta charset="utf-8">', "<figure>")):
        errors.append("%s: HTML 结构不完整" % diagram_id)
    return errors


def check(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    manifest_path = project_path(root, args.manifest)
    if not manifest_path.is_file():
        print("图表检查失败：缺少清单 %s" % manifest_path, file=sys.stderr)
        return 1
    try:
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("图表检查失败：%s" % error, file=sys.stderr)
        return 1
    errors = []
    ids = [row.get("id") for row in manifest["diagrams"] if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        errors.append("清单中存在重复图表 ID")
    for row in manifest["diagrams"]:
        if not isinstance(row, dict):
            errors.append("清单包含非对象条目")
        else:
            errors.extend(check_entry(root, row))
    if errors:
        for error in errors:
            print("FAIL %s" % error)
        print("图表检查失败：%d 项" % len(errors))
        return 1
    print("图表检查通过：%d 张图" % len(manifest["diagrams"]))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    render_parser = commands.add_parser("render", help="渲染一个 Mermaid 块并登记来源")
    render_parser.add_argument("--project-root", default=".")
    render_parser.add_argument("--source", required=True, help="项目内 Markdown、.mmd 或 .mermaid 文件")
    render_parser.add_argument("--diagram-index", type=int, default=0, help="Markdown 中 Mermaid 块序号，从 0 开始")
    render_parser.add_argument("--id", required=True, help="稳定图表 ID")
    render_parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    render_parser.add_argument("--type", required=True, choices=sorted(TYPES))
    render_parser.add_argument("--title", required=True)
    render_parser.add_argument("--description", required=True)
    render_parser.add_argument("--output-dir", default="outputs/diagrams")
    render_parser.set_defaults(func=render)
    check_parser = commands.add_parser("check", help="检查图表来源、哈希和结构")
    check_parser.add_argument("--project-root", default=".")
    check_parser.add_argument("--manifest", default="outputs/diagrams/manifest.json")
    check_parser.set_defaults(func=check)
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("图表工具失败：%s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
