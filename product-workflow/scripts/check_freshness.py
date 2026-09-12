#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_freshness.py —— 产物陈旧检测器（链级）

解决一个静默失效问题：**上游改了，下游产物还是按旧版做的，而且没有任何症状**。
本脚本用「来源指纹」把上下游锁在一起 —— 只要上游的**契约**变了，下游就会被判陈旧。

## 分层指纹（关键设计：灵敏度要等于"实质变更"）

| 上游类型 | 指纹方式 | 为什么 |
|---|---|---|
| `原始需求.md`（人写的自由文本） | **整文件 sha256** | 需求一变本就该重审全链，这条边上"过度敏感"反而是对的 |
| 产品设计文档 / 功能架构文档 / 模块详细设计 | **契约指纹** | 改错别字不该牵动下游；而**集合变化**（新增页面、改 AC、加表、加接口）必须牵动 |

契约指纹 = 从上游文件里提取这些集合 → 排序 → 序列化 → sha256 前 12 位：
- **AC 编号集合**（`AC-XXX-01`）
- **页面名集合**（「页面清单」表第一列）
- **表名集合**（`表名: xxx`）
- **endpoint 集合**（`POST /api/v1/...`）

**提取到哪些就用哪些**——某类元素在该文件里不存在就跳过，不会因此报错。

## 依赖图（谁能被谁作废）

    项目战略规划/原始需求.md            （人写，无元信息块）
        └─▶ 00_产品设计文档.md
                ├─▶ 00_功能架构设计文档.md
                └─▶ <序号>_<模块名>详细设计.md  ◀─┐
                                                    │ 同时依赖
                    00_功能架构设计文档.md ──────────┘

**代码与 E2E 用例不单独标记**：往源码里塞哈希会污染代码。它们由"最近的陈旧上游"**推导**——
只要③陈旧了，④⑤自然该按序重跑。

## 用法

    # 1) 阶段产出后盖章（写入/更新产物头部的「生成元信息」块）
    python3 check_freshness.py --stamp 项目战术执行/00_功能架构设计文档.md

    # 2) 随时体检（默认动作）
    python3 check_freshness.py --project-root <项目根>
    python3 check_freshness.py --project-root <项目根> --json | --quiet

    # 3) 结项：生成交付清单（含门禁结果 + AC 覆盖汇总 + 遗留项）
    python3 check_freshness.py --finalize --project-root <项目根>

**交付范围（部分交付）**：在 `项目战略规划/原始需求.md` 顶部写一行

    交付范围：仅需求分析    ← 只到 ① 产品设计文档
    交付范围：设计到模块    ← 到 ①②③（全部设计文档，不含代码）
    交付范围：全链          ← 缺省值；不声明即按全链判定（老项目行为不变）

`--finalize` 按声明裁剪结项条件：范围外阶段标「不在本次交付范围」不计入就绪；
范围外**产物若存在**会提示「超出范围」（不阻断）。体检（陈旧检测）不受范围影响。

退出码: 0 = 无陈旧（或结项就绪）；1 = 存在陈旧（或结项未就绪）；2 = 用法错误
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


def fingerprint(path, role):
    """返回 (指纹串, 集合dict)。原始需求用整文件哈希；其余用契约指纹。"""
    if role == "raw":
        with open(path, "rb") as fh:
            return "sha256:" + sha12(fh.read()), {}
    sets = extract_contract(path, role)
    if not sets:
        return None, {}
    payload = json.dumps(sets, ensure_ascii=False, sort_keys=True)
    return "fp:" + sha12(payload), sets


# ---------------------------------------------------------------- 产物发现

def discover(project_root):
    """返回 [(绝对路径, 相对路径, role, [(上游相对路径, 上游role)])]"""
    out = []
    req = os.path.join(project_root, REQ_PATH)
    ex = os.path.join(project_root, EXEC_DIR)

    design = os.path.join(ex, DESIGN_DOC)
    arch = os.path.join(ex, ARCH_DOC)

    design_up = [(REQ_PATH, "raw")] if os.path.isfile(req) else []
    arch_up = [(os.path.join(EXEC_DIR, DESIGN_DOC), "design_doc")]
    mod_up = [(os.path.join(EXEC_DIR, DESIGN_DOC), "design_doc"),
              (os.path.join(EXEC_DIR, ARCH_DOC), "arch_doc")]

    if os.path.isfile(design):
        out.append((design, os.path.join(EXEC_DIR, DESIGN_DOC), "design_doc", design_up))
    if os.path.isfile(arch):
        out.append((arch, os.path.join(EXEC_DIR, ARCH_DOC), "arch_doc", arch_up))
    for p in sorted(glob.glob(os.path.join(ex, "*详细设计.md"))):
        base = os.path.basename(p)
        if MODULE_DOC_RE.match(base):
            out.append((p, os.path.join(EXEC_DIR, base), "module_doc", mod_up))
    return out


