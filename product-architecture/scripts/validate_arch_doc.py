#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_arch_doc.py —— 功能架构设计文档阶段检查器

只做**高置信、低误报**的结构性检查。判断类内容（方案是否合理、是否重复描述业务含义）
不在本脚本范围，靠 `product-architecture/SKILL.md` 的人工自检清单。

检查项:
    A1 FAIL 至少 1 个真实 ```mermaid 代码块
    A2 FAIL Mermaid 合规（无全角标点 / 流程图不用 flowchart / 子图不用 direction）
    A3 FAIL 每个表定义块都有「字段定义」表格（列头含 字段名·类型·约束·描述）+ 表级「索引」行
    A4 FAIL 前端组件树里的 .tsx / .jsx 文件名必须是 PascalCase
    A5 WARN 产品设计文档「页面清单」里的页面未在架构文档中出现（弱版覆盖检查，需 --design-doc）
    A6 WARN ER 图实体名与表定义的表名集合不一致（弱版；关系与基数无法可靠判定）

用法:
    python3 validate_arch_doc.py --arch-doc <项目根>/项目战术执行/00_功能架构设计文档.md
    python3 validate_arch_doc.py --arch-doc ... --design-doc .../00_产品设计文档.md
    python3 validate_arch_doc.py --arch-doc ... --json | --quiet

退出码: 0 = 无 FAIL；1 = 存在 FAIL；2 = 用法错误
"""

import argparse
import glob
import json
import os
import re
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'product-workflow/scripts'))
from strict_docs import required, na, mermaid_errors, sections as strict_sections, meaningful, populated_tables

# ---------------------------------------------------------------- 常量

FENCE_RE = re.compile(r"^\s*```\s*([A-Za-z0-9_+-]*)\s*$")
ANY_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")

# Mermaid 绝对禁止的全角标点（见 mermaid-guide.md 第 1 节）
FULLWIDTH_CHARS = "（）“”‘’，。：；？！【】《》、"

# 表定义块的表名行：`表名:` / `**表名:**` / `表名 :`
TABLE_NAME_RE = re.compile(r"表名\s*[:：]\s*(.+?)\s*$")

def clean_name(raw):
    """剥掉 markdown 粗体、反引号与空白，得到裸标识符"""
    return re.sub(r"^[*`\s]+|[*`\s]+$", "", raw.strip())
# 字段定义表格必备的列（按语义匹配，允许「数据类型」这类变体）
FIELD_COL_GROUPS = (
    ("字段名", "字段", "名称"),
    ("类型", "数据类型"),
    ("约束", "必填"),
    ("描述", "注释", "说明", "备注"),
)

# 组件树代码块（含树形连接符）
TREE_CHAR_RE = re.compile(r"[├└]──|^\s*│", re.M)
COMPONENT_FILE_RE = re.compile(r"([A-Za-z0-9_@./-]+)\.(tsx|jsx)\b")


class Finding:
    def __init__(self, level, code, message):
        self.level = level          # FAIL / WARN / PASS
        self.code = code
        self.message = message

    def as_dict(self):
        return {"level": self.level, "code": self.code, "message": self.message}


# ---------------------------------------------------------------- 解析

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def split_blocks(text):
    """切成 (kind, payload)。kind: 'text' | 'fence'；fence 的 payload=(lang, body)"""
    blocks, lines = [], text.split("\n")
    i, buf = 0, []
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            if buf:
                blocks.append(("text", "\n".join(buf))); buf = []
            lang = m.group(1).lower()
            i += 1
            body = []
            while i < len(lines) and not FENCE_RE.match(lines[i]):
                body.append(lines[i]); i += 1
            i += 1
            blocks.append(("fence", (lang, "\n".join(body))))
        else:
            buf.append(lines[i]); i += 1
    if buf:
        blocks.append(("text", "\n".join(buf)))
    return blocks


def strip_fences(text):
    return "\n".join(p for k, p in split_blocks(text) if k == "text")


def tables_in(text):
    """返回 [(header_cells, start_line_index)]，按分隔行定位表格"""
    out, lines = [], text.split("\n")
    for i, line in enumerate(lines):
        if TABLE_SEP_RE.match(line) and i > 0 and lines[i - 1].strip().startswith("|"):
            cells = [c.strip().strip("`* ") for c in lines[i - 1].strip().strip("|").split("|")]
            out.append((cells, i - 1))
    return out


# ---------------------------------------------------------------- 检查

