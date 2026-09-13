#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_module_doc.py —— 模块详细设计文档门禁校验器

重点防的是**静默漂移**：模块设计声明的 AC 与产品设计文档对不上、或用例没覆盖到，
这类问题不会有任何外部症状，只能靠脚本发现。

检查项:
    M1 FAIL 模块文档里的 AC 编号，必须在产品设计文档中存在（悬空检测，需 --design-doc）
    M2 FAIL 「本模块覆盖的 AC」声明的集合，必须与测试用例表引用的集合一致
            （声明的没测 → 漏测；测了没声明 → 不一致）
    M3 FAIL 每个接口块必须含 Endpoint / 请求参数 / 成功响应 / 错误响应 四块
    M4 FAIL 数据库设计必须有含 CREATE TABLE 的代码块，且块内出现索引声明
    M5 FAIL Mermaid 合规（无全角标点 / 不用 flowchart / 子图不用 direction）
    M6 WARN 清单编号重复或 DDL 无注释；缺必需 AC/接口/数据库内容 FAIL

用法:
    python3 validate_module_doc.py --module-doc <项目根>/项目战术执行/01_xxx详细设计.md
    python3 validate_module_doc.py --module-doc ... --design-doc .../00_产品设计文档.md
    python3 validate_module_doc.py --module-doc ... --json | --quiet

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
from strict_docs import required, na, mermaid_errors, sections as strict_sections, meaningful

# ---------------------------------------------------------------- 常量

AC_VALID_RE = re.compile(r"AC-[A-Z][A-Z0-9]{1,7}-[0-9]{2}")
AC_CANDIDATE_RE = re.compile(r"AC-[A-Za-z0-9\u4e00-\u9fff]+(?:-[A-Za-z0-9\u4e00-\u9fff]+)*")

FENCE_RE = re.compile(r"^\s*```\s*([A-Za-z0-9_+-]*)\s*$")
ANY_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")

FULLWIDTH_CHARS = "（）“”‘’，。：；？！【】《》、"

INTERFACE_RE = re.compile(r"^\s*-\s*\*\*接口\s*\d+")
INTERFACE_REQUIRED = ("Endpoint", "请求参数", "成功响应", "错误响应")
INDEX_HINT_RE = re.compile(r"CREATE\s+(UNIQUE\s+)?INDEX|INDEX\s*\(|PRIMARY\s+KEY|UNIQUE", re.I)


class Finding:
    def __init__(self, level, code, message):
        self.level = level
        self.code = code
        self.message = message

    def as_dict(self):
        return {"level": self.level, "code": self.code, "message": self.message}


# ---------------------------------------------------------------- 解析

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def split_blocks(text):
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


def blocks_with_pos(text):
    """返回 [(kind, payload, start_line, end_line)]，行号含头不含尾。

    找代码块必须用**带围栏的原文**定位行号 —— 用去围栏后的文本去找 `CREATE TABLE`
    永远找不到（那一行已经被删掉了）。
    """
    out, lines = [], text.split("\n")
    i, buf, buf_start = 0, [], 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            if buf:
                out.append(("text", "\n".join(buf), buf_start, i))
                buf = []
            start, lang = i, m.group(1).lower()
            i += 1
            body = []
            while i < len(lines) and not FENCE_RE.match(lines[i]):
                body.append(lines[i]); i += 1
            i += 1
            out.append(("fence", (lang, "\n".join(body)), start, i))
        else:
            if not buf:
                buf_start = i
            buf.append(lines[i]); i += 1
    if buf:
        out.append(("text", "\n".join(buf), buf_start, len(lines)))
    return out


def heading_ranges(text, keyword):
    """返回标题含 keyword 的小节行区间 [(start, end)]（基于带围栏的原文）"""
    lines = text.split("\n")
    heads = [(i, len(m.group(1)), m.group(2).strip())
             for i, l in enumerate(lines) if (m := ANY_HEADING_RE.match(l))]
    out = []
    for k, (i, lvl, title) in enumerate(heads):
        if keyword not in title:
            continue
        end = len(lines)
        for j, l2, _t in heads[k + 1:]:
            if l2 <= lvl:
                end = j
                break
        out.append((i, end))
    return out


def collect_ac(text):
    cands = AC_CANDIDATE_RE.findall(text)
    valid = [c for c in cands if AC_VALID_RE.fullmatch(c)]
    invalid = sorted({c for c in cands if not AC_VALID_RE.fullmatch(c)})
    return valid, invalid


