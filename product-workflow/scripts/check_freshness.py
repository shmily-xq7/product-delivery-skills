#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产物来源检查与结项：完整正文 SHA256，显式章节切片，缺失/未知阻断。
正文变化意味着需要复核，不代表必须重写。--stamp 仅应在完成来源复核后使用。
代码/测试证据由 run_checks.py 绑定当前输入，结项复用有效证据。
"""

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

from workflow_config import load_config, document_paths, source_refs, read_source, spec_files
from delivery_evidence import approval, has_source, required_checks, current_evidence, executed_coverage

# ---------------------------------------------------------------- 常量

META_MARK = "**生成元信息**"
META_TITLE = "> **生成元信息**（由流程写入，请勿手工修改）"

AC_RE = re.compile(r"AC-[A-Z][A-Z0-9]{1,7}-[0-9]{2}")
TABLE_NAME_RE = re.compile(r"表名\s*[:：]\s*(.+?)\s*$")
ENDPOINT_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_\-/{}.:]+)")
TABLE_SEP_RE = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")
ANY_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*```\s*([A-Za-z0-9_+-]*)\s*$")

REQ_PATH = os.path.join("项目战略规划", "原始需求.md")
EXEC_DIR = "项目战术执行"
DESIGN_DOC = "00_产品设计文档.md"
ARCH_DOC = "00_功能架构设计文档.md"
MODULE_DOC_RE = re.compile(r"^\d{2}_.+详细设计\.md$")

# 产物陈旧 → 从哪个阶段开始按序重跑
BACKFLOW = {
    "design_doc": ["product-design", "product-architecture", "product-module-design",
                   "product-development", "product-e2e-test"],
    "arch_doc": ["product-architecture", "product-module-design",
                 "product-development", "product-e2e-test"],
    "module_doc": ["product-module-design", "product-development", "product-e2e-test"],
}
STAGE_OF = {
    "raw": "（人写）",
    "design_doc": "product-design",
    "arch_doc": "product-architecture",
    "module_doc": "product-module-design",
}


class Finding:
    def __init__(self, level, code, message, detail=None):
        self.level = level          # STALE / OK / WARN / SKIP
        self.code = code
        self.message = message
        self.detail = detail or []

    def as_dict(self):
        return {"level": self.level, "code": self.code,
                "message": self.message, "detail": self.detail}


# ---------------------------------------------------------------- 基础

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def sha12(s):
    data = s if isinstance(s, bytes) else s.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:12]


def strip_fences(text):
    out, lines = [], text.split("\n")
    i = 0
    while i < len(lines):
        if FENCE_RE.match(lines[i]):
            i += 1
            while i < len(lines) and not FENCE_RE.match(lines[i]):
                i += 1
            i += 1
        else:
            out.append(lines[i]); i += 1
    return "\n".join(out)


def clean_name(raw):
    return re.sub(r"^[*`\s]+|[*`\s]+$", "", raw.strip())


def page_names(plain):
    """从「页面清单」表取第一列"""
    lines = plain.split("\n")
    start = None
    for i, l in enumerate(lines):
        m = ANY_HEADING_RE.match(l)
        if m and "页面清单" in m.group(2):
            start = i + 1
            break
    if start is None:
        return []
    end = len(lines)
    for i in range(start, len(lines)):
        if ANY_HEADING_RE.match(lines[i]):
            end = i
            break
    seg = lines[start:end]
    hdr = None
    for i, l in enumerate(seg):
        if TABLE_SEP_RE.match(l) and i > 0 and seg[i - 1].strip().startswith("|"):
            hdr = i - 1
            break
    if hdr is None:
        return []
    names = []
    for l in seg[hdr + 2:]:
        if not l.strip().startswith("|"):
            break
        if TABLE_SEP_RE.match(l):
            continue
        first = clean_name(l.strip().strip("|").split("|")[0])
        if first:
            names.append(first)
    return names


def table_names(plain):
    return [clean_name(m.group(1)) for m in (TABLE_NAME_RE.search(l) for l in plain.split("\n")) if m]


def endpoints(plain):
    return ["%s %s" % (m.group(1), m.group(2)) for m in ENDPOINT_RE.finditer(plain)]


# ---------------------------------------------------------------- 契约与指纹

def extract_contract(path, role):
    """返回 {集合名: 排序后的列表}；提取不到就返回空 dict"""
    plain = strip_fences(read_text(path))
    sets = {}

    if role == "design_doc":
        v = sorted(set(page_names(plain)))
        if v:
            sets["页面名"] = v
    if role in ("design_doc", "module_doc"):
        v = sorted(set(AC_RE.findall(plain)))
        if v:
            sets["AC"] = v
    if role == "arch_doc":
        v = sorted(set(table_names(plain)))
        if v:
            sets["表名"] = v
    if role in ("arch_doc", "module_doc"):
        v = sorted(set(endpoints(plain)))
        if v:
            sets["endpoint"] = v
    return sets


def normalized_content(text):
    # Exclude only the tool-owned metadata block; keep rule text, types, SQL, AC details.
    lines = text.replace('\r\n', '\n').split('\n')
    _, span = parse_meta(text)
    if span:
        del lines[span[0]:span[1]]
    return '\n'.join(line.rstrip() for line in lines).strip() + '\n'


def content_hash(text):
    content = normalized_content(text)
    return 'sha256:' + hashlib.sha256(content.encode('utf-8')).hexdigest() if content.strip() else None


def fingerprint(path, role):
    text = read_text(path)
    if role == 'raw':
        with open(path, 'rb') as stream:
            data = stream.read()
        return ('sha256:' + hashlib.sha256(data).hexdigest() if data.strip() else None), {}
    return content_hash(text), extract_contract(path, role)


# ---------------------------------------------------------------- 产物发现

def source_fingerprint(root, reference, role):
    if "#sections=" in reference:
        text = read_source(root, reference)
        return content_hash(text), {"章节": reference.split("#sections=", 1)[1].split(",")}
    return fingerprint(os.path.join(root, reference), role)


def discover(project_root):
    """返回 [(绝对路径, 相对路径, role, [(上游相对路径, 上游role)])]"""
    out = []
    cfg = load_config(project_root)
    paths = cfg["paths"]
    docs = document_paths(cfg)
    req_rel = paths["requirement"]
    req = os.path.join(project_root, req_rel)
    ex = os.path.join(project_root, paths["execution"])
    design = os.path.join(project_root, docs["design"])
    arch = os.path.join(project_root, docs["architecture"])

    design_up = [(req_rel, "raw")]
    arch_up = [(docs["design"], "design_doc")]
    mod_up = [(docs["design"], "design_doc"),
              (docs["architecture"], "arch_doc")]

    if os.path.isfile(design):
        out.append((design, docs["design"], "design_doc", design_up))
    if os.path.isfile(arch):
        out.append((arch, docs["architecture"], "arch_doc", arch_up))
    for p in sorted(glob.glob(os.path.join(ex, "*详细设计.md"))):
        base = os.path.basename(p)
        if MODULE_DOC_RE.match(base):
            rel = os.path.join(paths["execution"], base)
            out.append((p, rel, "module_doc", source_refs(cfg, rel) or mod_up))
    return out


# ---------------------------------------------------------------- 元信息块

def parse_meta(text):
    """返回 ([(上游路径, 指纹串, 计数串)], 块起止行号) 或 (None, None)"""
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if l.strip().startswith("> **生成元信息**"):
            refs = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith(">"):
                for m in re.finditer(r"`([^`]+)`\s*@\s*`((?:fp|sha256):[0-9a-f]+)`(?:（([^）]*)）)?", lines[j]):
                    refs.append((m.group(1), m.group(2), m.group(3) or ""))
                j += 1
            return refs, (i, j)
    return None, None


def render_meta(entries):
    """entries: [(上游相对路径, 指纹串, 计数串)]"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [META_TITLE, "> 基于："]
    for path, fp, counts in entries:
        suffix = "（%s）" % counts if counts else ""
        lines.append("> - `%s` @ `%s`%s" % (path, fp, suffix))
    lines.append("> 生成于：%s" % now)
    return lines


