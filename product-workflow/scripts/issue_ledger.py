"""Structured blockers plus conservative migration of every legacy unresolved section."""
import hashlib
import json
from pathlib import Path
import re
from delivery_evidence import digest, input_digest
from workflow_config import local_path
from strict_docs import sections


def legacy_sections(root, cfg):
    found = []
    for path in sorted(local_path(root, cfg['paths']['execution']).glob('90_诊断报告_*.md')):
        for heading, body in sections(path.read_text(encoding='utf-8')):
            if not re.search('未确认|待处理|未解决', heading):
                continue
            # Nested headings are part of the section, not a reason to stop scanning.
            normalized = body.strip()
            if normalized in ('无', '无。', '暂无', '-', '（无）'):
                continue
            found.append((str(path.relative_to(Path(root).resolve())), hashlib.sha256(normalized.encode()).hexdigest(), normalized or '空白未确认章节：尚未完成检查'))
    return found


def collect(root, cfg):
    unresolved, resolved_sources = [], set()
    try:
        data = json.loads(local_path(root, '.product-workflow/issues.json').read_text())
        if data.get('schema_version') != 1 or not isinstance(data.get('issues'), list) or not all(isinstance(data.get(k), str) and data[k].strip() for k in ('reviewed_by', 'reviewed_at')):
            raise ValueError('问题台账结构或复核记录缺失')
        if data.get('input_sha256') != input_digest(root, cfg):
            raise ValueError('问题台账尚未针对当前输入复核')
        seen = set()
        for issue in data['issues']:
            if not isinstance(issue, dict) or not all(isinstance(issue.get(k), str) and issue[k].strip() for k in ('id','title','owner')) or issue['id'] in seen:
                raise ValueError('问题 ID/标题/负责人缺失或 ID 重复')
            seen.add(issue['id'])
            if type(issue.get('blocking')) is not bool or issue.get('severity') not in ('critical','high','medium','low') or issue.get('status') not in ('open','resolved','accepted'):
                raise ValueError('问题状态、级别或阻断标记不合法：'+issue['id'])
            if issue['status'] == 'open':
                if issue['blocking']:
                    unresolved.append((issue['id'], issue['title']))
                continue
            resolution = issue.get('resolution', {})
            proofs = resolution.get('evidence') if isinstance(resolution, dict) else None
            if not resolution.get('summary') or not isinstance(proofs, list) or not proofs:
                raise ValueError('关闭问题必须提供解决说明与证据：'+issue['id'])
            for proof in proofs:
                if not isinstance(proof, dict) or digest(local_path(root, proof['path'])) != proof['sha256']:
                    raise ValueError('问题关闭证据缺失或发生变化：'+issue['id'])
            if issue['status'] == 'accepted':
                accepted = issue.get('acceptance', {})
                if not all(isinstance(accepted.get(k), str) and accepted[k].strip() for k in ('confirmed_by','confirmation_reference')):
                    raise ValueError('接受风险必须记录真实人工确认：'+issue['id'])
            for source in issue.get('legacy_sources', []):
                local_path(root, source['path'])
                resolved_sources.add((source['path'], source['body_sha256']))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        unresolved.append(('问题台账 UNKNOWN', str(error)))
        resolved_sources.clear()
    for path, body_hash, body in legacy_sections(root, cfg):
        if (path, body_hash) not in resolved_sources:
            unresolved.append((path, body[:300]))
    return unresolved
