"""Execute selected checks; save version-bound evidence and compact summaries. No implicit command execution."""
import argparse
import datetime
import json
import os
import shutil
from pathlib import Path
import subprocess
from workflow_config import load_config, local_path
from delivery_evidence import input_digest, digest, current_evidence


def _run_unlocked(root, names, force=False):
    root = Path(root).resolve()
    cfg = load_config(root)
    if not names or any(name not in cfg['commands'] for name in names):
        raise ValueError('请指定已配置的检查项')
    planned = [(name, cfg['commands'][name]) for name in names]
    for name, command in planned:
        if not local_path(root, command['cwd']).is_dir():
            raise ValueError('工作目录不存在: ' + command['cwd'])
    directory = root / '.product-workflow' / 'runs' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    directory.mkdir(parents=True)
    index_path = root / '.product-workflow/latest.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    results = []
    for number, (name, command) in enumerate(planned):
        cached, note = current_evidence(root, cfg, name)
        if cached and not force:
            print(name + ': REUSED（当前输入版本的通过证据；--force 可重跑）')
            results.append(cached)
            continue
        logfile = directory / ('%02d.log' % number)
        report = directory / ('%02d.junit.xml' % number)
        before = input_digest(root, cfg)
        argv = [arg.replace('{report}', str(report)) for arg in command['argv']]
        env = os.environ.copy()
        if command.get('report') == 'junit':
            env['PLAYWRIGHT_JUNIT_OUTPUT_FILE'] = str(report)
        # Invalidate the old pass before starting; interrupted runs cannot reuse it.
        evidence_path = directory / ('%02d.json' % number)
        evidence_path.write_text('{}\n')
        index[name] = str(evidence_path.relative_to(root))
        tmp = index_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
        tmp.replace(index_path)
        with logfile.open('w', encoding='utf-8') as log:
            try:
                result = subprocess.run(argv, cwd=local_path(root, command['cwd']), stdout=log, stderr=subprocess.STDOUT, timeout=600, env=env)
                code = result.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                log.write(str(error)); code = 2
        item = {'schema_version': 1, 'check': name, 'cwd': command['cwd'], 'argv': command['argv'], 'command': command,
                'exit_code': code, 'input_before': before, 'input_after': input_digest(root, cfg),
                'log': str(logfile.relative_to(root)), 'log_sha256': digest(logfile)}
        if command.get('report') == 'junit' and report.is_file():
            item.update(report=str(report.relative_to(root)), report_sha256=digest(report))
        evidence_path.write_text(json.dumps(item, ensure_ascii=False, indent=2) + '\n')
        results.append(item)
        valid, note = current_evidence(root, cfg, name)
        print('%s: %s; %s' % (name, note, logfile))
        if not valid:
            item['evidence_invalid'] = True
    (directory / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    return int(any(item['exit_code'] != 0 or item.get('evidence_invalid') for item in results))


def run(root, names, force=False):
    lock = Path(root).resolve() / '.product-workflow/checks.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('检查正在执行或存在遗留锁；核对 checks.lock/pid 后处理，不能并发覆盖最新证据')
    try:
        (lock / 'pid').write_text(str(os.getpid()))
        return _run_unlocked(root, names, force)
    finally:
        shutil.rmtree(lock)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--check', nargs='+', required=True)
    parser.add_argument('--force', action='store_true', help='忽略同版本通过证据，重新执行（环境或外部服务变化时使用）')
    args = parser.parse_args()
    try:
        raise SystemExit(run(args.project_root, args.check, args.force))
    except (ValueError, OSError) as error:
        parser.exit(2, 'ERROR: %s\n' % error)