def write_meta(path, entries):
    text = read_text(path)
    lines = text.split("\n")
    old, span = parse_meta(text)
    block = render_meta(entries)

    if span:
        lines[span[0]:span[1]] = block
    else:
        # 插到文件最开头（若有 YAML frontmatter 则紧随其后）
        insert_at = 0
        if lines and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    insert_at = i + 1
                    break
        lines[insert_at:insert_at] = block + [""]

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return bool(old)


# ---------------------------------------------------------------- 检查

def counts_str(sets):
    if not sets:
        return ""
    return " · ".join("%s %d" % (k, len(v)) for k, v in sorted(sets.items()))


def evaluate(project_root):
    """返回 [{path, role, status, details, backflow}]；status: OK / STALE / UNMARKED

    体检与结项（--finalize）共用这一份评估，避免两处逻辑漂移。
    """
    out = []
    for abs_p, rel_p, role, upstreams in discover(project_root):
        refs, _span = parse_meta(read_text(abs_p))

        if refs is None:
            out.append({"path": rel_p, "role": role, "status": "UNMARKED",
                        "details": ["没有「生成元信息」块 —— 无法判定是否陈旧",
                                    "复核当前来源后才可 --stamp；盖章不证明已完成业务审查"],
                        "backflow": []})
            continue

        recorded = {p: (fp, c) for p, fp, c in refs}
        stale_ups, details = [], []
        for up_rel, up_role in upstreams:
            up_abs = os.path.join(project_root, up_rel.split("#sections=", 1)[0])
            if not os.path.isfile(up_abs):
                stale_ups.append(up_rel)
                details.append("上游不存在：%s" % up_rel)
                continue
            if up_rel not in recorded:
                stale_ups.append(up_rel)
                details.append("新增上游依赖：%s（产物未记录它）" % up_rel)
                continue
            try:
                cur_fp, cur_sets = source_fingerprint(project_root, up_rel, up_role)
            except (ValueError, OSError) as error:
                stale_ups.append(up_rel)
                details.append(str(error))
                continue
            if cur_fp is None:
                stale_ups.append(up_rel)
                details.append("上游为空，无法提取指纹：%s" % up_rel)
                continue
            if cur_fp != recorded[up_rel][0]:
                stale_ups.append(up_rel)
                old_c, new_c = recorded[up_rel][1], counts_str(cur_sets)
                d = "上游变更：%s\n            指纹 %s -> %s" % (up_rel, recorded[up_rel][0], cur_fp)
                if old_c or new_c:      # 整文件哈希的边没有集合，不打这行
                    d += "\n            集合 %s -> %s" % (old_c or "(未记录)", new_c or "(空)")
                details.append(d)

        out.append({"path": rel_p, "role": role,
                    "status": "STALE" if stale_ups else "OK",
                    "details": details,
                    "backflow": BACKFLOW.get(role, []) if stale_ups else []})
    # Full edges propagate every unresolved upstream review. Explicit slices isolate
    # content-only changes; missing/unmarked baseline provenance always propagates.
    graph = {rel: ups for _, rel, _, ups in discover(project_root)}
    seen = {}
    for row in out:
        structural = row['status'] == 'UNMARKED' or any('不存在' in d or '为空' in d for d in row['details'])
        if row['role'] == 'design_doc' and row['status'] != 'OK':
            structural = True
        for reference, _ in graph[row['path']]:
            upstream = seen.get(reference.split('#sections=', 1)[0])
            if upstream and upstream['status'] != 'OK' and ('#sections=' not in reference or upstream['chain_blocked']):
                row['status'] = 'STALE'
                row['details'].append('上游来源链尚未复核：' + upstream['path'])
                row['backflow'] = BACKFLOW.get(row['role'], [])
                structural = structural or upstream['chain_blocked']
        row['chain_blocked'] = structural
        seen[row['path']] = row
    return out



