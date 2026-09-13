"""Project settings and explicit module source slices. Python standard library only."""
import copy
import json
import re
from pathlib import Path

CONFIG_NAME = "product-workflow.json"
DEFAULTS = {
    "schema_version": 1,
    "paths": {
        "requirement": "项目战略规划/原始需求.md",
        "execution": "项目战术执行",
        "design_name": "00_产品设计文档.md",
        "architecture_name": "00_功能架构设计文档.md",
        "frontend": "frontend", "backend": "backend", "e2e": "frontend/tests/e2e",
    },
    "spec_extensions": [".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx"],
    "stack": {"frontend": "React + TypeScript + Ant Design", "backend": "FastAPI + SQLAlchemy + PostgreSQL"},
    "commands": {
        "typecheck": {"cwd": "frontend", "argv": ["npx", "tsc", "--noEmit"]},
        "lint": {"cwd": "frontend", "argv": ["npx", "eslint", "src", "--max-warnings", "0"]},
        "e2e": {"cwd": "frontend", "argv": ["npx", "playwright", "test", "--reporter=junit"], "report": "junit"},
        "backend": {"cwd": "backend", "argv": ["python", "-m", "pytest", "-q", "--junitxml={report}"], "report": "junit"},
    },
    "module_sources": {},
    "exemptions": {},
    "ac_tests": {},
}


def local_path(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("路径必须为非空项目相对路径: %r" % relative)
    base = Path(root).resolve()
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise ValueError("路径不可越出项目根: %s" % relative)
    return path


def load_config(root):
    cfg = copy.deepcopy(DEFAULTS)
    path = Path(root) / CONFIG_NAME
    raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise ValueError("配置必须为对象，且不能含未知键")
    for key, value in raw.items():
        if isinstance(cfg[key], dict):
            if not isinstance(value, dict):
                raise ValueError("%s 必须为对象" % key)
            if key == "paths" and set(value) - set(cfg[key]):
                raise ValueError("paths 存在未知键")
            cfg[key].update(value)
        else:
            cfg[key] = value
    if cfg["schema_version"] != 1:
        raise ValueError("不支持的配置版本")
    for key, value in cfg["paths"].items():
        local_path(root, value)
        if key.endswith("_name") and Path(value).name != value:
            raise ValueError("文档名不能包含目录")
    # A moved frontend also moves default test and command directories.
    overrides = raw.get("paths", {})
    if "frontend" in overrides and "e2e" not in overrides:
        cfg["paths"]["e2e"] = overrides["frontend"] + "/tests/e2e"
    for name, command in cfg["commands"].items():
        if name not in raw.get("commands", {}) and name in DEFAULTS["commands"]:
            command["cwd"] = cfg["paths"]["backend" if name == "backend" else "frontend"]
        if not isinstance(command, dict) or not {"cwd", "argv"} <= set(command) or set(command) - {"cwd", "argv", "report"}:
            raise ValueError("命令必须含 cwd 与 argv: %s" % name)
        if command.get("report") not in (None, "junit"):
            raise ValueError("report 仅支持 junit")
        local_path(root, command["cwd"])
        if not isinstance(command["argv"], list) or not command["argv"] or not all(isinstance(x, str) and x for x in command["argv"]):
            raise ValueError("argv 必须为非空字符串数组")
    for key, reason in cfg["exemptions"].items():
        if key not in {"frontend", "backend", "typecheck", "lint", "e2e"} or not isinstance(reason, str) or len(reason.strip()) < 8 or any(x in reason for x in ("待补充", "TODO", "TBD")):
            raise ValueError("豁免必须指明支持的检查/代码端及具体范围理由（至少 8 字）")
    for ac, tests in cfg['ac_tests'].items():
        if not re.fullmatch(r'AC-[A-Z][A-Z0-9]{1,7}-[0-9]{2}', ac) or not isinstance(tests, list) or not tests:
            raise ValueError('ac_tests 必须映射合法 AC 到非空测试数组')
        for test in tests:
            if not isinstance(test, dict) or set(test) != {'check', 'classname', 'name'} or test['check'] not in cfg['commands'] or not all(isinstance(test[k], str) for k in test) or not test['name']:
                raise ValueError('测试映射必须提供 check/classname/name，与 JUnit 测试身份完全匹配')
    exts = cfg["spec_extensions"]
    if not isinstance(exts, list) or not exts or not all(isinstance(x, str) and re.fullmatch(r"\.spec\.[a-z]+", x) for x in exts):
        raise ValueError("spec_extensions 必须为 .spec.ts 等扩展名数组")
    for module, sources in cfg["module_sources"].items():
        module_path = local_path(root, module)
        if module_path.parent != local_path(root, cfg["paths"]["execution"]) or not re.fullmatch(r"\d{2}_.+详细设计\.md", module_path.name):
            raise ValueError("模块配置键必须为执行目录中的模块文档路径")
        if not isinstance(sources, list) or len(sources) != 2 or {s.get("source") for s in sources if isinstance(s, dict)} != {"design", "architecture"}:
            raise ValueError("模块必须分别声明 design 和 architecture 来源: %s" % module)
        for source in sources:
            ids = source.get("sections")
            if set(source) != {"source", "sections"} or not isinstance(ids, list) or not ids or not all(isinstance(x, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", x) for x in ids) or len(ids) != len(set(ids)):
                raise ValueError("sections 必须为不重复的稳定 ID 数组")
    return cfg


def document_paths(cfg):
    p = cfg["paths"]
    return {"design": str(Path(p["execution"]) / p["design_name"]),
            "architecture": str(Path(p["execution"]) / p["architecture_name"])}


def spec_files(directory, extensions):
    base = Path(directory)
    if not base.is_dir():
        return None
    return sorted(str(p) for p in base.rglob("*") if p.is_file() and any(p.name.endswith(ext) for ext in extensions))


def source_refs(cfg, module):
    docs = document_paths(cfg)
    return [(docs[s["source"]] + "#sections=" + ",".join(sorted(s["sections"])),
             "design_doc" if s["source"] == "design" else "arch_doc")
            for s in cfg["module_sources"].get(module, [])]


def read_source(root, reference):
    relative, sep, selection = reference.partition("#sections=")
    text = local_path(root, relative).read_text(encoding="utf-8")
    if not sep:
        return text
    wanted = selection.split(",")
    # Stable marker on its own line, immediately before a Markdown heading.
    lines = text.splitlines(keepends=True)
    markers, headings, fence = {}, [], None
    for i, line in enumerate(lines):
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if match:
            token, rest = match.groups()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not rest.strip():
                fence = None
            continue
        if fence:
            continue
        marker = re.fullmatch(r"<!-- workflow:id ([A-Za-z][A-Za-z0-9_-]*) -->\s*", line)
        if marker:
            key = marker.group(1)
            if key in markers:
                raise ValueError("重复来源 ID: %s" % key)
            markers[key] = i
        heading = re.match(r"^(#{1,6})\s+", line)
        if heading:
            headings.append((i, len(heading.group(1))))
    result = []
    for key in wanted:
        if key not in markers:
            raise ValueError("来源章节不存在: %s" % key)
        start = markers[key]
        h = next(((i, level) for i, level in headings if i == start + 1), None)
        if h is None:
            raise ValueError("来源 ID 后必须紧接标题: %s" % key)
        end = next((i for i, level in headings if i > h[0] and level <= h[1]), len(lines))
        if end > 0 and end - 1 in markers.values():
            end -= 1
        result.append("".join(lines[start:end]).rstrip())
    return "\n\n".join(result) + "\n"
