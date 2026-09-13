#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_e2e_spec.py —— E2E 静态引用检查器（不证明实际执行）

把「产品设计文档里的验收标准（AC）」和「Playwright 用例」对起来查，两个方向都看：

    E1 WARN 静态 E2E 未引用：实际覆盖由结项器读取单元/API/E2E 报告
    E2 FAIL 悬空：用例引用了设计文档里不存在的 AC 编号
    E3 FAIL 用例里的 AC 编号格式不合法（出现 AC- 前缀但不符合编号规则）
    E4 WARN 某个 spec 文件完全没有 AC 标注
    E5 FAIL 设计文档里一条 AC 也没有（文档可能还没写验收标准）

编号规则（与 product-design 的 AC 规范一致）：
    AC-<2~8 位大写模块缩写>-<两位序号>，例如 AC-USER-01

用法:
    python3 validate_e2e_spec.py --design-doc <项目根>/项目战术执行/00_产品设计文档.md \
                                 --spec-dir  <项目根>/frontend/tests/e2e
    python3 validate_e2e_spec.py --design-doc ... --spec-dir ... --json
    python3 validate_e2e_spec.py --design-doc ... --spec-dir ... --quiet

退出码: 0 = 无 FAIL；1 = 存在 FAIL；2 = 用法错误
"""

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "product-workflow" / "scripts"))
from workflow_config import spec_files, DEFAULTS

# —— 与 product-design 的 AC 编号规则保持同一套（此处自带一份，避免跨 skill 运行时耦合）——
AC_VALID_RE = re.compile(r"AC-[A-Z][A-Z0-9]{1,7}-[0-9]{2}")
AC_CANDIDATE_RE = re.compile(r"AC-[A-Za-z0-9\u4e00-\u9fff]+(?:-[A-Za-z0-9\u4e00-\u9fff]+)*")

SPEC_EXTS = DEFAULTS["spec_extensions"]


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


def collect_ac_ids(text):
    """返回 (valid_ids 保留顺序, invalid_candidates 去重排序)"""
    cands = AC_CANDIDATE_RE.findall(text)
    valid = [c for c in cands if AC_VALID_RE.fullmatch(c)]
    invalid = sorted({c for c in cands if not AC_VALID_RE.fullmatch(c)})
    return valid, invalid


def find_spec_files(spec_dir, extensions=None):
    return spec_files(spec_dir, extensions or SPEC_EXTS)


# ---------------------------------------------------------------- 校验

def validate(design_doc, spec_dir, extensions=None):
    findings = []

    # 设计文档侧
    if not os.path.isfile(design_doc):
        findings.append(Finding("FAIL", "E0", "设计文档不存在：%s" % design_doc))
        return findings
    doc_valid, doc_bad = collect_ac_ids(read_text(design_doc))
    doc_set = set(doc_valid)
    if not doc_set:
        findings.append(Finding(
            "FAIL", "E5",
            "设计文档《%s》里没有任何合法的 AC 编号 —— 请先在产品设计文档里补「验收标准」"
            % os.path.basename(design_doc)))

    # 用例侧
    specs = find_spec_files(spec_dir, extensions)
    if specs is None:
        findings.append(Finding("FAIL", "E0", "用例目录不存在：%s" % spec_dir))
        return findings
    if not specs:
        findings.append(Finding("FAIL", "E4", "用例目录下没有找到 *.spec.ts 文件：%s" % spec_dir))

    ref_map = {}        # ac -> [文件]
    no_ac_files = []
    bad_tokens = {}     # 非法编号 -> [文件]
    for p in specs:
        txt = read_text(p)
        executable = re.sub(r'/\*.*?\*/|//[^\n]*', '', txt, flags=re.S)
        if not re.search(r'\b(?:test|it)(?:\.(?:only|skip|fixme|fail))?\s*\(', executable):
            findings.append(Finding('FAIL', 'E6', '文件没有可识别的测试声明（注释不算测试）：' + os.path.basename(p)))
        valid, invalid = collect_ac_ids(txt)
        for a in set(valid):
            ref_map.setdefault(a, []).append(os.path.basename(p))
        if not valid:
            no_ac_files.append(os.path.basename(p))
        for t in invalid:
            bad_tokens.setdefault(t, []).append(os.path.basename(p))

    # E3 编号格式
    for t in sorted(bad_tokens):
        findings.append(Finding(
            "FAIL", "E3",
            "用例中的 AC 编号「%s」格式不合法（%s）—— 应为 AC-<2~8位大写模块缩写>-<两位序号>，"
            "例如 AC-USER-01" % (t, "、".join(bad_tokens[t][:3]))))

    # E1 漏测
    missing = sorted(doc_set - set(ref_map))
    for a in missing:
        findings.append(Finding(
            "WARN", "E1", "静态 E2E 未引用 %s；是否已由单元/API/E2E 验证，须读取执行报告判断" % a))

    # E2 悬空
    dangling = sorted(set(ref_map) - doc_set)
    for a in dangling:
        where = "、".join(ref_map[a][:3])
        findings.append(Finding(
            "FAIL", "E2",
            "悬空：用例引用了设计文档里不存在的 %s（%s）—— 编号写错了，或设计文档已删改" % (a, where)))

    # E4 无标注的用例文件
    for f in sorted(no_ac_files):
        findings.append(Finding("WARN", "E4", "用例文件 %s 没有任何 AC 标注" % f))

    if not any(f.level == "FAIL" for f in findings):
        findings.append(Finding(
            "PASS", "OK",
            "静态引用检查通过：文档 %d 条 AC，用例引用 %d 条；不代表执行通过或断言有效" % (len(doc_set), len(ref_map))))
    return findings


# ---------------------------------------------------------------- 输出

def render(findings, design_doc, spec_dir):
    order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    lines = ["=" * 72,
             "设计文档: %s" % design_doc,
             "用例目录: %s" % spec_dir,
             "=" * 72]
    for f in sorted(findings, key=lambda x: order.get(x.level, 9)):
        tag = {"FAIL": "[FAIL]", "WARN": "[WARN]", "PASS": "[PASS]"}[f.level]
        lines.append("  %s %-3s %s" % (tag, f.code, f.message))
    fails = sum(1 for f in findings if f.level == "FAIL")
    warns = sum(1 for f in findings if f.level == "WARN")
    verdict = "FAIL" if fails else ("PASS(WARN)" if warns else "PASS")
    lines.append("  --> 结论: %s  (FAIL=%d WARN=%d)" % (verdict, fails, warns))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="E2E 静态引用检查器（不证明实际执行）")
    ap.add_argument("--design-doc", required=True, help="产品设计文档路径（00_产品设计文档.md）")
    ap.add_argument("--spec-dir", required=True, help="Playwright 用例目录（frontend/tests/e2e）")
    ap.add_argument("--extensions", nargs="+", default=SPEC_EXTS, help="测试扩展名；由项目配置统一提供")
    ap.add_argument("--json", action="store_true", help="输出机读 JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    args = ap.parse_args(argv)

    findings = validate(args.design_doc, args.spec_dir, args.extensions)
    fails = sum(1 for f in findings if f.level == "FAIL")
    warns = sum(1 for f in findings if f.level == "WARN")
    verdict = "FAIL" if fails else ("PASS(WARN)" if warns else "PASS")

    if args.json:
        # 与同族其他校验器保持一致：输出**数组**（每份产物一个元素）
        print(json.dumps([{
            "design_doc": args.design_doc,
            "spec_dir": args.spec_dir,
            "verdict": verdict, "fail": fails, "warn": warns,
            "findings": [f.as_dict() for f in findings],
        }], ensure_ascii=False, indent=2))
    elif args.quiet:
        print("%s  (FAIL=%d WARN=%d)" % (verdict, fails, warns))
    else:
        print(render(findings, args.design_doc, args.spec_dir))

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
