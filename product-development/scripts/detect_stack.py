#!/usr/bin/env python3
"""Select one frontend development profile from project config and package.json."""

import argparse
import json
import re
import sys
from pathlib import Path


PROFILES = {
    "react-antd": "references/profiles/react-antd.md",
    "vue2-element": "references/profiles/vue2-element.md",
    "vue3-element-plus": "references/profiles/vue3-element-plus.md",
}


def profile_from_label(label):
    value = str(label or "").lower().replace("_", " ")
    if "vue" in value:
        if re.search(r"vue\s*2\b", value) or "element ui" in value:
            return "vue2-element"
        if re.search(r"vue\s*3\b", value) or "element plus" in value:
            return "vue3-element-plus"
        raise ValueError("stack.frontend 声明了 Vue，但未指明 Vue 2 或 Vue 3")
    if "react" in value:
        return "react-antd"
    raise ValueError("无法识别 stack.frontend: %s" % label)


def major(version):
    match = re.search(r"(?<!\d)([23])(?:\.\d+)?", str(version or ""))
    return int(match.group(1)) if match else None


def numeric_version(version):
    match = re.search(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)", str(version or ""))
    return match.group(1) if match else None


def profile_from_package(package):
    dependencies = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        value = package.get(key, {})
        if isinstance(value, dict):
            dependencies.update(value)
    has_react = "react" in dependencies
    has_vue = "vue" in dependencies
    if has_react and has_vue:
        raise ValueError("package.json 同时包含 React 与 Vue；请在 product-workflow.json 明确 stack.frontend")
    if has_react:
        return "react-antd"
    if has_vue:
        vue_major = major(dependencies["vue"])
        if vue_major == 2 or "element-ui" in dependencies:
            compiler = dependencies.get("vue-template-compiler")
            vue_version, compiler_version = numeric_version(dependencies["vue"]), numeric_version(compiler)
            if compiler and vue_version and compiler_version and vue_version != compiler_version:
                raise ValueError("Vue 2 与 vue-template-compiler 必须使用完全一致的版本（%s != %s）" %
                                 (vue_version, compiler_version))
            sfc_major = major(dependencies.get("@vue/compiler-sfc"))
            if sfc_major == 3:
                raise ValueError("Vue 2 项目不能混用 Vue 3 的 @vue/compiler-sfc")
            return "vue2-element"
        if vue_major == 3 or "element-plus" in dependencies:
            if "vue-template-compiler" in dependencies:
                raise ValueError("Vue 3 项目不应使用 Vue 2 的 vue-template-compiler")
            return "vue3-element-plus"
        raise ValueError("无法从 vue 版本识别 Vue 2/3；请明确 stack.frontend")
    return None


def detect(project_root):
    root = Path(project_root).resolve()
    config_path = root / "product-workflow.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    if not isinstance(config, dict):
        raise ValueError("product-workflow.json 必须为对象")
    paths = config.get("paths", {}) if isinstance(config, dict) else {}
    frontend = paths.get("frontend", "frontend") if isinstance(paths, dict) else "frontend"
    if not isinstance(frontend, str) or not frontend or Path(frontend).is_absolute():
        raise ValueError("paths.frontend 必须为非空项目相对路径")
    frontend_root = (root / frontend).resolve()
    if frontend_root != root and root not in frontend_root.parents:
        raise ValueError("paths.frontend 不可越出项目根")
    declared = config.get("stack", {}).get("frontend") if isinstance(config.get("stack", {}), dict) else None

    package_paths = [frontend_root / "package.json", root / "package.json"]
    package_path = next((path for path in package_paths if path.is_file()), None)
    detected = None
    if package_path:
        detected = profile_from_package(json.loads(package_path.read_text(encoding="utf-8")))

    if declared:
        selected = profile_from_label(declared)
        if detected and selected != detected:
            raise ValueError("stack.frontend=%s 与 %s 的依赖不一致（%s）" %
                             (declared, package_path, detected))
        reason = "product-workflow.json"
    elif detected:
        selected, reason = detected, str(package_path.relative_to(root))
    else:
        selected, reason = "react-antd", "新项目默认"
    return {"profile": selected, "reference": PROFILES[selected], "reason": reason}


def main(argv=None):
    parser = argparse.ArgumentParser(description="识别 product-development 前端 profile")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = detect(args.project_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("%s\t%s\t%s" % (result["profile"], result["reference"], result["reason"]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print("ERROR: %s" % error, file=sys.stderr)
        sys.exit(2)
