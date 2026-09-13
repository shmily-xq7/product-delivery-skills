"""Version-bound local execution evidence. Hash checks establish consistency, not trust in an author."""
import hashlib
import json
import re
from pathlib import Path
from workflow_config import local_path, document_paths

EXCLUDED = {'node_modules', '.git', '.product-workflow', 'dist', 'build', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.venv', 'venv', 'test-results', 'playwright-report', 'coverage'}
SOURCE_EXT = {'.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs', '.java', '.vue', '.svelte', '.c', '.cpp', '.cs', '.swift', '.kt'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def input_digest(root, cfg):
    """Conservative project input snapshot; generated reports/logs are outside these roots."""
    files = set()
    for relative in (cfg['paths']['requirement'], cfg['paths']['execution'], cfg['paths']['frontend'], cfg['paths']['backend'], cfg['paths']['e2e']):
        path = local_path(root, relative)
        for item in ([path] if path.is_file() else path.rglob('*') if path.is_dir() else []):
            rel = item.relative_to(Path(root).resolve())
            if item.is_file() and not any(x in EXCLUDED for x in rel.parts) and not item.name.startswith(('90_诊断报告_', '99_交付清单')) and item.suffix not in {'.pyc', '.log'} and item.name != '.DS_Store':
                files.add(str(rel))
    # Root build configuration and dependency locks also affect execution.
    for item in Path(root).resolve().iterdir():
        if item.is_file() and item.suffix in {'.json', '.toml', '.yaml', '.yml', '.lock', '.ini', '.cfg', '.txt'}:
            files.add(item.name)
    payload = {'config': cfg, 'files': [(name, digest(local_path(root, name))) for name in sorted(files)]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def has_source(root, relative):
    path = local_path(root, relative)
    return path.is_dir() and any(p.is_file() and p.suffix in SOURCE_EXT and p.stat().st_size > 0 and not any(x in EXCLUDED for x in p.relative_to(path).parts) for p in path.rglob('*'))


def approval(root, cfg):
    try:
        data = json.loads(local_path(root, '.product-workflow/approval.json').read_text())
        required = ('confirmed_by', 'confirmed_at', 'confirmation_reference')
        if data.get('schema_version') != 1 or any(not isinstance(data.get(k), str) or not data[k].strip() for k in required):
            return False, '人工确认记录字段缺失'
        if data.get('requirement_sha256') != digest(local_path(root, cfg['paths']['requirement'])):
            return False, '人工确认对应的需求版本已变化'
        return True, '存在绑定当前需求的人工确认记录（记录真实性仍由人负责）'
    except (OSError, ValueError, TypeError, AttributeError):
        return False, '缺少或无法读取 .product-workflow/approval.json；不得由模型虚构确认'


def required_checks(cfg):
    return [name for name in cfg['commands'] if name not in cfg['exemptions']]


def current_evidence(root, cfg, name):
    try:
        index = json.loads(local_path(root, '.product-workflow/latest.json').read_text())
        path = local_path(root, index[name])
        data = json.loads(path.read_text())
        if data.get('schema_version') != 1 or data.get('check') != name or data.get('command') != cfg['commands'][name]:
            raise ValueError('执行配置不匹配')
        if data.get('exit_code') != 0 or data.get('input_before') != data.get('input_after') or data.get('input_after') != input_digest(root, cfg):
            raise ValueError('最近执行失败、执行期间输入变化或证据已过期')
        if digest(local_path(root, data['log'])) != data['log_sha256']:
            raise ValueError('日志不匹配')
        if cfg['commands'][name].get('report') == 'junit':
            if digest(local_path(root, data['report'])) != data['report_sha256']:
                raise ValueError('测试报告不匹配')
            junit_cases(local_path(root, data['report']))
        return data, 'PASS（当前输入版本）'
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return None, 'MISSING/STALE: ' + str(error)


def junit_cases(path):
    """Read actual testcase records, never infer execution from aggregate counts or comments."""
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as error:
        raise ValueError('JUnit 报告不可解析：' + str(error))
    root = tree.getroot()
    tag = lambda element: element.tag.rsplit('}', 1)[-1]
    if tag(root) not in ('testsuite', 'testsuites'):
        raise ValueError('不是 JUnit 报告')
    rows = []
    for element in root.iter():
        if tag(element) in ('testsuite', 'testsuites'):
            for key in ('failures', 'errors'):
                if float(element.get(key, '0')) != 0:
                    raise ValueError('JUnit 含失败或错误')
        if tag(element) == 'testcase':
            children = {tag(child) for child in element}
            if children & {'failure', 'error'}:
                raise ValueError('JUnit 含失败测试')
            if not element.get('name'):
                raise ValueError('测试缺少名称')
            rows.append({'name': element.get('name'), 'classname': element.get('classname', ''), 'passed': 'skipped' not in children and element.get('status', '').lower() not in ('notrun', 'disabled', 'skipped')})
    if not any(row['passed'] for row in rows):
        raise ValueError('JUnit 没有实际执行通过的测试（零测试或全部跳过）')
    return rows


def executed_coverage(root, cfg):
    covered, identities, problems = set(), set(), []
    ac_pattern = re.compile(r'\bAC-[A-Z][A-Z0-9]{1,7}-[0-9]{2}\b')
    for check in required_checks(cfg):
        command = cfg['commands'][check]
        if command.get('report') != 'junit':
            if check in ('backend', 'e2e'):
                problems.append(check + ' 必须配置 report=junit')
            continue
        item, note = current_evidence(root, cfg, check)
        if item is None:
            problems.append(check + ': ' + note); continue
        try:
            for row in junit_cases(local_path(root, item['report'])):
                if row['passed']:
                    covered.update(ac_pattern.findall(row['name']))
                    identities.add((check, row['classname'], row['name']))
        except ValueError as error:
            problems.append(check + ': ' + str(error))
    for ac, tests in cfg['ac_tests'].items():
        # Every explicitly mapped test for this AC must execute and pass.
        if tests and all((t['check'], t['classname'], t['name']) in identities for t in tests):
            covered.add(ac)
        else:
            covered.discard(ac)
            problems.append(ac + ' 的显式映射包含未通过或未执行的测试')
    return covered, problems
