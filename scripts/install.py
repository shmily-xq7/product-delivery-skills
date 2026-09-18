"""Stage and verify the complete skill bundle before replacing installed directories."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile


APP_PROFILES = {
    "claude-code": {
        "label": "Claude Code",
        "env": "CLAUDE_SKILLS_DIR",
        "relative": ".claude/skills",
        "marker": ".claude",
        "status": "官方用户级目录",
    },
    "codex": {
        "label": "OpenAI Codex",
        "env": "AGENT_SKILLS_DIR",
        "relative": ".agents/skills",
        "marker": ".codex",
        "status": "当前官方用户级目录",
    },
    "codex-legacy": {
        "label": "OpenAI Codex（旧目录）",
        "env": "CODEX_SKILLS_DIR",
        "relative": ".codex/skills",
        "marker": ".codex/skills",
        "status": "仅用于升级旧安装",
    },
    "workbuddy": {
        "label": "WorkBuddy",
        "env": "WORKBUDDY_SKILLS_DIR",
        "relative": ".workbuddy/skills",
        "marker": ".workbuddy",
        "status": "客户端兼容目录",
    },
    "qwen-office": {
        "label": "千问办公 / QwenWork",
        "env": "QWENWORK_SKILLS_DIR",
        "relative": ".qwenwork/skills",
        "marker": ".qwenwork",
        "status": "官方用户级目录",
    },
    "trae-work": {
        "label": "TRAE Work / TRAE CN",
        "env": "TRAE_SKILLS_DIR",
        "relative": ".trae-cn/skills",
        "marker": ".trae-cn",
        "status": "官方本地全局目录",
    },
    "trae-cli": {
        "label": "TraeCode CLI",
        "env": "TRAECLI_SKILLS_DIR",
        "relative": ".traecli/skills",
        "marker": ".traecli",
        "status": "官方 CLI 全局目录",
    },
    "dsh": {
        "label": "DeepSeek Harness (DSH)",
        "env": "DSH_SKILLS_DIR",
        "relative": ".dsh/skills",
        "marker": ".dsh",
        "status": "官方 DSH_HOME 技能目录",
    },
}

APP_ALIASES = {
    "claude": "claude-code",
    "claude-code": "claude-code",
    "codex": "codex",
    "codex-legacy": "codex-legacy",
    "workbuddy": "workbuddy",
    "qwen": "qwen-office",
    "qwenwork": "qwen-office",
    "qwen-office": "qwen-office",
    "trae": "trae-work",
    "trae-cn": "trae-work",
    "traework": "trae-work",
    "trae-work": "trae-work",
    "traecode": "trae-cli",
    "trae-cli": "trae-cli",
    "deepseek-harness": "dsh",
    "dsh": "dsh",
}


def inventory(directory):
    result = {}
    ignored = {"node_modules", "dist", "test-results", "playwright-report", "__pycache__", ".DS_Store"}
    for path in sorted(directory.rglob("*")):
        if ignored.intersection(path.relative_to(directory).parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("不安装符号链接: %s" % path)
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate_source(source):
    source = Path(source).resolve()
    release_path = source / "release.json"
    if not release_path.is_file():
        raise ValueError("完整发行包缺 release.json")
    release = json.loads(release_path.read_text(encoding="utf-8"))
    if not release.get("version"):
        raise ValueError("release.json 缺 version")
    declared = release.get("skills")
    if (
        not isinstance(declared, list)
        or not declared
        or any(not isinstance(name, str) or not re.fullmatch(r"product-[a-z0-9-]+", name) for name in declared)
        or len(declared) != len(set(declared))
    ):
        raise ValueError("release.json 的 skills 必须是非空、无重复的产品技能名称列表")
    actual = sorted(p.name for p in source.glob("product-*") if p.is_dir())
    missing = sorted(set(declared) - set(actual))
    extra = sorted(set(actual) - set(declared))
    if missing or extra:
        raise ValueError("发行清单与技能目录不一致：缺少 %s；未声明 %s" % (missing, extra))
    skills = [source / name for name in declared]
    for skill in skills:
        skill_file = skill / "SKILL.md"
        if not skill_file.is_file():
            raise ValueError("缺 SKILL.md: %s" % skill.name)
        content = skill_file.read_text(encoding="utf-8")
        match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.DOTALL)
        if not match:
            raise ValueError("SKILL.md 缺合法 YAML frontmatter: %s" % skill.name)
        frontmatter = match.group(1)
        name_match = re.search(r"^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", frontmatter, re.MULTILINE)
        if not name_match or name_match.group(1) != skill.name:
            raise ValueError("SKILL.md name 必须与目录名一致: %s" % skill.name)
        if not re.search(r"^description:\s*\S", frontmatter, re.MULTILINE):
            raise ValueError("SKILL.md 缺 description: %s" % skill.name)
    return source, skills, release


def stage_bundle(skills, stage):
    contents = {}
    for skill in skills:
        expected = inventory(skill)
        shutil.copytree(
            skill,
            stage / skill.name,
            ignore=shutil.ignore_patterns(
                "node_modules", "dist", "test-results", "playwright-report",
                "__pycache__", "*.pyc", ".DS_Store"
            ),
        )
        if inventory(stage / skill.name) != expected:
            raise ValueError("暂存校验失败: %s" % skill.name)
        contents[skill.name] = expected

    # 依赖安装也在暂存区完成，失败时不影响已安装版本。
    validators = stage / "product-workflow/validators"
    if (validators / "package-lock.json").is_file():
        result = subprocess.run(
            [
                "npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund",
                "--fetch-retries=0", "--fetch-timeout=30000",
                "--registry=https://registry.npmjs.org",
            ],
            cwd=validators,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode:
            raise ValueError("Mermaid 运行时暂存失败：" + result.stderr[-800:])
        probe = subprocess.run(
            ["node", "mermaid.mjs"],
            cwd=validators,
            input='["graph TD\\nA --> B"]',
            capture_output=True,
            text=True,
            timeout=60,
        )
        if probe.returncode or json.loads(probe.stdout) != [{"ok": True}]:
            raise ValueError("Mermaid 运行时自检失败")
        diagram_validators = stage / "product-diagram/validators"
        if diagram_validators.is_dir():
            shutil.copytree(validators / "node_modules", diagram_validators / "node_modules")
            render_probe = subprocess.run(
                ["node", "mermaid.mjs"],
                cwd=diagram_validators,
                input=json.dumps({
                    "action": "render",
                    "id": "install-probe",
                    "title": "安装检查",
                    "description": "检查图表运行时",
                    "text": "graph TD\nA --> B",
                }, ensure_ascii=False),
                capture_output=True,
                text=True,
                timeout=60,
            )
            try:
                render_result = json.loads(render_probe.stdout)
            except json.JSONDecodeError as error:
                raise ValueError("图表渲染运行时返回异常") from error
            if render_probe.returncode or not render_result.get("ok") or "<svg" not in render_result.get("svg", ""):
                raise ValueError("图表渲染运行时自检失败")
    return contents


def app_target(app, home=None, environ=None, platform_name=None):
    app = APP_ALIASES.get(app, app)
    if app not in APP_PROFILES:
        raise ValueError("不支持的客户端标识: %s" % app)
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    platform_name = sys.platform if platform_name is None else platform_name
    profile = APP_PROFILES[app]
    configured = environ.get(profile["env"])
    if configured:
        return Path(configured).expanduser()
    if app == "codex-legacy" and environ.get("CODEX_HOME"):
        return Path(environ["CODEX_HOME"]).expanduser() / "skills"
    if app == "dsh" and environ.get("DSH_HOME"):
        return Path(environ["DSH_HOME"]).expanduser() / "skills"
    return home / profile["relative"]


def detected_apps(home=None, environ=None, platform_name=None):
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    platform_name = sys.platform if platform_name is None else platform_name
    found = []
    for app, profile in APP_PROFILES.items():
        if app == "codex-legacy":
            continue
        marker = home / profile["marker"]
        if marker.exists() or environ.get(profile["env"]) or (app == "dsh" and environ.get("DSH_HOME")):
            found.append(app)
    return found


def resolve_targets(apps=None, targets=None, all_detected=False, home=None,
                    environ=None, platform_name=None):
    """Resolve and deduplicate client/custom targets without touching the filesystem."""
    apps = list(apps or [])
    targets = list(targets or [])
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    platform_name = sys.platform if platform_name is None else platform_name
    if all_detected:
        apps.extend(detected_apps(home, environ, platform_name))

    # Generic overrides count as an explicit destination choice.
    if not apps and not targets and not all_detected:
        generic = environ.get("AGENT_SKILLS_DIR") or environ.get("SKILLS_DIR")
        if generic:
            targets.append(generic)
        elif environ.get("WORKBUDDY_SKILLS_DIR"):
            targets.append(environ["WORKBUDDY_SKILLS_DIR"])

    candidates = []
    for requested in apps:
        app = APP_ALIASES.get(requested, requested)
        if app not in APP_PROFILES:
            raise ValueError("不支持的客户端标识: %s" % requested)
        candidates.append((APP_PROFILES[app]["label"], app_target(app, home, environ, platform_name)))
    candidates.extend(("自定义目录", Path(path).expanduser()) for path in targets)

    resolved = {}
    for label, path in candidates:
        key = str(path.resolve())
        if key in resolved:
            if label not in resolved[key][0]:
                resolved[key][0].append(label)
        else:
            resolved[key] = ([label], Path(key))
    return [(" + ".join(labels), path) for labels, path in resolved.values()]


def install(source, target, client="自定义目录"):
    source, skills, release = validate_source(source)
    target = Path(target).expanduser().resolve()
    for skill in skills:
        if (target / skill.name).is_symlink() or ((target / skill.name).exists() and not (target / skill.name).is_dir()):
            raise ValueError("目标技能必须为普通目录: %s" % skill.name)
    target.mkdir(parents=True, exist_ok=True)
    state = target / ".product-delivery"
    state.mkdir(exist_ok=True)
    lock = state / "install.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError("另一安装正在进行或遗留锁存在: %s" % lock)
    (lock / "pid").write_text(str(os.getpid()))
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    backup = state / "backups" / run_id
    committed, moved = [], []
    try:
        with tempfile.TemporaryDirectory(prefix="stage-", dir=state) as temp:
            stage = Path(temp)
            contents = stage_bundle(skills, stage)
            backup.mkdir(parents=True)
            manifest = {
                **release,
                "installed_at": run_id,
                "client": client,
                "target": str(target),
                "skills": contents,
            }
            staged_manifest = stage / "manifest.json"
            staged_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            current_manifest = state / "manifest.json"
            if current_manifest.exists():
                shutil.copy2(current_manifest, backup / "manifest.json")
            try:
                for skill in skills:
                    name = skill.name
                    if (target / name).exists():
                        os.replace(target / name, backup / name)
                        moved.append(name)
                    os.replace(stage / name, target / name)
                    committed.append(name)
                os.replace(staged_manifest, current_manifest)
            except BaseException:
                for name in reversed(committed):
                    shutil.rmtree(target / name)
                for name in reversed(moved):
                    os.replace(backup / name, target / name)
                raise
        print("已安装 %d 个技能到 %s（%s）；版本 %s" % (len(skills), target, client, release["version"]))
        print("版本与文件哈希: %s" % (state / "manifest.json"))
        print("旧版备份: %s" % backup)
        print("下一轮对话可使用；需要时重新打开对应 AI 助手的会话。")
    finally:
        shutil.rmtree(lock)


def export_packages(source, destination):
    """Build one root-SKILL.md ZIP per skill for clients that require UI import."""
    _, skills, release = validate_source(source)
    destination = Path(destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    packages = {}
    with tempfile.TemporaryDirectory(prefix="product-delivery-packages-") as temp:
        stage = Path(temp)
        stage_bundle(skills, stage)
        for skill in skills:
            output = destination / (skill.name + ".zip")
            temporary = destination / (".%s-%s.tmp" % (output.name, uuid.uuid4().hex))
            try:
                with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                    for path in sorted((stage / skill.name).rglob("*")):
                        if path.is_file():
                            archive.write(path, path.relative_to(stage / skill.name))
                digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
                os.replace(temporary, output)
            finally:
                if temporary.exists():
                    temporary.unlink()
            packages[output.name] = digest
    manifest = {
        **release,
        "format": "one-skill-per-zip; SKILL.md at archive root",
        "packages": packages,
    }
    (destination / "packages.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("已生成 %d 个客户端导入包到 %s；版本 %s" % (len(packages), destination, release["version"]))


def print_apps(home=None, environ=None, platform_name=None):
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    platform_name = sys.platform if platform_name is None else platform_name
    found = set(detected_apps(home, environ, platform_name))
    print("客户端标识\t默认目标\t检测\t说明")
    for app, profile in APP_PROFILES.items():
        detection = "不自动检测" if app == "codex-legacy" else ("已检测" if app in found else "未检测")
        print("%s\t%s\t%s\t%s" % (
            app,
            app_target(app, home, environ, platform_name),
            detection,
            profile["status"],
        ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app",
        action="append",
        choices=sorted(APP_ALIASES),
        help="客户端；可重复指定。必须由用户显式选择",
    )
    parser.add_argument("--target", action="append", help="自定义技能根目录；可重复指定")
    parser.add_argument("--all-detected", action="store_true", help="安装到本机检测到的全部受支持客户端")
    parser.add_argument("--list-apps", action="store_true", help="列出客户端、默认目录和检测状态后退出")
    parser.add_argument("--dry-run", action="store_true", help="只显示将写入的目录")
    parser.add_argument(
        "--export-packages",
        metavar="DIR",
        help="生成逐技能 ZIP，供支持客户端界面导入",
    )
    args = parser.parse_args()
    try:
        if args.list_apps:
            print_apps()
            return
        source = Path(__file__).resolve().parents[1]
        if args.export_packages:
            if args.dry_run:
                print("将生成客户端导入包: %s" % Path(args.export_packages).expanduser().resolve())
            else:
                export_packages(source, args.export_packages)
        should_install = bool(args.app or args.target or args.all_detected or not args.export_packages)
        if not should_install:
            return
        destinations = resolve_targets(args.app, args.target, args.all_detected)
        if not destinations:
            if args.all_detected:
                raise ValueError("没有检测到受支持客户端；请使用 --app 或 --target 指定目标")
            raise ValueError("未指定安装目标；请先运行 --list-apps，再使用 --app 或 --target")
        if args.dry_run:
            for client, target in destinations:
                print("将安装到 %s: %s" % (client, target))
            return
        failures = []
        for client, target in destinations:
            try:
                install(source, target, client)
            except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                failures.append("%s (%s): %s" % (client, target, error))
        if failures:
            raise ValueError("以下目标安装失败：\n- " + "\n- ".join(failures))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, "安装失败: %s\n" % error)


if __name__ == "__main__":
    main()
