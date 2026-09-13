"""Shared required-content checks and actual Mermaid syntax parsing."""
import json
from pathlib import Path
import re
import subprocess


def sections(text):
    lines = text.splitlines(); heads = []; fence = False
    for index, line in enumerate(lines):
        if re.match(r'^\s*(```|~~~)', line):
            fence = not fence; continue
        match = re.match(r'^(#{1,6})\s+(.+)', line)
        if match and not fence:
            heads.append((index, len(match[1]), match[2]))
    result = []
    for i, (start, level, title) in enumerate(heads):
        end = next((n for n, depth, _ in heads[i+1:] if depth <= level), len(lines))
        result.append((title, '\n'.join(lines[start+1:end])))
    return result


def meaningful(body):
    lines = [x.strip() for x in body.splitlines() if x.strip() and not x.lstrip().startswith(('#', '>', '<!--'))]
    text = '\n'.join(lines)
    return bool(text) and not re.fullmatch(r'[\s*`\-|:]*|(?:待补充|TODO|TBD|待定|暂无|无)[。.\s]*', text, re.I)


def na(text, area):
    matches = re.findall(r'^\s*N/A\['+re.escape(area)+r'\]\s*[:：]\s*(.+)$', text, re.M)
    return bool(matches) and all(len(x.strip()) >= 8 and meaningful(x) and not re.search('待补充|TODO|TBD|待定', x, re.I) for x in matches)


def required(text, names):
    found = sections(text)
    return ['缺少或为空的必需章节：'+name for name in names if not any(name in title and meaningful(body) for title, body in found)]


def mermaid_errors(blocks):
    if not blocks:
        return ['缺少 Mermaid 图']
    script = Path(__file__).resolve().parents[1]/'validators/mermaid.mjs'
    try:
        run = subprocess.run(['node',str(script)], input=json.dumps(blocks), text=True, capture_output=True, timeout=60)
        if run.returncode != 0:
            return ['Mermaid 语法未验证：运行时缺失或异常；请重新安装完整技能包。'+run.stderr[:200]]
        data = json.loads(run.stdout)
        if not isinstance(data, list) or len(data) != len(blocks) or any(not isinstance(x, dict) or type(x.get('ok')) is not bool for x in data):
            raise ValueError('解析器返回格式异常')
        return ['Mermaid 图 %d 语法错误：%s' % (i+1, x.get('error','unknown')) for i,x in enumerate(data) if not x['ok']]
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return ['Mermaid 语法未验证：'+str(error)]


def populated_tables(text):
    lines = text.splitlines(); count = 0
    for i, line in enumerate(lines):
        if re.fullmatch(r'\s*\|[\s:|\-]+\|\s*', line) and i > 0 and lines[i-1].strip().startswith('|'):
            if i+1 < len(lines) and lines[i+1].strip().startswith('|'):
                cells = lines[i+1].strip().strip('|').split('|')
                if any(meaningful(c.strip().strip('`*')) for c in cells):
                    count += 1
    return count