def sections(plain):
    """按标题切成 [(level, title, body)]"""
    lines = plain.split("\n")
    heads = [(i, len(m.group(1)), m.group(2).strip())
             for i, l in enumerate(lines) if (m := ANY_HEADING_RE.match(l))]
    out = []
    for k, (i, lvl, title) in enumerate(heads):
        end = len(lines)
        for j, l2, _t in heads[k + 1:]:
            if l2 <= lvl:
                end = j
                break
        out.append((lvl, title, "\n".join(lines[i:end])))
    return out


def tables_with_headers(text):
    """返回 [(header_cells, data_rows)]，data_rows 为单元格列表的列表"""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        if TABLE_SEP_RE.match(lines[i]) and i > 0 and lines[i - 1].strip().startswith("|"):
            header = [c.strip().strip("`* ") for c in lines[i - 1].strip().strip("|").split("|")]
            rows, j = [], i + 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                if not TABLE_SEP_RE.match(lines[j]):
                    rows.append([c.strip().strip("`* ")
                                 for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append((header, rows))
            i = j
        else:
            i += 1
    return out


# ---------------------------------------------------------------- 检查

def check_mermaid(blocks, findings):
    """M5"""
    mer = [payload[1] for kind, payload in blocks
           if kind == "fence" and payload[0] == "mermaid"]
    if not mer:
        findings.append(Finding("FAIL", "M5", "未找到 ```mermaid 代码块（页面功能流程 / ER 图应为必需）"))
    for bi, body in enumerate(mer, 1):
        bad = sorted(set(ch for ch in body if ch in FULLWIDTH_CHARS))
        if bad:
            findings.append(Finding(
                "FAIL", "M5", "第 %d 个 Mermaid 块含全角标点：%s（见 mermaid-guide.md 第 1 节）"
                % (bi, " ".join(bad))))
        if re.search(r"^\s*flowchart\b", body, re.M):
            findings.append(Finding("FAIL", "M5",
                                    "第 %d 个 Mermaid 块用了 `flowchart` —— 应用 `graph TD` / `graph LR`" % bi))
        if re.search(r"^\s*direction\s+(TB|TD|BT|LR|RL)\b", body, re.M):
            findings.append(Finding("FAIL", "M5",
                                    "第 %d 个 Mermaid 块在子图里用了 `direction` —— 应拆图或调整排布" % bi))


def check_ac_consistency(plain, design_doc, findings):
    """M1 悬空 / M2 声明 vs 用例 / M6 重复"""
    doc_ac, doc_bad = collect_ac(plain)
    if doc_bad:
        findings.append(Finding("FAIL", "M1", "AC 编号格式不合法：%s" % " ".join(doc_bad[:6])))

    # 悬空：模块文档引用的 AC 必须在产品设计文档中存在
    if design_doc:
        if not os.path.isfile(design_doc):
            findings.append(Finding("FAIL", "M1", "设计文档不存在：%s" % design_doc))
        else:
            design_ac = set(collect_ac(read_text(design_doc))[0])
            if not design_ac:
                findings.append(Finding("WARN", "M6",
                                        "产品设计文档里没有任何 AC 编号 —— 请先在阶段①补齐验收标准"))
            for a in sorted(set(doc_ac) - design_ac):
                findings.append(Finding(
                    "FAIL", "M1",
                    "悬空：模块文档引用了 %s，但产品设计文档中没有这个编号 —— 编号写错，或上游已删改" % a))
    else:
        findings.append(Finding("WARN", "M1", "未提供 --design-doc，跳过 AC 悬空检查"))

    # 声明集合（「本模块覆盖的 AC」小节）
    declared_list = []
    for _lvl, title, body in sections(plain):
        if "覆盖的 AC" in title or "覆盖的AC" in title:
            declared_list += collect_ac(body)[0]
    declared = set(declared_list)
    for a in sorted({x for x in declared_list if declared_list.count(x) > 1}):
        findings.append(Finding(
            "WARN", "M6", "「本模块覆盖的 AC」清单里 %s 出现了 %d 次（同一编号应只登记一次）"
            % (a, declared_list.count(a))))

    # 用例集合（表头含「对应 AC 编号」的表格）
    used = set()
    found_case_table = False
    for header, rows in tables_with_headers(plain):
        joined = " ".join(header)
        if "对应 AC" in joined or "AC 编号" in joined and "用例" in joined:
            found_case_table = True
            idx = next((i for i, c in enumerate(header) if "AC" in c), None)
            if idx is None:
                continue
            for r in rows:
                if idx < len(r):
                    used |= set(collect_ac(r[idx])[0])

    if not found_case_table or not declared:
        findings.append(Finding("FAIL", "M6", "未识别到「本模块覆盖的 AC」表或测试用例表，无法完成 AC 一致性检查，阻断"))
        return

    for a in sorted(declared - used):
        findings.append(Finding(
            "FAIL", "M2", "漏测：声明覆盖 %s，但测试用例表里没有任何用例引用它" % a))
    for a in sorted(used - declared):
        findings.append(Finding(
            "FAIL", "M2", "不一致：用例引用了 %s，但它不在「本模块覆盖的 AC」清单里" % a))


def check_interfaces(plain, findings):
    """M3 接口三块 + 错误响应"""
    lines = plain.split("\n")
    starts = [i for i, l in enumerate(lines) if INTERFACE_RE.match(l)]
    if not starts:
        findings.append(Finding("FAIL", "M6", "未识别到「- **接口N: 名称**」形式的接口块，无法完成接口检查，阻断"))
        return
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        for j in range(i + 1, end):
            if ANY_HEADING_RE.match(lines[j]):
                end = j
                break
        block = "\n".join(lines[i:end])
        title = re.sub(r"^\s*-\s*\*\*|\*\*.*$", "", lines[i]).strip() or lines[i].strip()[:24]
        for key in INTERFACE_REQUIRED:
            values = [line.split('|')[2].strip() for line in block.splitlines() if key in line and line.count('|') >= 2]
            if key not in block or not any(meaningful(value.strip('`*')) for value in values):
                findings.append(Finding(
                    "FAIL", "M3", "接口「%s」缺「%s」块 —— 契约表须含 Endpoint / 请求参数 / 成功响应 / 错误响应"
                    % (title, key)))


def check_ddl(text, findings):
    """M4 数据库设计必须有 CREATE TABLE + 索引声明"""
    ranges = heading_ranges(text, "数据库设计")
    if not ranges:
        findings.append(Finding("FAIL", "M6", "未识别到「数据库设计」小节，无法完成 DDL 检查，阻断"))
        return

    ddls = []
    for kind, payload, start, _end in blocks_with_pos(text):
        if kind != "fence":
            continue
        _lang, body = payload
        if not any(s <= start < e for s, e in ranges):
            continue
        if "CREATE TABLE" in body.upper():
            ddls.append(body)

    if not ddls:
        findings.append(Finding(
            "FAIL", "M4", "「数据库设计」小节下没有含 `CREATE TABLE` 的代码块 —— 每张表都要有 DDL"))
        return
    if not any(INDEX_HINT_RE.search(b) for b in ddls):
        findings.append(Finding(
            "FAIL", "M4", "DDL 中未见任何索引声明（`CREATE INDEX` / `PRIMARY KEY` / `UNIQUE`）"))
    if not any(re.search(r"^\s*--", b, re.M) for b in ddls):
        findings.append(Finding("WARN", "M6", "DDL 中没有注释行（`-- ...`）—— 字段与索引建议加注释"))


def validate(module_doc, design_doc=None):
    findings = []
    if not os.path.isfile(module_doc):
        findings.append(Finding("FAIL", "M0", "模块文档不存在：%s" % module_doc))
        return findings

    text = read_text(module_doc)
    plain = strip_fences(text)

    for error in required(text, ['产品设计', '前端详细设计', '后端详细设计', '测试详细设计']):
        findings.append(Finding('FAIL', 'M7', error))
    for error in mermaid_errors([p[1] for k,p in split_blocks(text) if k == 'fence' and p[0] == 'mermaid']):
        findings.append(Finding('FAIL', 'M8', error))
    check_mermaid(split_blocks(text), findings)
    check_ac_consistency(plain, design_doc, findings)
    if not na(plain, 'api'):
        check_interfaces(plain, findings)
    if not na(plain, 'database'):
        check_ddl(text, findings)

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
    ap = argparse.ArgumentParser(description="模块详细设计文档门禁校验器")
    ap.add_argument("--module-doc", required=True, nargs="+",
                    help="模块详细设计文档路径（支持通配）")
    ap.add_argument("--design-doc", default=None, help="产品设计文档路径（AC 悬空检查用）")
    ap.add_argument("--json", action="store_true", help="输出机读 JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    args = ap.parse_args(argv)

    paths = []
    for pattern in args.module_doc:
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
