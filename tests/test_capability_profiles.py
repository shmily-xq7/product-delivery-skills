import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detect_stack = load("detect_stack", ROOT / "product-development/scripts/detect_stack.py")
page_patterns = load("page_patterns", ROOT / "product-development/scripts/page_patterns.py")


class DevelopmentProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def package(self, dependencies, in_frontend=True):
        base = self.root / "frontend" if in_frontend else self.root
        base.mkdir(parents=True, exist_ok=True)
        (base / "package.json").write_text(json.dumps({"dependencies": dependencies}))

    def test_detects_supported_profiles_and_defaults_react(self):
        self.assertEqual(detect_stack.detect(self.root)["profile"], "react-antd")
        self.package({"vue": "^2.7.16", "element-ui": "^2.15.14"})
        self.assertEqual(detect_stack.detect(self.root)["profile"], "vue2-element")
        (self.root / "frontend/package.json").write_text(json.dumps({"dependencies": {
            "vue": "^3.5.0", "element-plus": "^2.8.0"
        }}))
        self.assertEqual(detect_stack.detect(self.root)["profile"], "vue3-element-plus")
        (self.root / "frontend/package.json").write_text(json.dumps({"dependencies": {
            "react": "^18.3.0", "antd": "^5.0.0"
        }}))
        self.assertEqual(detect_stack.detect(self.root)["profile"], "react-antd")

    def test_explicit_stack_wins_only_when_dependencies_agree(self):
        self.package({"vue": "^3.5.0", "element-plus": "^2.8.0"})
        (self.root / "product-workflow.json").write_text(json.dumps({
            "stack": {"frontend": "Vue 3 + TypeScript + Element Plus"}
        }))
        self.assertEqual(detect_stack.detect(self.root)["reason"], "product-workflow.json")
        (self.root / "product-workflow.json").write_text(json.dumps({
            "stack": {"frontend": "React + TypeScript + Ant Design"}
        }))
        with self.assertRaisesRegex(ValueError, "依赖不一致"):
            detect_stack.detect(self.root)

    def test_ambiguous_package_requires_explicit_choice(self):
        self.package({"react": "^18", "vue": "^3"})
        with self.assertRaisesRegex(ValueError, "同时包含 React 与 Vue"):
            detect_stack.detect(self.root)

    def test_rejects_incompatible_vue_compilers(self):
        self.package({
            "vue": "^2.6.14", "element-ui": "^2.15.14",
            "vue-template-compiler": "^2.7.16"
        })
        with self.assertRaisesRegex(ValueError, "完全一致"):
            detect_stack.detect(self.root)
        (self.root / "frontend/package.json").write_text(json.dumps({"dependencies": {
            "vue": "^2.7.16", "element-ui": "^2.15.14",
            "vue-template-compiler": "^2.7.16", "@vue/compiler-sfc": "^3.5.0"
        }}))
        with self.assertRaisesRegex(ValueError, "不能混用"):
            detect_stack.detect(self.root)


class PagePatternCatalogTests(unittest.TestCase):
    def test_catalog_has_unique_resolvable_patterns(self):
        catalog = page_patterns.load_catalog()
        ids = [pattern["id"] for pattern in catalog["patterns"]]
        self.assertEqual(len(ids), 10)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(page_patterns.find_pattern(catalog, "rbac-matrix")["title"], "权限矩阵")

    def test_unknown_pattern_reports_available_ids(self):
        catalog = page_patterns.load_catalog()
        with self.assertRaisesRegex(ValueError, "standard-list"):
            page_patterns.find_pattern(catalog, "unknown")


if __name__ == "__main__":
    unittest.main()