def check_one(project_root):
    findings = []
    rows = evaluate(project_root)
    if not rows:
        cfg = load_config(project_root)
        docs = document_paths(cfg)
        findings.append(Finding(
            "WARN", "F-EMPTY",
            "未发现工作流产物，当前项目尚未初始化或项目路径/配置不正确",
            ["检查路径：%s" % os.path.abspath(project_root),
             "产品设计：%s" % docs["design"],
             "功能架构：%s" % docs["architecture"],
             "模块目录：%s" % cfg["paths"]["execution"],
             "请先确认 --project-root 与 product-workflow.json；没有产物不等于全部正常"]
        ))
        return findings
    for r in rows:
        if r["status"] == "UNMARKED":
            findings.append(Finding("WARN", "F0",
                                    "%s 没有「生成元信息」块 —— 无法判定是否陈旧" % r["path"],
                                    r["details"]))
        elif r["status"] == "STALE":
            detail = list(r["details"])
            if r["backflow"]:
                detail.append("建议回流：%s" % " → ".join(r["backflow"]))
            findings.append(Finding("STALE", "F2", "%s 疑似陈旧（上游已变）" % r["path"], detail))
        else:
            findings.append(Finding("OK", "F3", "%s 与其上游一致" % r["path"]))
    return findings


# ---------------------------------------------------------------- 结项（--finalize）