# ---------------------------------------------------------------- 元信息块

def parse_meta(text):
    """返回 ([(上游路径, 指纹串, 计数串)], 块起止行号) 或 (None, None)"""
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if META_MARK in l:
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
                                    "若是机制引入前生成的，运行 --stamp 补上即可"],
                        "backflow": []})
            continue

        recorded = {p: (fp, c) for p, fp, c in refs}
        stale_ups, details = [], []
        for up_rel, up_role in upstreams:
            up_abs = os.path.join(project_root, up_rel)
            if not os.path.isfile(up_abs):
                details.append("上游不存在：%s" % up_rel)
                continue
            if up_rel not in recorded:
                stale_ups.append(up_rel)
                details.append("新增上游依赖：%s（产物未记录它）" % up_rel)
                continue
            cur_fp, cur_sets = fingerprint(up_abs, up_role)
            if cur_fp is None:
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
    return out


def check_one(project_root):
    findings = []
    for r in evaluate(project_root):
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
    """跑一个校验器并解析它的 --json 输出。

    同族校验器约定输出**数组**；这里对「单个对象」也兼容一下，避免因形状不一致
    被误判成"未检测"。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        out = r.stdout.strip()
        for ch in ("[", "{"):
            i = out.find(ch)
            if i < 0:
                continue
            try:
                data = json.loads(out[i:])
            except Exception:
                continue
            return data if isinstance(data, list) else [data]
        return None
    except Exception:
        return None


def run_gates(root, in_scope=None):
    """跑各阶段校验器，返回 [(阶段, 脚本名, 判定, 明细)]

    in_scope：交付范围覆盖的阶段 token 集合（None = 不限制）。
    范围外的阶段**不跑**；其产物若存在，会在交付清单里单独提示「超出范围」。"""
    ex = os.path.join(root, EXEC_DIR)
    design = os.path.join(ex, DESIGN_DOC)
    arch = os.path.join(ex, ARCH_DOC)
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
    e2e_dir = os.path.join(root, "frontend", "tests", "e2e")
    if _tok("e2e") and os.path.isdir(e2e_dir) and os.path.isfile(design):
        run("⑤ E2E 测试", ("product-e2e-test", "scripts", "validate_e2e_spec.py"),
            ["--design-doc", design, "--spec-dir", e2e_dir], "validate_e2e_spec.py")
    return results


def ac_coverage(root):
    """返回 (设计定义的 AC, 模块文档承载的 AC, E2E 用例引用的 AC)"""
    ex = os.path.join(root, EXEC_DIR)
    design = os.path.join(ex, DESIGN_DOC)
    design_ac = set(AC_RE.findall(strip_fences(read_text(design)))) if os.path.isfile(design) else set()
    module_ac = set()
    for p in glob.glob(os.path.join(ex, "*详细设计.md")):
        if MODULE_DOC_RE.match(os.path.basename(p)):
            module_ac |= set(AC_RE.findall(strip_fences(read_text(p))))
    e2e_ac = set()
    for p in glob.glob(os.path.join(root, "frontend", "tests", "e2e", "**", "*.spec.ts"), recursive=True):
        e2e_ac |= set(AC_RE.findall(read_text(p)))
    return design_ac, module_ac, e2e_ac


def collect_unresolved(root):
    """从诊断报告的「未确认项」小节收集遗留项"""
    out = []
    for p in sorted(glob.glob(os.path.join(root, EXEC_DIR, "90_诊断报告_*.md"))):
        lines = strip_fences(read_text(p)).split("\n")
        for i, l in enumerate(lines):
            if ANY_HEADING_RE.match(l) and "未确认" in l:
                buf = []
                for l2 in lines[i + 1:]:
                    if ANY_HEADING_RE.match(l2):
                        break
                    if l2.strip():
                        buf.append(l2.strip())
                body = " ".join(buf).strip()
                if body and body not in ("无", "暂无", "-", "（无）", "待补充"):
                    out.append((os.path.basename(p), body[:200]))
                break
    return out


# 交付范围声明（写在 原始需求.md 头部；缺省全链，向后兼容）
SCOPE_LINE_RE = re.compile(r"交付范围\s*[:：]\s*([^\s*`>#。；]+)")
DEFAULT_SCOPE = "全链"
SCOPE_LEVELS = {
    "仅需求分析": ("design",),
    "设计到模块": ("design", "arch", "module"),
    "全链": ("design", "arch", "module", "dev", "e2e"),
}
GATE_STAGE_TOKEN = {"①": "design", "②": "arch", "③": "module", "⑤": "e2e"}


def parse_scope(root):
    """从 原始需求.md 解析「交付范围」声明，返回 (范围值, 说明文字)。

    缺文件 / 未声明 / 值非法 → 默认「全链」（向后兼容：不声明的老项目行为不变）。"""
    p = os.path.join(root, REQ_PATH)
    if not os.path.isfile(p):
        return DEFAULT_SCOPE, "未找到 `原始需求.md`，按默认范围**全链**判定"
    m = SCOPE_LINE_RE.search(read_text(p))
    if not m:
        return DEFAULT_SCOPE, "未声明交付范围，按默认**全链**判定"
    val = m.group(1).strip().strip("。；;，,")
    if val not in SCOPE_LEVELS:
        return DEFAULT_SCOPE, ("交付范围「%s」无法识别（可选：%s），按默认**全链**判定"
                               % (val, " / ".join(SCOPE_LEVELS)))
    return val, "交付范围：**%s**" % val


def finalize(root, out_path=None):
    """生成交付清单，返回 (输出路径, 是否就绪, 一句话摘要)

    结项按「交付范围」裁剪（parse_scope）；范围外阶段不计入就绪判定，
    其产物若存在仅提示「超出范围」。"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ex = os.path.join(root, EXEC_DIR)
    out_path = out_path or os.path.join(ex, DELIVERY_NAME)

    freshness = evaluate(root)
    design_path = os.path.join(ex, DESIGN_DOC)
    arch_path = os.path.join(ex, ARCH_DOC)
    design_ac, module_ac, e2e_ac = ac_coverage(root)
    unresolved = collect_unresolved(root)

    scope_val, scope_note = parse_scope(root)
    in_scope = SCOPE_LEVELS[scope_val]

    stale = [r for r in freshness if r["status"] == "STALE"]
    unmarked = [r for r in freshness if r["status"] == "UNMARKED"]
    miss_in_module = sorted(design_ac - module_ac)
    dangling = sorted((module_ac | e2e_ac) - design_ac)
    has_e2e = bool(glob.glob(os.path.join(root, "frontend", "tests", "e2e", "**", "*.spec.ts"),
                             recursive=True))
    miss_in_e2e = sorted(design_ac - e2e_ac) if has_e2e else []
    has_code = (os.path.isdir(os.path.join(root, "frontend"))
                or os.path.isdir(os.path.join(root, "backend")))

    # ---- 范围外产物：存在但超出声明范围 —— 仅提示，不算失败 ----
    out_of_scope = []
    if "arch" not in in_scope and os.path.isfile(arch_path):
        out_of_scope.append("`%s`（含其陈旧状态）" % ARCH_DOC)
    if "module" not in in_scope:
        out_of_scope += ["`%s`（含其陈旧状态）" % os.path.basename(p)
                         for p in sorted(glob.glob(os.path.join(ex, "*详细设计.md")))
                         if MODULE_DOC_RE.match(os.path.basename(p))]
    if "e2e" not in in_scope and has_e2e:
        out_of_scope.append("`frontend/tests/e2e/` 用例")
    if "dev" not in in_scope and has_code:
        out_of_scope.append("`frontend/` 与 `backend/` 代码")

    # ---- 条件 1：产物齐全（按范围定义）----
    if scope_val == "仅需求分析":
        products_ok = os.path.isfile(design_path)
        products_note = "范围内产物：`%s` %s" % (DESIGN_DOC, "存在" if products_ok else "**缺失**")
    elif scope_val == "设计到模块":
        n_mods = sum(1 for p in glob.glob(os.path.join(ex, "*详细设计.md"))
                     if MODULE_DOC_RE.match(os.path.basename(p)))
        miss = [n for n, ok in ((DESIGN_DOC, os.path.isfile(design_path)),
                                (ARCH_DOC, os.path.isfile(arch_path)),
                                ("模块详细设计 ≥1 份", n_mods >= 1)) if not ok]
        products_ok = not miss
        products_note = ("范围内产物齐全（设计 / 架构 / %d 份模块）" % n_mods) if products_ok             else "缺失：%s" % "、".join(miss)
    else:
        products_ok = bool(freshness) and has_code
        products_note = "设计产物 %d 份、%s" % (len(freshness),
                                               "代码目录存在" if has_code else "**未见代码目录**")

    # ---- 条件 3：门禁（只跑范围内阶段）----
    gates = run_gates(root, in_scope)
    s_fail = [g for g in gates if g[2] == "FAIL"]
    s_unknown = [g for g in gates if g[2] == "未检测"]
    gates_ok = not s_fail and not s_unknown
    gates_note = "FAIL %d、未检测 %d（仅判交付范围内阶段）" % (len(s_fail), len(s_unknown))

    # ---- 条件 4：AC 覆盖（按范围）----
    if scope_val == "仅需求分析":
        ac_counted, ac_ok = False, True
        ac_note = "跨阶段覆盖不在交付范围；AC 的格式与唯一性已由 ① 门禁 C12–C14 判定"
        m_miss, d_dang, m_e2e = [], [], []
    elif scope_val == "设计到模块":
        ac_counted, ac_ok = True, not miss_in_module and not dangling
        ac_note = "模块未声明 %d、悬空 %d（E2E 覆盖不在交付范围）" % (len(miss_in_module), len(dangling))
        m_miss, d_dang, m_e2e = miss_in_module, dangling, []
    else:
        ac_counted, ac_ok = True, not miss_in_module and not dangling and not miss_in_e2e
        ac_note = "模块未声明 %d、E2E 未引用 %d、悬空 %d" % (
            len(miss_in_module), len(miss_in_e2e), len(dangling))
        m_miss, d_dang, m_e2e = miss_in_module, dangling, miss_in_e2e

    # (名称, 是否计入判定, 是否通过, 说明)
    checks = [
        ("产物齐全（按交付范围）", True, products_ok, products_note),
        ("来源链自洽（无陈旧 / 无未标记）", True, not stale and not unmarked,
         "陈旧 %d、未标记 %d" % (len(stale), len(unmarked))),
        ("各阶段门禁 PASS", True, gates_ok, gates_note),
        ("AC 覆盖（按交付范围）", ac_counted, ac_ok, ac_note),
        ("无遗留未确认项", True, not unresolved, "遗留 %d 项" % len(unresolved)),
    ]
    ready = all(ok for _n, counted, ok, _note in checks if counted)

    L = ["# 交付清单", "",
         "**生成时间**：%s" % now,
         "**范围**：%s" % scope_note,
         "**结论**：%s" % ("**就绪** —— 交付范围内条件满足，可交付" if ready
                            else "**未就绪** —— 见下方未通过项"),
         "",
         "> 本文件由 `product-workflow/scripts/check_freshness.py --finalize` 生成，**请勿手工修改**。",
         "> 上游任一产物变更后，重跑一次即可刷新。范围声明见 `原始需求.md` 顶部。", "",
         "## 1. 结项判定", "",
         "| 条件 | 结果 | 说明 |", "|---|---|---|"]
    for name, counted, ok, note in checks:
        verdict = ("通过" if ok else "**未通过**") if counted else "— 不在本次交付范围"
        L.append("| %s | %s | %s |" % (name, verdict, note))

    L += ["", "## 2. 产物清单与来源链", "", "| 产物 | 来源链状态 |", "|---|---|"]
    for r in freshness:
        st = {"OK": "与上游一致",
              "STALE": "**陈旧**（上游已变）",
              "UNMARKED": "未标记，无法判定"}[r["status"]]
        L.append("| `%s` | %s |" % (r["path"], st))
    L.append("| 代码 / E2E 用例 | 由「最近的陈旧上游」推导，不单独标记 |")
    if stale:
        L += ["", "**陈旧产物的回流建议**："]
        for r in stale:
            L.append("- `%s` → %s" % (r["path"], " → ".join(r["backflow"]) or "（人工判断）"))

    L += ["", "## 3. 各阶段门禁结果", "", "| 阶段 | 校验器 | 结果 | 明细 |", "|---|---|---|---|"]
    if gates:
        for stage, label, verdict, note in gates:
            L.append("| %s | `%s` | %s | %s |" % (stage, label, verdict, note))
    else:
        L.append("| — | — | 未检测 | 交付范围内暂无可校验的产物 |")
    out_stages = [s for s, t in GATE_STAGE_TOKEN.items() if t not in in_scope]
    if out_stages:
        L.append("| %s | — | — 不在本次交付范围 | 按 `原始需求.md` 的交付范围声明跳过 |" % "、".join(out_stages))

    L += ["", "## 4. AC 覆盖汇总", "",
          "| 环节 | AC 条数 |", "|---|---|",
          "| 设计文档定义 | %d |" % len(design_ac),
          "| 模块详细设计承载 | %d |" % len(module_ac),
          "| E2E 用例引用 | %d |" % len(e2e_ac), ""]
    if m_miss:
        L.append("**设计定义了但模块未承载**：%s" % "、".join(m_miss[:12]))
    if m_e2e:
        L.append("**设计定义了但 E2E 未引用**：%s" % "、".join(m_e2e[:12]))
    if d_dang:
        L.append("**悬空引用**（模块/用例引用了设计里没有的编号）：%s" % "、".join(d_dang[:12]))
    if not (m_miss or m_e2e or d_dang):
        L.append("判定范围内三环一致，无缺口。")

    L += ["", "## 5. 遗留未确认项", ""]
    if unresolved:
        for f, body in unresolved:
            L.append("- `%s`：%s" % (f, body))
    else:
        L.append("无。")

    if out_of_scope:
        L += ["", "## 6. 超出交付范围的产物", "",
              "以下产物**存在**但超出 `原始需求.md` 声明的交付范围（不阻断结项，但建议核对范围声明是否过期）："]
        for x in out_of_scope:
            L.append("- %s" % x)

    if not ready:
        L += ["", "## 7. 下一步", ""]
        for name, counted, ok, note in checks:
            if counted and not ok:
                L.append("- **%s**：%s" % (name, note))
        L += ["", "修复后重跑：`python3 product-workflow/scripts/check_freshness.py "
                  "--finalize --project-root <项目根>`"]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    summary = "就绪" if ready else "未就绪（%d 项待处理）" % sum(
        1 for _n, c, ok, _note in checks if c and not ok)
    return out_path, ready, summary


