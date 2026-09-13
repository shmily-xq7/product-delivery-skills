#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_design_doc.py —— 产品设计文档门禁硬校验器

把《product-design》SKILL.md 的「强约束」从"AI 人工查"升级为"脚本硬查"。
扫描一份产品设计文档，输出 PASS / WARN / FAIL 报告；存在 FAIL 时退出码为 1，
可直接用于门禁阻断。

用法:
    python3 validate_design_doc.py --doc <路径>/00_产品设计文档.md
    python3 validate_design_doc.py --doc <路径>/00_产品设计文档.md --json
    python3 validate_design_doc.py --doc <路径>/*.md --quiet

检查项:
    C1 FAIL 必需章节存在（业务流程 / 页面清单 / 功能设计详情）
    C2 FAIL 至少 1 个真实 Mermaid 代码块
    C3 FAIL Mermaid 代码块内无全角标点（参照 mermaid-guide.md）
    C4 FAIL 无「按钮/操作按钮」单独成表
    C5 FAIL 页面主体、以及每个弹窗/抽屉/步骤/tab，各自表格数 <= 2
    C6 FAIL 每个页面/弹窗应有「字段字典」
    C7 WARN 每个页面/弹窗应有 ASCII 布局图代码块
    C8 FAIL 每个页面/弹窗应有「交互矩阵」
    C9 WARN 越界内容检测（出现表结构 DDL / 技术选型字样提示移交架构阶段）
    C10 FAIL 页面线框图中不得混入 Unicode 框线字符（须用 ASCII 的 + - |）
    C11 FAIL 页面线框图中不得出现 emoji / 宽度不定的符号（单宽几何符号见 WIREFRAME_ALLOWED）
    C12 FAIL AC 编号格式合法（AC-<2~8位大写模块缩写>-<两位序号>）
    C13 FAIL AC 编号全文唯一（不得重复定义）
    C14 FAIL 每个页面小节至少 1 条验收标准（AC）
    C15 WARN 弹窗/抽屉/步骤/tab 子节应各自列出 AC（若页面级 AC 已覆盖可忽略）

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

REQUIRED_SECTIONS = ["业务流程", "页面清单", "功能设计详情"]

# 全角标点（Mermaid 禁用集，见 mermaid-guide.md）
FULLWIDTH_CHARS = "（）“”‘’，。：；？！【】《》、"

# Unicode 框线字符（页面线框图禁用；文件树/流程示意不受限）
BOX_CHARS = set("┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬╭╮╯╰")

# 页面线框图**允许**的单宽几何 / 勾选符号（用来替代 emoji 做状态标记）
# 注意：▼ □ ● ○ ■ ◆ ◀ ▶ 属 East Asian「Ambiguous」宽度 —— 在部分中日韩等宽字体下会按 2 列
# 渲染而致错位；若阅读环境如此，请改用纯文字标记（v / [ ] / [x] / (o) / ( )）。
# ☐ ☑ ☒ ✓ ▪ ▫ 为真正单宽（N/Na），无此风险。
WIREFRAME_ALLOWED = set("▼▽▲△■□▪▫●○◆◇◀▶◁▷☐☑☒✓")

# 非 ASCII 符号 / emoji 的候选范围：命中后**剔除 WIREFRAME_ALLOWED** 才是违规
NON_ASCII_SYMBOL_RE = re.compile(
    "[\u25a0-\u25ff\u2600-\u27bf\u2b00-\u2bff\U0001f000-\U0001faff\ufe0f]"
)

# 暗示走了技术侧的内容（越界）
BOUNDARY_HINTS = ["CREATE TABLE", "CREATE  TABLE", "技术选型", "架构风格", "微服务拆分"]

# ---- AC 验收标准（见 product-design-spec.md 第 6 节）----
# 合法编号：AC-<2~8位大写字母数字，首字符为字母>-<两位数字>
AC_VALID_RE = re.compile(r"AC-[A-Z][A-Z0-9]{1,7}-[0-9]{2}")
# 候选串：以 AC- 开头、由 ASCII 字母数字或中文构成（用于捞出不合法写法）
AC_CANDIDATE_RE = re.compile(r"AC-[A-Za-z0-9\u4e00-\u9fff]+(?:-[A-Za-z0-9\u4e00-\u9fff]+)*")
# 标题以这些词结尾说明该小节是「弹窗/步骤/tab」这一级元素（需要自带 AC）
AC_SCOPE_SUFFIX = ("弹窗", "抽屉", "tab", "步骤")

# 页面级标题（### 开头，且不在「全局检查」等非页面小节下）
PAGE_HEADING_RE = re.compile(r"^(#{3})\s+(.+?)\s*$")
ANY_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

FENCE_RE = re.compile(r"^\s*```\s*([A-Za-z0-9_+-]*)\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")


class Finding:
    def __init__(self, level, code, message, where=""):
        self.level = level          # PASS / WARN / FAIL
        self.code = code
        self.message = message
        self.where = where

    def as_dict(self):
        return {"level": self.level, "code": self.code,
                "message": self.message, "where": self.where}


# ---------------------------------------------------------------- 解析

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def split_blocks(text):
    """把文本切成 (kind, payload) 列表。kind: 'text' | 'fence'；fence 的 payload=(lang, body)"""
    blocks = []
    lines = text.split("\n")
    i = 0
    buf = []
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            if buf:
                blocks.append(("text", "\n".join(buf)))
                buf = []
            lang = m.group(1).lower()
            i += 1
            body = []
            while i < len(lines) and not FENCE_RE.match(lines[i]):
                body.append(lines[i])
                i += 1
            i += 1  # 跳过闭合围栏
            blocks.append(("fence", (lang, "\n".join(body))))
        else:
            buf.append(lines[i])
            i += 1
    if buf:
        blocks.append(("text", "\n".join(buf)))
    return blocks


def strip_fences(text):
    """去掉所有围栏代码块，得到纯散文文本（用于章节/表格统计，避免代码块内噪声）"""
    out = []
    for kind, payload in split_blocks(text):
        if kind == "text":
            out.append(payload)
    return "\n".join(out)


def collect_headings(text):
    """返回 [(level:int, title:str, line_index_span)]，基于去掉代码块后的文本"""
    heads = []
    for idx, line in enumerate(strip_fences(text).split("\n")):
        m = ANY_HEADING_RE.match(line)
        if m:
            heads.append((len(m.group(1)), m.group(2).strip()))
    return heads


def count_tables(text):
    """统计一段文本里的 markdown 表格数量（以分隔行为锚点）"""
    n = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if TABLE_SEP_RE.match(line) and i > 0 and lines[i - 1].strip().startswith("|"):
            n += 1
    return n


def find_button_tables(text):
    """找出以「按钮」为列头的表（= 按钮操作单独成表）"""
    hits = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if TABLE_SEP_RE.match(line) and i > 0:
            header = lines[i - 1]
            if not header.strip().startswith("|"):
                continue
            cells = [c.strip().strip("`* ") for c in header.strip().strip("|").split("|")]
            for c in cells:
                if c in ("按钮", "操作按钮", "按钮名称"):
                    hits.append(" ".join(header.strip().split()))
                    break
    return hits


def slice_page_sections(text):
    """把（去代码块后的）文本按 ### 标题切成页面小节。
    返回 [(title, body)]；只取位于 `## 功能设计详情` 之后、下一个 ## 之前的 ### 小节。
    """
    plain = strip_fences(text)
    lines = plain.split("\n")

    # 定位「功能设计详情」二级标题
    start = None
    for i, line in enumerate(lines):
        m = ANY_HEADING_RE.match(line)
        if m and len(m.group(1)) == 2 and "功能设计详情" in m.group(2):
            start = i + 1
            break
    if start is None:
        return []

    # 找到其后的下一个 ##
    end = len(lines)
    for i in range(start, len(lines)):
        m = ANY_HEADING_RE.match(lines[i])
        if m and len(m.group(1)) <= 2:
            end = i
            break

    pages = []
    cur_title, cur_body = None, []
    for line in lines[start:end]:
        m = PAGE_HEADING_RE.match(line)
        if m:
            if cur_title is not None:
                pages.append((cur_title, "\n".join(cur_body)))
            cur_title, cur_body = m.group(2), []
        elif cur_title is not None:
            cur_body.append(line)
    if cur_title is not None:
        pages.append((cur_title, "\n".join(cur_body)))
    return pages


def wireframe_blocks(text):
    """找出「页面线框图」代码块。

    判定规则：非 mermaid 的围栏代码块，且其**最近的上级标题**含「布局」或「线框」。
    返回 [(heading, body)]。
    文件树 / 代码结构树 / 流程示意（标题不含上述词）**不计入**——它们允许用 Unicode 连接符。
    """
    results = []
    heading = ""
    for kind, payload in split_blocks(text):
        if kind == "text":
            for line in payload.split("\n"):
                m = ANY_HEADING_RE.match(line)
                if m:
                    heading = m.group(2).strip()
        else:
            lang, body = payload
            if lang in ("mermaid",):
                continue
            if ("布局" in heading) or ("线框" in heading):
                results.append((heading, body))
    return results


def collect_ac_ids(text):
    """返回 (valid_ids, invalid_candidates)。

    valid  ：形如 AC-USER-01 的合法编号（保留出现顺序，含重复项，供唯一性判断）
    invalid：写了 AC- 前缀但格式不合规的候选串（去重后排序）
    """
    cands = AC_CANDIDATE_RE.findall(text)
    valid = [c for c in cands if AC_VALID_RE.fullmatch(c)]
    invalid = sorted({c for c in cands if not AC_VALID_RE.fullmatch(c)})
    return valid, invalid


def _is_scope_title(title):
    """判断标题是否代表「弹窗 / 抽屉 / 步骤 / tab」这一级元素（C15 / C5 用）。

    只按**后缀**判定，不做「包含即排除」——否则「查看用户详情弹窗」会因为标题里
    有个「详情」被误杀，而它确实是一个弹窗。元素内部的内容块（`字段字典（弹窗表单）`、
    `弹窗布局图`、`弹窗概要`、`交互矩阵（弹窗内）`）后缀都不是这些词，天然不会命中。
    """
    t = title.strip().rstrip("：: ")
    low = t.lower()
    if t.startswith("步骤") or "多步骤" in t or "子tab" in low:
        return True
    return t.endswith(AC_SCOPE_SUFFIX)


def scope_subsections(section_body):
    """切出「弹窗 / 抽屉 / 步骤 / tab」级子小节，返回 [(title, body)]。

    边界：该标题 → 下一个「层级 <= 自己」的标题。
    """
    lines = section_body.split("\n")
    heads = []
    for i, line in enumerate(lines):
        m = ANY_HEADING_RE.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    out = []
    for k, (i, lvl, title) in enumerate(heads):
        if lvl < 4 or not _is_scope_title(title):
            continue
        end = len(lines)
        for j, l2, _t in heads[k + 1:]:
            if l2 <= lvl:
                end = j
                break
        out.append((title, "\n".join(lines[i:end])))
    return out


def tables_by_scope(page_body):
    """按「页面主体 + 各自弹窗/抽屉/步骤/tab」分别统计表格数，返回 [(作用域名, 表数)]。

    V2 约束是「每个页面 / 弹窗 ≤ 2 张表」，所以必须**分作用域**统计 —— 把整段页面
    （页面主体 + 所有弹窗）加总会得出 2 + 2×N 的假超标。
    """
    lines = page_body.split("\n")
    heads = []
    for i, line in enumerate(lines):
        m = ANY_HEADING_RE.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    sub_ranges = []
    for k, (i, lvl, title) in enumerate(heads):
        if lvl < 4 or not _is_scope_title(title):
            continue
        end = len(lines)
        for j, l2, _t in heads[k + 1:]:
            if l2 <= lvl:
                end = j
                break
        sub_ranges.append((i, end, title))

    # 页面主体 = 挖掉所有弹窗级子节之后的剩余部分
    mask = [True] * len(lines)
    for i, end, _t in sub_ranges:
        for x in range(i, end):
            mask[x] = False
    main = "\n".join(l for idx, l in enumerate(lines) if mask[idx])

    scopes = [("页面主体", count_tables(main))]
    for i, end, title in sub_ranges:
        scopes.append((title, count_tables("\n".join(lines[i:end]))))
    return scopes


# ---------------------------------------------------------------- 检查

def validate(path):
    findings = []
    if not os.path.isfile(path):
        findings.append(Finding("FAIL", "C0", "文件不存在或不是文件", path))
        return findings

    text = read_text(path)
    plain = strip_fences(text)

    for error in required(text, ['业务流程', '页面清单', '功能设计详情', '全局检查']):
        findings.append(Finding('FAIL', 'C16', error, path))
    from check_freshness import page_names
    listed = page_names(plain)
    detailed = [re.sub(r'^\d+[.、\s]*', '', title).strip() for title, _ in slice_page_sections(text)]
    if not listed or len(listed) != len(set(listed)) or set(listed) != set(detailed) or len(detailed) != len(set(detailed)):
        findings.append(Finding('FAIL', 'C17', '页面清单必须非空、唯一，并与页面详情名称一一对应：清单=%s，详情=%s' % (listed, detailed), path))

    # C1 必需章节
    heads = collect_headings(text)
    titles = [t for _lvl, t in heads]
    for sec in REQUIRED_SECTIONS:
        if not any(sec in t for t in titles):
            findings.append(Finding("FAIL", "C1", "缺少必需章节：%s" % sec, path))

    # C2 / C3 Mermaid
    mermaid_blocks = [body for kind, payload in split_blocks(text)
                      if kind == "fence" and payload[0] == "mermaid"
                      for body in [payload[1]]]
    if not mermaid_blocks:
        findings.append(Finding("FAIL", "C2", "没有找到任何 ```mermaid 代码块（需至少 1 个真实流程图）", path))
    else:
        for bi, body in enumerate(mermaid_blocks, 1):
            bad = sorted(set(ch for ch in body if ch in FULLWIDTH_CHARS))
            if bad:
                findings.append(Finding(
                    "FAIL", "C3",
                    "第 %d 个 Mermaid 代码块含全角标点：%s（参照 mermaid-guide.md）"
                    % (bi, " ".join(bad)), path))

    for error in mermaid_errors(mermaid_blocks):
        findings.append(Finding('FAIL', 'C18', error, path))

    # C4 按钮单独成表
    btn_tables = find_button_tables(plain)
    if btn_tables:
        for hdr in btn_tables[:5]:
            findings.append(Finding("FAIL", "C4", "疑似「按钮操作单独成表」：%s" % hdr, path))

    # C12 / C13 AC 编号（格式 + 唯一性）
    ac_valid, ac_invalid = collect_ac_ids(plain)
    if ac_invalid:
        findings.append(Finding(
            "FAIL", "C12",
            "AC 编号格式不合法：%s —— 应为 AC-<2~8位大写模块缩写>-<两位序号>，"
            "例如 AC-USER-01（见 product-design-spec.md 第 6 节）"
            % " ".join(ac_invalid[:6]), path))
    if ac_valid:
        for a in sorted({x for x in ac_valid if ac_valid.count(x) > 1}):
            findings.append(Finding(
                "FAIL", "C13",
                "AC 编号重复定义：%s（出现 %d 次）—— 编号须全文唯一"
                % (a, ac_valid.count(a)), path))

    # 页面级检查
    pages = slice_page_sections(text)
    if not pages:
        findings.append(Finding("FAIL", "C5", "未能识别出 `### <页面名称>` 形式的页面小节，无法完成页面级检查，阻断", path))

    for title, body in pages:
        for label in ('字段字典', '交互矩阵'):
            matches = [content for heading, content in strict_sections(body) if label in heading]
            if not matches or not all(populated_tables(content) > 0 for content in matches):
                findings.append(Finding('FAIL', 'C19', '页面「%s」的%s须含实际表格内容' % (title, label), path))
        # C5 表格数（分作用域：页面主体 + 各弹窗/抽屉/步骤/tab 各自统计）
        for scope_name, n_tab in tables_by_scope(body):
            if n_tab > 2:
                findings.append(Finding(
                    "FAIL", "C5",
                    "「%s」的 %s 下有 %d 张表（V2 约束 ≤2：字段字典 + 交互矩阵）"
                    % (title, scope_name, n_tab), path))

        # C6 字段字典
        if "字段字典" not in body and "字段规格" not in body:
            findings.append(Finding("FAIL", "C6", "页面「%s」未见「字段字典」小节" % title, path))

        # C8 交互矩阵
        if "交互矩阵" not in body and "交互说明" not in body:
            findings.append(Finding("FAIL", "C8", "页面「%s」未见「交互矩阵」小节" % title, path))

        # C14 每个页面至少 1 条 AC
        page_ac, page_bad = collect_ac_ids(body)
        if not page_ac and not page_bad:
            # 写了 AC- 但格式不合法的情况由 C12 报，这里不重复报
            findings.append(Finding(
                "FAIL", "C14",
                "页面「%s」没有任何验收标准（AC）—— 每个页面/弹窗至少 1 条" % title, path))
        if page_ac:
            # C15 弹窗/抽屉/步骤/tab 子节应各自列出 AC
            lacking = [t for t, sub in scope_subsections(body)
                       if not collect_ac_ids(sub)[0]]
            if lacking:
                findings.append(Finding(
                    "WARN", "C15",
                    "页面「%s」下这些子节未见 AC：%s（若页面级 AC 已覆盖可忽略）"
                    % (title, "、".join(lacking[:4])), path))

    # C7 / C10 / C11 页面线框图
    wireframes = wireframe_blocks(text)
    if not wireframes:
        findings.append(Finding(
            "WARN", "C7",
            "未检出页面线框图（「页面布局设计详情」下应有 ``` 包裹的 ASCII 图）", path))
    else:
        box_hits, sym_hits = set(), set()
        for _heading, body in wireframes:
            box_hits |= {ch for ch in body if ch in BOX_CHARS}
            sym_hits |= {c for c in NON_ASCII_SYMBOL_RE.findall(body)
                         if c not in WIREFRAME_ALLOWED}
        if box_hits:
            findings.append(Finding(
                "FAIL", "C10",
                "页面线框图混入 Unicode 框线字符 %s —— 须改用 ASCII 的 + - |"
                "（文件树/流程示意不受此限）" % " ".join(sorted(box_hits)), path))
        if sym_hits:
            findings.append(Finding(
                "FAIL", "C11",
                "页面线框图出现 emoji / 宽度不定的符号 %s —— 改用单宽几何符号"
                "（▼ □ ☑ ☐ ● ○ 等）或文字标记（(o) (x) [编辑]）"
                % " ".join(sorted(sym_hits)), path))

    # C9 越界内容
    for hint in BOUNDARY_HINTS:
        if hint in plain:
            findings.append(Finding(
                "WARN", "C9",
                "检出疑似技术侧内容「%s」，产品设计文档不应包含技术选型/DDL（移交 product-architecture）"
                % hint, path))
            break

    if not any(f.level == "FAIL" for f in findings):
        findings.append(Finding("PASS", "OK", "全部硬性检查通过", path))
    return findings


# ---------------------------------------------------------------- 输出

def render_text(all_findings):
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
    ap = argparse.ArgumentParser(description="产品设计文档门禁硬校验器")
    ap.add_argument("--doc", required=True, nargs="+",
                    help="待校验的设计文档路径（支持多个，支持 shell 通配）")
    ap.add_argument("--json", action="store_true", help="输出机读 JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    args = ap.parse_args(argv)

    paths = []
    for pattern in args.doc:
        hits = glob.glob(pattern)
        paths.extend(hits if hits else [pattern])

    all_findings = [(p, validate(p)) for p in paths]

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
    else:
        if args.quiet:
            for path, findings in all_findings:
                fails = sum(1 for f in findings if f.level == "FAIL")
                warns = sum(1 for f in findings if f.level == "WARN")
                verdict = "FAIL" if fails else ("PASS(WARN)" if warns else "PASS")
                print("%s  %s  (FAIL=%d WARN=%d)" % (verdict, path, fails, warns))
        else:
            print(render_text(all_findings))

    has_fail = any(f.level == "FAIL" for _p, fs in all_findings for f in fs)
    return 1 if has_fail else 0


if __name__ == "__main__":
    sys.exit(main())