def check_mermaid(blocks, findings):
    """A1 / A2"""
    mer = [payload[1] for kind, payload in blocks
           if kind == "fence" and payload[0] == "mermaid"]
    if not mer:
        findings.append(Finding("FAIL", "A1", "没有找到任何 ```mermaid 代码块（系统架构图 / ER 图是必需产物）"))
        return
    for bi, body in enumerate(mer, 1):
        bad = sorted(set(ch for ch in body if ch in FULLWIDTH_CHARS))
        if bad:
            findings.append(Finding(
                "FAIL", "A2",
                "第 %d 个 Mermaid 块含全角标点：%s（见 mermaid-guide.md 第 1 节）" % (bi, " ".join(bad))))
        if re.search(r"^\s*flowchart\b", body, re.M):
            findings.append(Finding(
                "FAIL", "A2",
                "第 %d 个 Mermaid 块用了 `flowchart` —— 规范要求用 `graph TD` / `graph LR`" % bi))
        if re.search(r"^\s*direction\s+(TB|TD|BT|LR|RL)\b", body, re.M):
            findings.append(Finding(
                "FAIL", "A2",
                "第 %d 个 Mermaid 块在子图里用了 `direction` —— 部分渲染版本不支持，应拆图或调整排布" % bi))


def check_table_defs(plain, findings):
    """A3 每个表定义块必须有字段定义表格，且列头完整"""
    lines = plain.split("\n")
    name_idx = [(i, TABLE_NAME_RE.search(l)) for i, l in enumerate(lines) if TABLE_NAME_RE.search(l)]
    if not name_idx:
        findings.append(Finding(
            "FAIL", "A3",
            "未识别到「表名:」形式的表定义块（数据库设计应逐表给出表名 / 所属模块 / 核心职责 / 字段定义 / 索引）"))
        return

    for k, (i, m) in enumerate(name_idx):
        end = name_idx[k + 1][0] if k + 1 < len(name_idx) else len(lines)
        block = "\n".join(lines[i:end])
        tname = clean_name(m.group(1))
        if "字段定义" not in block:
            findings.append(Finding("FAIL", "A3", "表 %s 缺「字段定义」" % tname))
            continue
        heads = [h for h, _ in tables_in(block)]
        if not heads or not populated_tables(block):
            findings.append(Finding("FAIL", "A3", "表 %s 的「字段定义」下没有表格" % tname))
            continue
        ok = False
        for cells in heads:
            joined = " ".join(cells)
            if all(any(x in joined for x in grp) for grp in FIELD_COL_GROUPS):
                ok = True
                break
        if not ok:
            findings.append(Finding(
                "FAIL", "A3",
                "表 %s 的字段定义表列头不完整（需同时含：字段名 / 类型 / 约束 / 描述）。实际表头：%s"
                % (tname, " / ".join(heads[0]))))

        # 表级「索引」行（与 表名 / 所属模块 / 核心职责 / 字段定义 并列）——
        # 「索引」不是字段的属性，硬塞进字段表会让每行都重复写一遍索引。
        if not re.search(r"索引\s*[:：]", block):
            findings.append(Finding(
                "FAIL", "A3",
                "表 %s 缺表级「索引」行 —— 应写 `索引 : ...`；无索引时显式写「索引 : 无」" % tname))


def check_component_names(blocks, findings):
    """A4 组件树里的 .tsx/.jsx 文件名必须 PascalCase"""
    seen, bad = set(), []
    for kind, payload in blocks:
        if kind != "fence":
            continue
        _lang, body = payload
        if not TREE_CHAR_RE.search(body):
            continue
        for m in COMPONENT_FILE_RE.finditer(body):
            raw = m.group(1)
            base = raw.rsplit("/", 1)[-1]
            if base.lower() in ("index",):
                continue
            if base[0].islower():
                if base not in seen:
                    seen.add(base); bad.append(base)
    for b in bad:
        findings.append(Finding(
            "FAIL", "A4",
            "组件树里的 %s 用了小写开头 —— 组件与页面文件必须是 PascalCase（如 UserManagement.tsx）" % b))


def design_page_names(design_doc):
    """从产品设计文档的「页面清单」表取第一列（页面名）"""
    if not design_doc or not os.path.isfile(design_doc):
        return None
    lines = strip_fences(read_text(design_doc)).split("\n")

    start = None
    for i, l in enumerate(lines):
        m = ANY_HEADING_RE.match(l)
        if m and "页面清单" in m.group(2):
            start = i + 1
            break
    if start is None:
        return None

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
        return None

    names = []
    for l in seg[hdr + 2:]:
        if not l.strip().startswith("|"):
            break
        if TABLE_SEP_RE.match(l):
            continue
        first = l.strip().strip("|").split("|")[0].strip().strip("`* ")
        if first:
            names.append(first)
    return names


def check_page_coverage(design_doc, arch_text, findings):
    """A5 页面清单 ↔ 架构文档（弱版覆盖）"""
    names = design_page_names(design_doc)
    if names is None:
        findings.append(Finding("FAIL", "A5", "未能读取产品设计文档的「页面清单」，跳过覆盖检查"))
        return
    missing = [n for n in names if n and n not in arch_text]
    for n in missing:
        findings.append(Finding(
            "FAIL", "A5",
            "页面「%s」在产品设计文档的页面清单里，但架构文档中未出现 —— 确认它的模块/表/组件归属已写明" % n))