# ---------------------------------------------------------------- 输出

def render(findings):
    lines = ["=" * 72, "产物陈旧检测", "=" * 72]
    for f in findings:
        lines.append("  [%s] %s" % (f.level, f.message))
        for d in f.detail:
            lines.append("           %s" % d)
    n_stale = sum(1 for f in findings if f.level == "STALE")
    n_warn = sum(1 for f in findings if f.level == "WARN")
    verdict = "STALE" if n_stale else ("OK(WARN)" if n_warn else "OK")
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
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)

    if args.finalize:
        path, ready, summary = finalize(root, args.finalize_path)
        print("已生成：%s" % path)
        print("结项结论：%s" % summary)
        return 0 if ready else 1

    if args.stamp:
        msgs = []
        for target in args.stamp:
            abs_t = target if os.path.isabs(target) else os.path.join(root, target)
            if not os.path.isfile(abs_t):
                msgs.append("SKIP %s（文件不存在）" % target); continue
            # 找到它在依赖图里的位置
            hit = None
            for abs_p, rel_p, role, upstreams in discover(root):
                if os.path.abspath(abs_p) == abs_t:
                    hit = (rel_p, role, upstreams); break
            if not hit:
                msgs.append("SKIP %s（不在已知产物依赖图中）" % target); continue
            rel_p, role, upstreams = hit
            entries = []
            for up_rel, up_role in upstreams:
                up_abs = os.path.join(root, up_rel)
                if not os.path.isfile(up_abs):
                    msgs.append("  ! %s 的上游 %s 不存在，跳过该条" % (rel_p, up_rel)); continue
                fp, sets = fingerprint(up_abs, up_role)
                if fp is None:
                    msgs.append("  ! %s 无法提取契约指纹，跳过该条" % up_rel); continue
                entries.append((up_rel, fp, counts_str(sets)))
            updated = write_meta(abs_t, entries)
            msgs.append("%s %s（%d 条上游）" % ("UPDATED" if updated else "STAMPED", rel_p, len(entries)))
        print("\n".join(msgs))
        return 0

    findings = check_one(root)
    if args.json:
        print(json.dumps([f.as_dict() for f in findings], ensure_ascii=False, indent=2))
    elif args.quiet:
        n_stale = sum(1 for f in findings if f.level == "STALE")
        n_warn = sum(1 for f in findings if f.level == "WARN")
        print("%s  (STALE=%d WARN=%d)" % ("STALE" if n_stale else ("OK(WARN)" if n_warn else "OK"),
                                          n_stale, n_warn))
    else:
        print(render(findings))

    return 1 if any(f.level == "STALE" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
