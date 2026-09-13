import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'product-workflow/scripts'))
import check_freshness as workflow
import workflow_config as config
import delivery_evidence as evidence
import run_checks


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
    def put(self, path, text):
        p = self.root / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text); return p
    def configure(self, data):
        self.put('product-workflow.json', json.dumps(data)); return config.load_config(self.root)
    def execute(self, names, force=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return run_checks.run(self.root, names, force)
    def test_empty_directory_and_only_module_cannot_finalize(self):
        (self.root/'frontend').mkdir()
        self.put('项目战术执行/01_用户详细设计.md', '> **生成元信息**\n> 基于：\n')
        _, ready, _ = workflow.finalize(str(self.root))
        self.assertFalse(ready)
        self.assertFalse(evidence.has_source(self.root, 'frontend'))
        self.assertTrue(all(x[2] == '未检测' for x in workflow.run_gates(str(self.root), ('design', 'arch', 'e2e'))))
    def test_nonzero_validator_cannot_pass_using_json(self):
        with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 2, '[{"fail":0,"warn":0}]', 'oops')):
            self.assertIsNone(workflow._run_json(['unused']))
    def test_requirement_approval_is_bound_to_version(self):
        cfg = config.load_config(self.root)
        req = self.put(cfg['paths']['requirement'], '交付范围：全链\n用户管理')
        self.assertFalse(evidence.approval(self.root, cfg)[0])
        self.put('.product-workflow/approval.json', json.dumps({'schema_version':1, 'requirement_sha256':evidence.digest(req), 'confirmed_by':'test-user', 'confirmed_at':'2026-09-12T00:00:00Z', 'confirmation_reference':'test-only synthetic fixture'}))
        self.assertTrue(evidence.approval(self.root, cfg)[0])
        req.write_text(req.read_text() + '\n新增规则')
        self.assertFalse(evidence.approval(self.root, cfg)[0])
    def test_evidence_reuse_changes_and_latest_failure(self):
        cfg = self.configure({'commands': {'typecheck': {'cwd':'frontend','argv':[sys.executable, 'check.py']}}})
        code = self.put('frontend/check.py', 'print("actual execution")\n')
        self.assertEqual(self.execute(['typecheck']), 0)
        index = (self.root/'.product-workflow/latest.json').read_text()
        self.assertEqual(self.execute(['typecheck']), 0)
        self.assertEqual(index, (self.root/'.product-workflow/latest.json').read_text())
        self.assertIsNotNone(evidence.current_evidence(self.root, cfg, 'typecheck')[0])
        code.write_text('raise SystemExit(1)\n')
        self.assertIsNone(evidence.current_evidence(self.root, cfg, 'typecheck')[0])
        self.assertEqual(self.execute(['typecheck']), 1)
        code.write_text('print("actual execution")\n')
        self.assertIsNone(evidence.current_evidence(self.root, cfg, 'typecheck')[0])
    def test_modified_log_invalidates_pass(self):
        cfg = self.configure({'commands': {'typecheck': {'cwd':'frontend','argv':[sys.executable, 'check.py']}}})
        self.put('frontend/check.py','print("ok")')
        self.execute(['typecheck'])
        data, _ = evidence.current_evidence(self.root, cfg, 'typecheck')
        self.put(data['log'], 'modified')
        self.assertIsNone(evidence.current_evidence(self.root, cfg, 'typecheck')[0])
    def provenance_fixture(self):
        cfg = config.load_config(self.root)
        req = self.put(cfg['paths']['requirement'], '交付范围：设计到模块\n管理用户')
        design = self.put('项目战术执行/00_产品设计文档.md', '# 设计\nAC-USER-01 最多100人')
        arch = self.put('项目战术执行/00_功能架构设计文档.md', '# 架构\n表名: users\ncount integer')
        module = self.put('项目战术执行/01_用户详细设计.md', '# 模块\nAC-USER-01')
        with contextlib.redirect_stdout(io.StringIO()):
            workflow.main(['--project-root',str(self.root),'--stamp',str(design),str(arch),str(module)])
        return req, design, arch, module
    def test_rule_and_field_changes_invalidate_full_fingerprints(self):
        req, design, arch, module = self.provenance_fixture()
        self.assertTrue(all(x['status']=='OK' for x in workflow.evaluate(str(self.root))))
        design.write_text(design.read_text().replace('100','999'))
        self.assertEqual(workflow.evaluate(str(self.root))[1]['status'],'STALE')
        before = workflow.fingerprint(arch,'arch_doc')[0]
        arch.write_text(arch.read_text().replace('integer','text'))
        self.assertNotEqual(before, workflow.fingerprint(arch,'arch_doc')[0])
    def test_removed_requirement_keeps_dependency_and_blocks_transitively(self):
        req, *_ = self.provenance_fixture(); req.unlink()
        self.assertTrue(all(x['status']=='STALE' for x in workflow.evaluate(str(self.root))))
    def test_requirement_change_propagates_without_downstream_edits(self):
        req, *_ = self.provenance_fixture(); req.write_text(req.read_text()+'\n新增规则')
        self.assertTrue(all(x['status']=='STALE' for x in workflow.evaluate(str(self.root))))
    def test_metadata_refresh_does_not_change_content_hash(self):
        _, design, arch, module = self.provenance_fixture()
        before = workflow.fingerprint(design,'design_doc')[0]
        workflow.write_meta(design, [('r.md','sha256:'+'a'*64,'')])
        self.assertEqual(before, workflow.fingerprint(design,'design_doc')[0])
    def validator(self, skill, filename, text, design=None):
        import importlib.util
        spec = importlib.util.spec_from_file_location(skill, ROOT/skill/'scripts'/filename)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        doc = self.put(skill+'.md', text)
        return module.validate(str(doc), str(design)) if design else module.validate(str(doc))
    def test_empty_design_architecture_module_fail(self):
        for skill, name in [('product-design','validate_design_doc.py'), ('product-architecture','validate_arch_doc.py'), ('product-module-design','validate_module_doc.py')]:
            with self.subTest(skill=skill):
                rows = self.validator(skill,name,'## 业务流程\n```mermaid\nthis is not a graph\n```\n## 页面清单\n## 功能设计详情\n')
                self.assertTrue(any(row.level == 'FAIL' for row in rows))
    def test_mermaid_actual_parser_rejects_invalid_syntax(self):
        from strict_docs import mermaid_errors
        self.assertEqual(mermaid_errors(['graph TD\nA --> B']), [])
        self.assertTrue(mermaid_errors(['graph TD\nA --> [broken']))
    def test_page_list_details_must_match(self):
        text = '## 业务流程\n```mermaid\ngraph TD\nA --> B\n```\n## 页面清单\n| 页面 | 说明 |\n|---|---|\n| 用户 | 用户列表 |\n## 功能设计详情\n### 别的页面\nAC-USER-01 查询成功\n## 全局检查\n确认覆盖全部需求\n'
        rows = self.validator('product-design','validate_design_doc.py',text)
        self.assertTrue(any(row.code=='C17' and row.level=='FAIL' for row in rows))
    def test_explicit_na_requires_substantive_reason(self):
        from strict_docs import na
        self.assertFalse(na('N/A[database]: 待补充','database'))
        self.assertTrue(na('N/A[database]: 本模块只读取外部服务且不持久化任何数据','database'))
    def actual_unit_fixture(self, skip=False):
        cfg = self.configure({'commands': {'backend': {'cwd':'backend','argv':[sys.executable,'run.py','{report}'],'report':'junit'}},'exemptions':{'typecheck':'本验证项目仅有 Python 后端实现','lint':'本验证项目仅有 Python 后端实现','e2e':'本验证项目为无界面的纯计算模块'}})
        script = '''import sys, unittest, xml.etree.ElementTree as ET
class ActualTest(unittest.TestCase):
    def test_calculation(self):
        self.assertEqual(sum([1, 2, 3]), 6)
suite = unittest.defaultTestLoader.loadTestsFromTestCase(ActualTest)
result = unittest.TestResult()
suite.run(result)
root = ET.Element('testsuite', tests=str(result.testsRun))
case = ET.SubElement(root, 'testcase', name='AC-USER-01 calculation', classname='ActualTest')
for _, detail in result.failures + result.errors:
    ET.SubElement(case, 'failure').text = detail
for _, reason in result.skipped:
    ET.SubElement(case, 'skipped').text = reason
ET.ElementTree(root).write(sys.argv[1], encoding='utf-8')
sys.exit(0 if result.wasSuccessful() else 1)
'''
        if skip:
            script = script.replace('    def test_calculation', '    @unittest.skip("not ready")\n    def test_calculation')
        self.put('backend/run.py', script)
        return cfg
    def test_actual_unit_run_proves_ac_without_e2e_comments(self):
        cfg = self.actual_unit_fixture()
        self.assertEqual(self.execute(['backend']),0)
        covered, errors = evidence.executed_coverage(self.root,cfg)
        self.assertEqual(covered,{'AC-USER-01'}); self.assertEqual(errors,[])
    def test_skipped_tests_do_not_prove_coverage(self):
        cfg = self.actual_unit_fixture(skip=True)
        self.assertEqual(self.execute(['backend']),1)
        self.assertEqual(evidence.executed_coverage(self.root,cfg)[0],set())
    def test_zero_malformed_and_failed_junit_rejected(self):
        for data in ('<testsuite tests="100"/>', '<testsuite><testcase name="AC-USER-01"><failure/></testcase></testsuite>', '<invalid>'):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    evidence.junit_cases(self.put('report.xml',data))
    def test_comment_only_spec_cannot_pass_static_gate(self):
        design = self.put('design.md','AC-USER-01 查询成功')
        self.put('spec/a.spec.ts','// AC-USER-01\n// test("fake", () => {});')
        import importlib.util
        spec=importlib.util.spec_from_file_location('spec_validator', ROOT/'product-e2e-test/scripts/validate_e2e_spec.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertTrue(any(x.level=='FAIL' for x in module.validate(str(design),str(self.root/'spec'))))
    def test_modified_report_invalidates_execution_evidence(self):
        cfg = self.actual_unit_fixture(); self.execute(['backend'])
        item,_ = evidence.current_evidence(self.root,cfg,'backend')
        self.put(item['report'],'<testsuite/>')
        self.assertIsNone(evidence.current_evidence(self.root,cfg,'backend')[0])
    def ledger(self, issues):
        cfg = config.load_config(self.root)
        return self.put('.product-workflow/issues.json', json.dumps({'schema_version':1,'reviewed_by':'regression-fixture','reviewed_at':'2026-09-12','input_sha256':evidence.input_digest(self.root,cfg),'issues':issues}))
    def test_all_legacy_unresolved_sections_are_checked(self):
        self.put('项目战术执行/90_诊断报告_测试.md','## 未确认项\n无\n## 追加诊断\n### 未确认项\n待补充\n## 追加诊断二\n### 未解决\n- 权限边界尚未验证\n')
        self.ledger([])
        unresolved = workflow.collect_unresolved(str(self.root))
        self.assertEqual(len(unresolved),2)
        self.assertIn('待补充',str(unresolved));self.assertIn('权限边界',str(unresolved))
    def test_missing_ledger_and_open_blocker_block(self):
        self.assertTrue(workflow.collect_unresolved(str(self.root)))
        self.ledger([{'id':'F1','title':'没有验证权限','owner':'team','blocking':True,'severity':'high','status':'open'}])
        self.assertEqual(workflow.collect_unresolved(str(self.root))[0][0],'F1')
    def test_closed_issue_requires_evidence_and_tracks_legacy_section(self):
        from issue_ledger import legacy_sections
        self.put('项目战术执行/90_诊断报告_测试.md','## 未确认项\n待补充\n')
        issue={'id':'F1','title':'补全验证','owner':'team','blocking':True,'severity':'high','status':'resolved'}
        self.ledger([issue]); self.assertTrue(workflow.collect_unresolved(str(self.root)))
        proof=self.put('validation.md','实际复核结果（测试夹具）')
        path, body_hash, _ = legacy_sections(self.root,config.load_config(self.root))[0]
        issue.update(resolution={'summary':'已完成复核','evidence':[{'path':'validation.md','sha256':evidence.digest(proof)}]},legacy_sources=[{'path':path,'body_sha256':body_hash}])
        self.ledger([issue]); self.assertEqual(workflow.collect_unresolved(str(self.root)),[])
        proof.write_text('证据发生变化')
        self.assertTrue(workflow.collect_unresolved(str(self.root)))
    def valid_design(self):
        return '''# 产品设计
## 业务流程
```mermaid
graph TD
A --> B
```
## 页面清单
| 页面 | 说明 |
|---|---|
| 用户 | 查看用户 |
## 功能设计详情
### 用户
#### 字段字典
| 字段 | 类型 |
|---|---|
| 名称 | 文本 |
#### 交互矩阵
| 事件 | 结果 |
|---|---|
| 查询 | 显示匹配用户 |
#### 验收标准
- AC-USER-01 输入已存在的用户名 → 查询 → 返回该用户。
## 全局检查
已检查页面与需求一致，覆盖查询成功行为。
'''
    def test_positive_design_scope_then_missing_confirmation_blocks(self):
        cfg = config.load_config(self.root)
        req=self.put(cfg['paths']['requirement'],'交付范围：产品设计\n查询用户')
        design=self.put('项目战术执行/00_产品设计文档.md',self.valid_design())
        with contextlib.redirect_stdout(io.StringIO()):
            workflow.main(['--project-root',str(self.root),'--stamp',str(design)])
        self.put('.product-workflow/approval.json',json.dumps({'schema_version':1,'requirement_sha256':evidence.digest(req),'confirmed_by':'fixture-user','confirmed_at':'2026-09-12','confirmation_reference':'synthetic test fixture only'}))
        self.ledger([])
        path, ready, _ = workflow.finalize(str(self.root))
        self.assertTrue(ready,Path(path).read_text())
        (self.root/'.product-workflow/approval.json').unlink()
        self.assertFalse(workflow.finalize(str(self.root))[1])
    def test_positive_full_scope_with_explicit_backend_only_delivery(self):
        self.actual_unit_fixture()
        raw = json.loads((self.root/'product-workflow.json').read_text())
        raw['exemptions']['frontend']='本回归夹具仅交付 Python 服务，页面设计留作后续阶段'
        cfg = self.configure(raw)
        req = self.put(cfg['paths']['requirement'],'交付范围：全链\n交付 Python 计算服务，前端设计保留但本次不实现 UI。')
        design = self.put('项目战术执行/00_产品设计文档.md', self.valid_design().replace('输入已存在的用户名 → 查询 → 返回该用户。', '输入 [1,2,3] → 求和 → 返回 6。'))
        arch = self.put('项目战术执行/00_功能架构设计文档.md','''# 架构
## 需求分析
用户场景计算由 Python 服务承担。
## 总体技术方案
```mermaid
graph TD
A --> B
```
## 开发规范
函数使用 snake_case，纯函数不保存外部状态。
## 功能设计
N/A[database]: 纯函数计算不保存任何持久化数据
N/A[frontend]: 本次只交付后端服务，前端页面留待后续实现
## 方案自检
已检查需求与纯计算服务边界。
''')
        module = self.put('项目战术执行/01_用户详细设计.md','''# 模块
## 产品设计
来源：产品设计用户页面，本阶段实现计算服务。
### 本模块覆盖的 AC
AC-USER-01
```mermaid
graph TD
A --> B
```
## 前端详细设计
N/A[frontend]: 本次仅交付计算服务，前端页面留待后续实现
## 后端详细设计
N/A[api]: 本次交付可调用的本地函数，不提供网络接口
N/A[database]: 纯函数不读取或写入持久化数据库
## 测试详细设计
| 用例 | 对应 AC 编号 |
|---|---|
| calculation | AC-USER-01 |
''')
        with contextlib.redirect_stdout(io.StringIO()):
            workflow.main(['--project-root',str(self.root),'--stamp',str(design),str(arch),str(module)])
        self.put('.product-workflow/approval.json',json.dumps({'schema_version':1,'requirement_sha256':evidence.digest(req),'confirmed_by':'fixture-user','confirmed_at':'2026-09-12','confirmation_reference':'synthetic regression fixture, not real approval'}))
        self.ledger([])
        self.assertEqual(self.execute(['backend']),0)
        path, ready, _ = workflow.finalize(str(self.root))
        self.assertTrue(ready,Path(path).read_text())
        self.put('backend/new.py','NEW_RULE = True')
        self.assertFalse(workflow.finalize(str(self.root))[1])
    def test_copied_ac_in_module_body_is_not_declared_coverage(self):
        self.put('项目战术执行/00_产品设计文档.md','AC-USER-01\nAC-USER-02')
        self.put('项目战术执行/01_用户详细设计.md','## 来源摘录\nAC-USER-02\n## 本模块覆盖的 AC\nAC-USER-01\n## 测试\n其他测试说明')
        self.assertEqual(workflow.ac_coverage(str(self.root))[1],{'AC-USER-01'})
