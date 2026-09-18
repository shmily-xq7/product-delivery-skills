import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "diagram_tool", ROOT / "product-diagram/scripts/diagram_tool.py"
)
diagram_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagram_tool)


class DiagramToolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name).resolve()
        source = self.project / "项目战术执行/00_产品设计文档.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            "# 产品设计\n\n```mermaid\ngraph TD\nA[提交] --> B{通过?}\nB -->|是| C[完成]\nB -->|否| D[退回]\n```\n",
            encoding="utf-8",
        )
        self.source = source

    def render(self):
        output = io.StringIO()
        runtime_modules = ROOT / "product-workflow/validators/node_modules"
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), patch.dict(
            os.environ, {"PRODUCT_DIAGRAM_NODE_MODULES": str(runtime_modules)}
        ):
            code = diagram_tool.main([
                "render",
                "--project-root", str(self.project),
                "--source", "项目战术执行/00_产品设计文档.md",
                "--diagram-index", "0",
                "--id", "APPROVAL-FLOW",
                "--stage", "design",
                "--type", "business-flow",
                "--title", "审批流程",
                "--description", "展示提交、通过和退回路径",
            ])
        return code, output.getvalue()

    def test_render_register_and_check_staleness(self):
        code, output = self.render()
        self.assertEqual(code, 0, output)
        directory = self.project / "outputs/diagrams/APPROVAL-FLOW"
        svg = (directory / "APPROVAL-FLOW.svg").read_text(encoding="utf-8")
        html = (directory / "APPROVAL-FLOW.html").read_text(encoding="utf-8")
        manifest = json.loads((self.project / "outputs/diagrams/manifest.json").read_text())
        self.assertIn('role="img"', svg)
        self.assertIn("<title", svg)
        self.assertIn("<desc", svg)
        self.assertIn("<figure>", html)
        self.assertNotIn("<script src=", html)
        self.assertEqual(manifest["diagrams"][0]["source"]["diagram_index"], 0)

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(diagram_tool.main(["check", "--project-root", str(self.project)]), 0)

        text = self.source.read_text(encoding="utf-8").replace("C[完成]", "C[已完成]")
        self.source.write_text(text, encoding="utf-8")
        check_output = io.StringIO()
        with contextlib.redirect_stdout(check_output):
            self.assertEqual(diagram_tool.main(["check", "--project-root", str(self.project)]), 1)
        self.assertIn("来源 Mermaid 块已变化", check_output.getvalue())

    def test_rejects_path_outside_project(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            code = diagram_tool.main([
                "render", "--project-root", str(self.project), "--source", "../outside.md",
                "--id", "OUTSIDE", "--stage", "design", "--type", "business-flow",
                "--title", "越界", "--description", "越界路径",
            ])
        self.assertEqual(code, 1)
        self.assertIn("路径不可越出项目根", output.getvalue())

    def test_renders_sequence_state_and_er_diagrams(self):
        examples = {
            "sequence": "sequenceDiagram\nparticipant A\nparticipant B\nA->>B: Request\nB-->>A: Response",
            "state": "stateDiagram-v2\n[*] --> Draft\nDraft --> Done\nDone --> [*]",
            "er": "erDiagram\nUSER ||--o{ ORDER : places\nUSER {\nint id PK\n}\nORDER {\nint id PK\n}",
        }
        runtime_modules = ROOT / "product-workflow/validators/node_modules"
        with patch.dict(os.environ, {"PRODUCT_DIAGRAM_NODE_MODULES": str(runtime_modules)}):
            for name, source in examples.items():
                with self.subTest(name=name):
                    svg = diagram_tool.render_svg(name.upper(), name, name, source)
                    self.assertIn('role="img"', svg)
                    self.assertIn("<title", svg)


class ReleaseManifestTests(unittest.TestCase):
    def test_release_manifest_declares_every_skill_directory(self):
        release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
        actual = sorted(path.name for path in ROOT.glob("product-*") if path.is_dir())
        self.assertEqual(sorted(release["skills"]), actual)


if __name__ == "__main__":
    unittest.main()