def check_er_consistency(blocks, plain, findings):
    """A6 ER 图实体名 vs 表定义的表名（弱版）"""
    entities = set()
    for kind, payload in blocks:
        if kind != "fence":
            continue
        lang, body = payload
        if lang != "mermaid" or "erDiagram" not in body:
            continue
        for line in body.split("\n"):
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{", line)
            if m:
                entities.add(m.group(1))
            for t in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s+[|}{o]{1,3}[-.]{1,2}[|}{o]{1,3}\s+([A-Za-z_][A-Za-z0-9_]*)", line):
                entities.update(t)
    if not entities:
        return
    defined = set()
    for l in plain.split("\n"):
        m = TABLE_NAME_RE.search(l)
        if m:
            defined.add(clean_name(m.group(1)))
    only_er = sorted(entities - defined)
    only_tbl = sorted(defined - entities)
    if only_er:
        findings.append(Finding(
            "WARN", "A6", "ER 图里有实体但表定义中没有：%s" % "、".join(only_er[:6])))
    if only_tbl:
        findings.append(Finding(
            "WARN", "A6", "表定义里有表但 ER 图中没有：%s" % "、".join(only_tbl[:6])))


def validate(arch_doc, design_doc=None):
    findings = []
    if not os.path.isfile(arch_doc):
        findings.append(Finding("FAIL", "A0", "架构文档不存在：%s" % arch_doc))
        return findings

    text = read_text(arch_doc)
    plain = strip_fences(text)
    blocks = split_blocks(text)

    for error in required(text, ['需求', '总体技术方案', '开发规范', '功能设计', '自检']):
        findings.append(Finding('FAIL', 'A7', error))
    for error in mermaid_errors([p[1] for k,p in blocks if k == 'fence' and p[0] == 'mermaid']):
        findings.append(Finding('FAIL', 'A8', error))
    if not na(plain, 'frontend') and not any(k == 'fence' and TREE_CHAR_RE.search(p[1]) and COMPONENT_FILE_RE.search(p[1]) for k,p in blocks):
        findings.append(Finding('FAIL', 'A9', '缺少前端组件树；无前端时声明 N/A[frontend]: 具体理由'))
    check_mermaid(blocks, findings)
    if not na(plain, 'database'):
        check_table_defs(plain, findings)
    check_component_names(blocks, findings)
    check_er_consistency(blocks, plain, findings)
    if design_doc:
        check_page_coverage(design_doc, plain, findings)

    if not any(f.level == "FAIL" for f in findings):
        findings.append(Finding("PASS", "OK", "全部硬性结构检查通过"))
    return findings


# ---------------------------------------------------------------- 输出

def render(all_findings):
    order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    lines = []
    for path, findings in all_findings:
        lines.append("=" * 72)
        lines.append("文档: %s" % path)
        lines.append("=" * 72)
        for f in sorted(findings, key=lambda x: order.get(x.level, 9)):
            tag = {"FAIL": "[FAIL]", "WARN": "[WARN]", "PASS": "[PASS]"}[f.level]
            lines.append("  %s %-3s %s" % (tag, f.code, f.message))
        fails = sum(1 for f in findings if f.level == "FAIL")
        warns = sum(1 for f in findings if f.level == "WARN")
        verdict = "FAIL" if fails else ("PASS(WARN)" if warns else "PASS")
        lines.append("  --> 结论: %s  (FAIL=%d WARN=%d)" % (verdict, fails, warns))
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="功能架构设计文档阶段检查器")
    ap.add_argument("--arch-doc", required=True, nargs="+", help="架构文档路径（支持通配）")
    ap.add_argument("--design-doc", default=None, help="产品设计文档路径（用于页面覆盖弱检查）")
    ap.add_argument("--json", action="store_true", help="输出机读 JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    args = ap.parse_args(argv)

    paths = []
    for pattern in args.arch_doc:
        hits = glob.glob(pattern)
        paths.extend(hits if hits else [pattern])

    all_findings = [(p, validate(p, args.design_doc)) for p in paths]

    if args.json:
        payload = []
        for path, findings in all_findings:
            fails = sum(1 for f in findings if f.level == "FAIL")
            warns = sum(1 for f in findings if f.level == "WARN")
            payload.append({
                "doc": path,
                "verdict": "FAIL" if fails else ("PASS(WARN)" if warns else "PASS"),
                "fail": fails, "warn": warns,
                "findings": [f.as_dict() for f in findings],
            })
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.quiet:
        for path, findings in all_findings:
            fails = sum(1 for f in findings if f.level == "FAIL")
            warns = sum(1 for f in findings if f.level == "WARN")
            verdict = "FAIL" if fails else ("PASS(WARN)" if warns else "PASS")
            print("%s  %s  (FAIL=%d WARN=%d)" % (verdict, path, fails, warns))
    else:
        print(render(all_findings))

    return 1 if any(f.level == "FAIL" for _p, fs in all_findings for f in fs) else 0


if __name__ == "__main__":
    sys.exit(main())