DELIVERY_NAME = "99_交付清单.md"


def sibling_script(parts):
    """按安装位置推导同族 skill 的脚本路径；找不到返回 None（单独安装时优雅降级）"""
    skills_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p = os.path.join(skills_dir, *parts)
    return p if os.path.isfile(p) else None


def _run_json(cmd):
    """Malformed output or a failed process can never become PASS."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        data = json.loads(result.stdout)
        if not isinstance(data, list) or not data:
            return None
        if any(not isinstance(row, dict) or any(type(row.get(k)) is not int or row[k] < 0 for k in ('fail', 'warn')) for row in data):
            return None
        if result.returncode != 0 and not any(row['fail'] for row in data):
            return None
        return data
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def run_gates(root, in_scope=None):
    """跑各阶段校验器，返回 [(阶段, 脚本名, 判定, 明细)]

    in_scope：交付范围覆盖的阶段 token 集合（None = 不限制）。
    范围外的阶段**不跑**；其产物若存在，会在交付清单里单独提示「超出范围」。"""
    cfg = load_config(root)
    paths = cfg["paths"]
    ex = os.path.join(root, paths["execution"])
    design = os.path.join(ex, paths["design_name"])
    arch = os.path.join(ex, paths["architecture_name"])
    results = []
    _tok = lambda t: in_scope is None or t in in_scope

    def run(stage, parts, args, label):
        script = sibling_script(parts)
        if not script:
            results.append((stage, label, "未检测", "未找到校验器脚本")); return
        data = _run_json([sys.executable, script] + args + ["--json"])
        if data is None:
            results.append((stage, label, "未检测", "运行失败或未输出 JSON")); return
        fails = sum(d.get("fail", 0) for d in data)
        warns = sum(d.get("warn", 0) for d in data)
        results.append((stage, label,
                        "FAIL" if fails else ("PASS(WARN)" if warns else "PASS"),
                        "FAIL=%d WARN=%d" % (fails, warns)))

    extra_design = ["--design-doc", design] if os.path.isfile(design) else []
    if _tok("design") and os.path.isfile(design):
        run("① 产品设计", ("product-design", "scripts", "validate_design_doc.py"),
            ["--doc", design], "validate_design_doc.py")
    if _tok("arch") and os.path.isfile(arch):
        run("② 功能架构", ("product-architecture", "scripts", "validate_arch_doc.py"),
            ["--arch-doc", arch] + extra_design, "validate_arch_doc.py")
    mods = sorted(p for p in glob.glob(os.path.join(ex, "*详细设计.md"))
                  if MODULE_DOC_RE.match(os.path.basename(p)))
    if _tok("module") and mods:
        run("③ 模块详细设计", ("product-module-design", "scripts", "validate_module_doc.py"),
            ["--module-doc"] + mods + extra_design, "validate_module_doc.py")
    e2e_dir = os.path.join(root, paths["e2e"])
    if _tok("e2e") and os.path.isdir(e2e_dir) and os.path.isfile(design):
        run("⑤ E2E 测试", ("product-e2e-test", "scripts", "validate_e2e_spec.py"),
            ["--design-doc", design, "--spec-dir", e2e_dir, "--extensions"] + cfg["spec_extensions"], "validate_e2e_spec.py")
    expected = {'design': '① 产品设计', 'arch': '② 功能架构', 'module': '③ 模块详细设计', 'e2e': '⑤ E2E 测试'}
    for token, label in expected.items():
        if _tok(token) and not any(row[0] == label for row in results):
            results.append((label, '必需产物', '未检测', 'MISSING：范围内产物缺失'))
    return results


def ac_coverage(root):
    """返回 (设计定义的 AC, 模块文档承载的 AC, E2E 用例引用的 AC)"""
    cfg = load_config(root)
    paths = cfg["paths"]
    ex = os.path.join(root, paths["execution"])
    design = os.path.join(ex, paths["design_name"])
    design_ac = set(AC_RE.findall(strip_fences(read_text(design)))) if os.path.isfile(design) else set()
    module_ac = set()
    for p in glob.glob(os.path.join(ex, "*详细设计.md")):
        if MODULE_DOC_RE.match(os.path.basename(p)):
            from strict_docs import sections
            for heading, body in sections(strip_fences(read_text(p))):
                if '覆盖的 AC' in heading or '覆盖的AC' in heading:
                    module_ac |= set(AC_RE.findall(body))
    e2e_ac = set()
    for p in (spec_files(os.path.join(root, paths["e2e"]), cfg["spec_extensions"]) or []):
        e2e_ac |= set(AC_RE.findall(read_text(p)))
    return design_ac, module_ac, e2e_ac


def collect_unresolved(root):
    from issue_ledger import collect
    return collect(root, load_config(root))


# 交付范围声明（写在 原始需求.md 头部；缺省全链，向后兼容）
SCOPE_LINE_RE = re.compile(r"交付范围\s*[:：]\s*([^\s*`>#。；]+)")
DEFAULT_SCOPE = "全链"
SCOPE_LEVELS = {
    "产品设计": ("design",),
    "设计到模块": ("design", "arch", "module"),
    "全链": ("design", "arch", "module", "dev", "e2e"),
}
GATE_STAGE_TOKEN = {"①": "design", "②": "arch", "③": "module", "⑤": "e2e"}


def parse_scope(root):
    """从 原始需求.md 解析「交付范围」声明，返回 (范围值, 说明文字)。

    缺文件 / 未声明 / 值非法 → 默认「全链」（向后兼容：不声明的老项目行为不变）。"""
    p = os.path.join(root, load_config(root)["paths"]["requirement"])
    if not os.path.isfile(p):
        return DEFAULT_SCOPE, "未找到 `原始需求.md`，按默认范围**全链**判定"
    m = SCOPE_LINE_RE.search(read_text(p))
    if not m:
        return DEFAULT_SCOPE, "未声明交付范围，按默认**全链**判定"
    val = m.group(1).strip().strip("。；;，,")
    val = {"仅需求分析": "产品设计"}.get(val, val)
    if val not in SCOPE_LEVELS:
        return DEFAULT_SCOPE, ("交付范围「%s」无法识别（可选：%s），按默认**全链**判定"
                               % (val, " / ".join(SCOPE_LEVELS)))
    return val, "交付范围：**%s**" % val


def finalize(root, out_path=None):
    """Fail closed: inventory, provenance, static gates and saved runtime evidence."""
    cfg = load_config(root)
    paths = cfg['paths']
    ex = os.path.join(root, paths['execution'])
    out_path = out_path or os.path.join(ex, DELIVERY_NAME)
    scope, scope_note = parse_scope(root)
    tokens = SCOPE_LEVELS[scope]
    checks = []
    def check(name, ok, note):
        checks.append((name, bool(ok), str(note)))
    docs = document_paths(cfg)
    required = [paths['requirement'], docs['design']]
    if 'arch' in tokens:
        required.append(docs['architecture'])
    for name in required:
        p = os.path.join(root, name)
        check('必需文档 ' + name, os.path.isfile(p) and bool(read_text(p).strip()), '必须存在且非空')
    req = os.path.join(root, paths['requirement'])
    value = SCOPE_LINE_RE.search(read_text(req)) if os.path.isfile(req) else None
    check('交付范围明确', bool(value) and value.group(1).strip('。；;，,') in tuple(SCOPE_LEVELS) + ('仅需求分析',), scope_note)
    ok, note = approval(root, cfg)
    check('需求经人工确认', ok, note)
    freshness = evaluate(root)
    roles = {'design_doc': 'design', 'arch_doc': 'arch', 'module_doc': 'module'}
    relevant = [row for row in freshness if roles[row['role']] in tokens]
    if 'module' in tokens:
        check('至少一份模块详细设计', any(row['role'] == 'module_doc' for row in relevant), '模块覆盖由 AC 检查继续约束')
    for row in relevant:
        check('来源 ' + row['path'], row['status'] == 'OK', row['status'] + ': ' + '; '.join(row['details']))
    exemptions = cfg['exemptions']
    if 'dev' in tokens:
        for side in ('frontend', 'backend'):
            check(side + ' 实际源码', side in exemptions or has_source(root, paths[side]), exemptions.get(side, '空目录、依赖目录不能作为源码'))
        check('至少一端实际源码', any(has_source(root, paths[s]) for s in ('frontend', 'backend') if s not in exemptions), '不可豁免全部实现')
        for name in required_checks(cfg):
            evidence, note = current_evidence(root, cfg, name)
            check('运行检查 ' + name, evidence is not None, note)
    gate_tokens = tuple(t for t in tokens if t != 'e2e' or 'e2e' not in exemptions)
    gates = run_gates(root, gate_tokens)
    for stage, label, verdict, note in gates:
        check(stage + ' ' + label, verdict in ('PASS', 'PASS(WARN)'), verdict + ': ' + note)
    design_ac, module_ac, spec_ac = ac_coverage(root)
    if 'module' in tokens:
        check('模块 AC 覆盖', bool(design_ac) and design_ac <= module_ac and not module_ac - design_ac,
              '缺失：%s；悬空：%s' % (sorted(design_ac - module_ac), sorted(module_ac - design_ac)))
    if 'dev' in tokens:
        covered, problems = executed_coverage(root, cfg)
        check('AC 实际执行覆盖（单元/API/E2E）', bool(design_ac) and design_ac <= covered and not covered - design_ac and not problems,
              '未覆盖：%s；悬空：%s；异常：%s' % (sorted(design_ac-covered), sorted(covered-design_ac), problems))
    unresolved = collect_unresolved(root)
    check('无遗留阻断项', not unresolved, unresolved or '无')
    ready = all(ok for _, ok, _ in checks)
    lines = ['# 交付清单', '', '**范围**：' + scope_note,
             '**结论**：' + ('就绪' if ready else '未就绪'), '',
             '> 自动生成。静态规则与本地执行证据不能证明业务语义完全正确。', '',
             '| 条件 | 结果 | 说明 |', '|---|---|---|']
    for name, ok, note in checks:
        lines.append('| %s | %s | %s |' % (name, '通过' if ok else '**未通过**', note.replace('|', '／').replace('\n', '<br>')))
    if exemptions:
        lines += ['', '## 明确豁免', ''] + ['- %s：%s' % item for item in exemptions.items()]
    lines += ['', '证据失效仅表示需要复核；确认影响范围后再决定更新产物或重跑检查。',
              '环境、工具链或外部服务变化时，请使用 run_checks.py --force 重新执行。']
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as stream:
        stream.write('\n'.join(lines) + '\n')
    return out_path, ready, '就绪' if ready else '未就绪（%d 项待处理）' % sum(not ok for _, ok, _ in checks)


# ---------------------------------------------------------------- 输出

def render(findings):
    lines = ["=" * 72, "产物陈旧检测", "=" * 72]
    for f in findings:
        lines.append("  [%s] %s" % (f.level, f.message))
        for d in f.detail:
            lines.append("           %s" % d)
    n_stale = sum(1 for f in findings if f.level == "STALE")
    n_warn = sum(1 for f in findings if f.level == "WARN")
    uninitialized = any(f.code == "F-EMPTY" for f in findings)
    verdict = "UNINITIALIZED" if uninitialized else ("STALE" if n_stale else ("OK(WARN)" if n_warn else "OK"))
    lines.append("  --> 结论: %s  (STALE=%d WARN=%d)" % (verdict, n_stale, n_warn))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="产物陈旧检测器（链级）")
    ap.add_argument("--project-root", default=".", help="项目根目录（默认当前目录）")
    ap.add_argument("--stamp", nargs="+", help="给这些产物写入/更新「生成元信息」块")
    ap.add_argument("--finalize", action="store_true", help="生成结项交付清单（99_交付清单.md）")
    ap.add_argument("--finalize-path", default=None,
                    help="交付清单输出路径（默认 <项目根>/项目战术执行/99_交付清单.md）")
    ap.add_argument("--json", action="store_true", help="输出机读 JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    ap.add_argument("--strict", action="store_true",
                    help="WARN（含未初始化）也返回非零；用于 CI 或自动化检查")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)

    if args.finalize:
        path, ready, summary = finalize(root, args.finalize_path)
        print("已生成：%s" % path)
        print("结项结论：%s" % summary)
        return 0 if ready else 1

    if args.stamp:
        planned = []
        artifacts = {os.path.abspath(p): (rel, role, ups)
                     for p, rel, role, ups in discover(root)}
        for target in args.stamp:
            abs_t = os.path.abspath(target if os.path.isabs(target) else os.path.join(root, target))
            if not os.path.isfile(abs_t) or abs_t not in artifacts:
                raise ValueError("盖章目标不存在或不在产物依赖图: %s" % target)
            rel, role, upstreams = artifacts[abs_t]
            if not upstreams:
                raise ValueError("产物缺少必需来源，不能盖空章: %s" % rel)
            entries = []
            for up_rel, up_role in upstreams:
                fp, sets = source_fingerprint(root, up_rel, up_role)
                if fp is None:
                    raise ValueError("无法提取来源指纹: %s" % up_rel)
                entries.append((up_rel, fp, counts_str(sets)))
            planned.append((abs_t, rel, entries))
        for abs_t, rel, entries in planned:
            updated = write_meta(abs_t, entries)
            print("%s %s（%d 条上游）" % ("UPDATED" if updated else "STAMPED", rel, len(entries)))
        return 0

    findings = check_one(root)
    if args.json:
        print(json.dumps([f.as_dict() for f in findings], ensure_ascii=False, indent=2))
    elif args.quiet:
        n_stale = sum(1 for f in findings if f.level == "STALE")
        n_warn = sum(1 for f in findings if f.level == "WARN")
        uninitialized = any(f.code == "F-EMPTY" for f in findings)
        verdict = "UNINITIALIZED" if uninitialized else ("STALE" if n_stale else ("OK(WARN)" if n_warn else "OK"))
        print("%s  (STALE=%d WARN=%d)" % (verdict,
                                          n_stale, n_warn))
    else:
        print(render(findings))

    blocking = any(f.level == "STALE" for f in findings)
    if args.strict:
        blocking = blocking or any(f.level == "WARN" for f in findings)
    return 1 if blocking else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print("ERROR: %s" % error, file=sys.stderr)
        sys.exit(2)
