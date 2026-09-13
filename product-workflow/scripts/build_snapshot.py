"""Generate a self-contained review copy without editing maintained source documents."""
import argparse
import hashlib
from pathlib import Path
from workflow_config import load_config, local_path, source_refs, read_source


def build(root, module, output):
    cfg = load_config(root)
    refs = source_refs(cfg, module)
    if not refs:
        raise ValueError("请先在 module_sources 声明模块的两个上游章节")
    source = local_path(root, module)
    destination = local_path(root, output)
    inputs = [source] + [local_path(root, ref.split("#sections=", 1)[0]) for ref, _ in refs]
    if destination in inputs or destination.exists():
        raise ValueError("快照输出必须是新的文件，不能覆盖来源或既有快照")
    content = ["> 自动生成的评审快照；维护源文档，按需重新生成。\n", source.read_text(encoding="utf-8")]
    for ref, _ in refs:
        text = read_source(root, ref)
        digest = hashlib.sha256(text.encode()).hexdigest()
        content.extend(["\n---\n", "来源：`%s`；sha256：`%s`\n" % (ref, digest), text])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as file:
        file.write("\n".join(content))
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--module", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        print(build(args.project_root, args.module, args.output))
    except (ValueError, OSError) as error:
        parser.exit(2, "ERROR: %s\n" % error)
