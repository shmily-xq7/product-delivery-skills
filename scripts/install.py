"""Stage and verify the complete skill bundle before replacing installed directories."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid


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


def install(source, target):
    source, target = Path(source).resolve(), Path(target).expanduser().resolve()
    skills = sorted(p for p in source.glob("product-*") if p.is_dir())
    if len(skills) != 11:
        raise ValueError("完整发行包应包含 11 个技能")
    for skill in skills:
        if not (skill / "SKILL.md").is_file():
            raise ValueError("缺 SKILL.md: %s" % skill.name)
        if (target / skill.name).is_symlink() or ((target / skill.name).exists() and not (target / skill.name).is_dir()):
            raise ValueError("目标技能必须为普通目录: %s" % skill.name)
    release = json.loads((source / "release.json").read_text(encoding="utf-8"))
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
            contents = {}
            for skill in skills:
                expected = inventory(skill)
                shutil.copytree(skill, stage / skill.name, ignore=shutil.ignore_patterns("node_modules", "dist", "test-results", "playwright-report", "__pycache__", "*.pyc", ".DS_Store"))
                if inventory(stage / skill.name) != expected:
                    raise ValueError("暂存校验失败: %s" % skill.name)
                contents[skill.name] = expected
            # Dependency installation is staged too: failure leaves the installed bundle intact.
            validators = stage / 'product-workflow/validators'
            if (validators / 'package-lock.json').is_file():
                result = subprocess.run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund', '--fetch-retries=0', '--fetch-timeout=30000', '--registry=https://registry.npmjs.org'], cwd=validators, capture_output=True, text=True, timeout=300)
                if result.returncode:
                    raise ValueError('Mermaid 运行时暂存失败：' + result.stderr[-800:])
                probe = subprocess.run(['node', 'mermaid.mjs'], cwd=validators, input='["graph TD\\nA --> B"]', capture_output=True, text=True, timeout=60)
                if probe.returncode or json.loads(probe.stdout) != [{'ok': True}]:
                    raise ValueError('Mermaid 运行时自检失败')
            backup.mkdir(parents=True)
            manifest = {**release, "installed_at": run_id, "target": str(target), "skills": contents}
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
        print("已安装 %d 个技能到 %s；版本 %s" % (len(skills), target, release["version"]))
        print("版本与文件哈希: %s" % (state / "manifest.json"))
        print("旧版备份: %s" % backup)
        print("下一轮对话可使用；需要时重新打开对应 AI 助手的会话。")
    finally:
        shutil.rmtree(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", choices=["codex", "workbuddy"], default="codex")
    parser.add_argument("--target", help="覆盖安装目标；其次兼容 SKILLS_DIR / WORKBUDDY_SKILLS_DIR")
    args = parser.parse_args()
    default = (Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
               if args.app == "codex" else Path.home() / ".workbuddy" / "skills")
    target = args.target or os.environ.get("SKILLS_DIR") or os.environ.get("WORKBUDDY_SKILLS_DIR") or default
    try:
        install(Path(__file__).resolve().parents[1], target)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, "安装失败: %s\n" % error)


if __name__ == "__main__":
    main()
