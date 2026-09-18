import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'product-workflow/scripts'))
import workflow_config as config
import check_freshness as workflow
import build_snapshot
import run_checks
spec=importlib.util.spec_from_file_location('bundle_install', ROOT/'scripts/install.py')
installer=importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
    def put(self, name, text):
        p=self.root/name; p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
    def cfg(self, value): self.put('product-workflow.json',json.dumps(value))
    def setup_project(self):
        self.cfg({'paths':{'requirement':'docs/requirements.md','execution':'docs/design','frontend':'web','backend':'api'},'module_sources':{
            'docs/design/01_用户详细设计.md':[{'source':'design','sections':['USER']},{'source':'architecture','sections':['API']}]
        }})
        self.put('docs/requirements.md','交付范围：设计到模块\n用户管理')
        self.design=self.put('docs/design/00_产品设计文档.md','## 页面清单\n| 页面 | 说明 |\n|---|---|\n| 用户 | 管理 |\n## 功能设计详情\n<!-- workflow:id USER -->\n### 用户\nAC-USER-01 最多100人\n<!-- workflow:id OTHER -->\n### 其他\n其他功能\n')
        self.arch=self.put('docs/design/00_功能架构设计文档.md','<!-- workflow:id API -->\n## 用户 API\n表名: users\nPOST /users\n<!-- workflow:id COMMON -->\n## 其他\n说明\n')
        self.module=self.put('docs/design/01_用户详细设计.md','## 本模块覆盖的 AC\nAC-USER-01\n')
        with contextlib.redirect_stdout(io.StringIO()): workflow.main(['--project-root',str(self.root),'--stamp',str(self.design),str(self.arch),str(self.module)])
    def test_custom_paths_and_independent_projects(self):
        self.setup_project()
        self.assertEqual(config.load_config(self.root)['paths']['e2e'],'web/tests/e2e')
        self.assertEqual(config.load_config(self.root)['commands']['typecheck']['cwd'],'web')
        self.assertEqual(len(workflow.discover(str(self.root))),3)
        self.assertEqual(config.load_config(ROOT)['paths']['execution'],'项目战术执行')
    def test_unrelated_changes_do_not_invalidate_module(self):
        self.setup_project();self.design.write_text(self.design.read_text().replace('其他功能','其他功能已改变'))
        result=next(x for x in workflow.evaluate(str(self.root)) if x['role']=='module_doc')
        self.assertEqual(result['status'],'OK')
    def test_related_rule_change_invalidates_module(self):
        self.setup_project();self.design.write_text(self.design.read_text().replace('最多100人','最多999人'))
        result=next(x for x in workflow.evaluate(str(self.root)) if x['role']=='module_doc')
        self.assertEqual(result['status'],'STALE')
    def test_removed_section_fails_and_stamp_does_not_write(self):
        self.setup_project();self.design.write_text(self.design.read_text().replace('workflow:id USER','workflow:id RENAMED'))
        before=self.module.read_bytes()
        with self.assertRaises(ValueError): workflow.main(['--project-root',str(self.root),'--stamp',str(self.module)])
        self.assertEqual(before,self.module.read_bytes())
        self.assertEqual(workflow.evaluate(str(self.root))[-1]['status'],'STALE')
    def test_deleted_source_invalidates_module(self):
        self.setup_project(); self.arch.unlink()
        self.assertEqual(workflow.evaluate(str(self.root))[-1]['status'],'STALE')
    def test_missing_stamp_has_nonzero_cli_exit(self):
        result=subprocess.run([sys.executable,str(ROOT/'product-workflow/scripts/check_freshness.py'),'--project-root',str(self.root),'--stamp','missing.md'],capture_output=True)
        self.assertNotEqual(result.returncode,0)
    def test_empty_project_reports_uninitialized_and_strict_fails(self):
        findings=workflow.check_one(str(self.root))
        self.assertEqual([(x.level,x.code) for x in findings],[('WARN','F-EMPTY')])
        self.assertIn('UNINITIALIZED',workflow.render(findings))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(workflow.main(['--project-root',str(self.root)]),0)
            self.assertEqual(workflow.main(['--project-root',str(self.root),'--strict']),1)
    def test_stamp_batch_preflight_preserves_earlier_file(self):
        self.setup_project();before=self.design.read_bytes()
        with self.assertRaises(ValueError):workflow.main(['--project-root',str(self.root),'--stamp',str(self.design),'missing.md'])
        self.assertEqual(before,self.design.read_bytes())
    def test_duplicate_markers_and_path_escape_rejected(self):
        self.put('source.md','<!-- workflow:id ONE -->\n## One\nA\n<!-- workflow:id ONE -->\n## Again\nB\n')
        with self.assertRaises(ValueError):config.read_source(self.root,'source.md#sections=ONE')
        self.cfg({'paths':{'execution':'../escape'}})
        with self.assertRaises(ValueError):config.load_config(self.root)
    def test_code_fence_headings_do_not_truncate_slice(self):
        self.put('source.md','<!-- workflow:id ONE -->\n## One\n```md\n## fake\n```\nend\n<!-- workflow:id TWO -->\n## Two\nother\n')
        text=config.read_source(self.root,'source.md#sections=ONE')
        self.assertIn('end',text);self.assertNotIn('other',text);self.assertNotIn('workflow:id TWO',text)
    def test_snapshot_preserves_sources_and_refuses_overwrite(self):
        self.setup_project();before={p:p.read_bytes() for p in [self.design,self.arch,self.module]}
        output=build_snapshot.build(self.root,'docs/design/01_用户详细设计.md','outputs/review.md')
        self.assertIn('最多100人',output.read_text());self.assertNotIn('其他功能',output.read_text())
        for path,content in before.items():self.assertEqual(path.read_bytes(),content)
        with self.assertRaises(ValueError):build_snapshot.build(self.root,'docs/design/01_用户详细设计.md','outputs/review.md')
    def test_extensions_shared_by_finalizer_and_validator(self):
        self.setup_project();self.put('web/tests/e2e/test.spec.jsx','// AC-USER-01')
        spec=importlib.util.spec_from_file_location('e2e',ROOT/'product-e2e-test/scripts/validate_e2e_spec.py')
        e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
        self.assertEqual(workflow.ac_coverage(str(self.root))[2],{'AC-USER-01'})
        self.assertEqual(len(e.find_spec_files(str(self.root/'web/tests/e2e'))),1)
    def test_legacy_scope_alias_and_custom_finalize_paths(self):
        self.cfg({'paths':{'requirement':'r.md','execution':'d','design_name':'product.md'}})
        self.put('r.md','交付范围：仅需求分析\n需求')
        self.assertEqual(workflow.parse_scope(str(self.root))[0],'产品设计')
        design=self.put('d/product.md','## 业务流程\n```mermaid\ngraph TD\nA --> B\n```\n## 页面清单\n## 功能设计详情\n')
        with contextlib.redirect_stdout(io.StringIO()):workflow.main(['--project-root',str(self.root),'--stamp',str(design)])
        path,_,_=workflow.finalize(str(self.root))
        self.assertEqual(path,str(self.root/'d/99_交付清单.md'))
        self.assertIn('product.md',Path(path).read_text())
    def test_commands_use_independent_cwd_and_keep_logs(self):
        (self.root/'web').mkdir();(self.root/'api').mkdir()
        self.cfg({'commands':{n:{'cwd':n,'argv':[sys.executable,'-c','import os; print(os.getcwd())']} for n in ['web','api']}})
        with contextlib.redirect_stdout(io.StringIO()):code=run_checks.run(self.root,['web','api'])
        self.assertEqual(code,0)
        logs=sorted((self.root/'.product-workflow/runs').glob('*/*.log'))
        self.assertEqual([p.read_text().strip() for p in logs],[str(self.root/'web'),str(self.root/'api')])


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name).resolve()/'source';self.source.mkdir();self.target=Path(self.temp.name).resolve()/'目标 with spaces'
        self.skill_names=['product-%02d'%n for n in range(11)]
        (self.source/'release.json').write_text(json.dumps({'version':'test','base_commit':'base','skills':self.skill_names}))
        for n in range(11):
            name='product-%02d'%n;d=self.source/name;d.mkdir()
            (d/'SKILL.md').write_text('---\nname: %s\ndescription: test skill\n---\nold %d'%(name,n))
    def install(self):
        with contextlib.redirect_stdout(io.StringIO()):installer.install(self.source,self.target)
    def test_repeat_install_records_version_and_hidden_backups(self):
        self.install();self.install()
        manifest=json.loads((self.target/'.product-delivery/manifest.json').read_text())
        self.assertEqual(len(manifest['skills']),11)
        self.assertEqual(manifest['client'],'自定义目录')
        self.assertEqual(len(list(self.target.glob('product-*'))),11)
        self.assertEqual(len(list((self.target/'.product-delivery/backups').iterdir())),2)
        for name,content in manifest['skills'].items():self.assertEqual(content,installer.inventory(self.target/name))
    def test_failed_source_validation_preserves_installed_files(self):
        self.install();(self.source/'product-10/SKILL.md').unlink()
        with self.assertRaises(ValueError):self.install()
        self.assertTrue((self.target/'product-10/SKILL.md').read_text().endswith('old 10'))
    def test_mid_replacement_failure_rolls_back_entire_bundle(self):
        self.install();manifest=(self.target/'.product-delivery/manifest.json').read_bytes()
        for p in self.source.glob('product-*/SKILL.md'):
            name=p.parent.name;p.write_text('---\nname: %s\ndescription: test skill\n---\nnew'%name)
        real=installer.os.replace
        def failing(src,dst):
            if Path(dst)==self.target/'product-03' and 'stage-' in str(src):raise OSError('simulated failure')
            return real(src,dst)
        with patch.object(installer.os,'replace',side_effect=failing):
            with self.assertRaises(OSError):self.install()
        for n in range(11):self.assertTrue((self.target/('product-%02d'%n)/'SKILL.md').read_text().endswith('old '+str(n)))
        self.assertEqual(manifest,(self.target/'.product-delivery/manifest.json').read_bytes())
        self.assertFalse((self.target/'.product-delivery/install.lock').exists())

    def test_validator_dependency_failure_preserves_installed_bundle(self):
        (self.source/'product-10').rename(self.source/'product-workflow')
        skill=self.source/'product-workflow/SKILL.md'
        skill.write_text(skill.read_text().replace('name: product-10','name: product-workflow'))
        release=json.loads((self.source/'release.json').read_text())
        release['skills'][-1]='product-workflow'
        (self.source/'release.json').write_text(json.dumps(release))
        self.install()
        before=(self.target/'.product-delivery/manifest.json').read_bytes()
        validators=self.source/'product-workflow/validators';validators.mkdir()
        (validators/'package-lock.json').write_text('{}')
        with patch.object(installer.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','network failure')):
            with self.assertRaises(ValueError):self.install()
        self.assertEqual(before,(self.target/'.product-delivery/manifest.json').read_bytes())
        self.assertFalse((self.target/'.product-delivery/install.lock').exists())

    def test_source_frontmatter_name_and_description_are_validated(self):
        skill=self.source/'product-00/SKILL.md'
        skill.write_text('---\nname: another-name\ndescription: test\n---\nbody')
        with self.assertRaisesRegex(ValueError,'name 必须与目录名一致'):self.install()
        skill.write_text('---\nname: product-00\n---\nbody')
        with self.assertRaisesRegex(ValueError,'缺 description'):self.install()

    def test_release_manifest_must_match_skill_directories(self):
        extra=self.source/'product-extra';extra.mkdir()
        (extra/'SKILL.md').write_text('---\nname: product-extra\ndescription: extra\n---\n')
        with self.assertRaisesRegex(ValueError,'发行清单与技能目录不一致'):self.install()

    def test_client_aliases_multiple_targets_and_deduplication(self):
        home=Path(self.temp.name)/'home';home.mkdir()
        targets=installer.resolve_targets(
            ['claude','qwenwork','traework','codex','dsh'],
            [home/'.agents/skills'],
            home=home,
            environ={},
            platform_name='darwin',
        )
        by_path={str(path):label for label,path in targets}
        self.assertEqual(by_path[str((home/'.claude/skills').resolve())],'Claude Code')
        self.assertEqual(by_path[str((home/'.qwenwork/skills').resolve())],'千问办公 / QwenWork')
        self.assertEqual(by_path[str((home/'.trae-cn/skills').resolve())],'TRAE Work / TRAE CN')
        self.assertEqual(by_path[str((home/'.dsh/skills').resolve())],'DeepSeek Harness (DSH)')
        self.assertEqual(
            by_path[str((home/'.agents/skills').resolve())],
            'OpenAI Codex + 自定义目录',
        )

    def test_all_detected_uses_markers_and_skips_legacy_profile(self):
        home=Path(self.temp.name)/'home';home.mkdir()
        for marker in ['.claude','.codex','.workbuddy','.trae-cn']:(home/marker).mkdir()
        targets=installer.resolve_targets(
            all_detected=True,
            home=home,
            environ={},
            platform_name='darwin',
        )
        labels={label for label,_ in targets}
        self.assertEqual(labels,{'Claude Code','OpenAI Codex','WorkBuddy','TRAE Work / TRAE CN'})
        self.assertNotIn(home/'.codex/skills',{path for _,path in targets})

    def test_generic_override_does_not_add_implicit_codex(self):
        home=Path(self.temp.name)/'home';home.mkdir()
        target=home/'shared skills'
        self.assertEqual(
            installer.resolve_targets(home=home,environ={'AGENT_SKILLS_DIR':str(target)}),
            [('自定义目录',target.resolve())],
        )
        self.assertEqual(installer.resolve_targets(home=home,environ={}),[])

    def test_dsh_home_and_direct_override(self):
        home=Path(self.temp.name)/'home';home.mkdir()
        dsh_home=home/'dsh data'
        self.assertEqual(
            installer.app_target('dsh',home,{'DSH_HOME':str(dsh_home)}),
            dsh_home/'skills',
        )
        direct=home/'custom dsh skills'
        self.assertEqual(
            installer.app_target('deepseek-harness',home,{'DSH_SKILLS_DIR':str(direct)}),
            direct,
        )
        self.assertIn('dsh',installer.detected_apps(home,{'DSH_HOME':str(dsh_home)}))

    def test_export_packages_puts_skill_file_at_archive_root(self):
        destination=Path(self.temp.name)/'packages'
        with contextlib.redirect_stdout(io.StringIO()):installer.export_packages(self.source,destination)
        archives=sorted(destination.glob('product-*.zip'))
        self.assertEqual(len(archives),11)
        with zipfile.ZipFile(archives[0]) as package:
            self.assertIn('SKILL.md',package.namelist())
            self.assertFalse(any(name.startswith('product-00/') for name in package.namelist()))
        manifest=json.loads((destination/'packages.json').read_text())
        self.assertEqual(len(manifest['packages']),11)
        for archive in archives:
            self.assertEqual(manifest['packages'][archive.name],hashlib.sha256(archive.read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
