"""
Unit tests for template generation (template/codegen) and code execution (runcode/compile).
"""

import io
import os
import tempfile
import unittest
from pathlib import Path

from shell.builtins.registry import registry
from shell.core.context import ShellContext


class TestCodeOps(unittest.TestCase):
    def setUp(self):
        self.orig_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.context = ShellContext(
            cwd=self.temp_dir.name,
            stdout=self.stdout,
            stderr=self.stderr,
            history_file=None,
        )

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.temp_dir.cleanup()

    def test_template_list(self):
        tmpl_cmd = registry.get("template")
        self.assertIsNotNone(tmpl_cmd)

        code = tmpl_cmd.execute(["list"], self.context)
        self.assertEqual(code, 0)
        output = self.stdout.getvalue()
        self.assertIn("Available Code Templates", output)
        self.assertIn("python", output)
        self.assertIn("add", output)
        self.assertIn("age", output)

    def test_create_and_run_python_add(self):
        tmpl_cmd = registry.get("template")
        run_cmd = registry.get("runcode")

        # Create add template
        code = tmpl_cmd.execute(["create", "python", "add", "math_add.py"], self.context)
        self.assertEqual(code, 0)
        created_file = self.context.cwd / "math_add.py"
        self.assertTrue(created_file.exists())
        self.assertIn("add_numbers", created_file.read_text(encoding="utf-8"))

        # Execute add template
        code = run_cmd.execute(["math_add.py"], self.context)
        self.assertEqual(code, 0)
        output = self.stdout.getvalue()
        self.assertIn("Python Addition Program", output)
        self.assertIn("Result:", output)

    def test_create_and_run_python_age(self):
        tmpl_cmd = registry.get("template")
        run_cmd = registry.get("runcode")

        # Create age validation template
        code = tmpl_cmd.execute(["create", "python", "age", "check_age.py"], self.context)
        self.assertEqual(code, 0)
        created_file = self.context.cwd / "check_age.py"
        self.assertTrue(created_file.exists())
        self.assertIn("validate_age", created_file.read_text(encoding="utf-8"))

        # Execute age validation template
        code = run_cmd.execute(["check_age.py"], self.context)
        self.assertEqual(code, 0)
        output = self.stdout.getvalue()
        self.assertIn("Python Age Validation Program", output)
        self.assertIn("Eligible (Adult)", output)
        self.assertIn("Ineligible (Minor)", output)

    def test_create_c_and_cpp_templates(self):
        tmpl_cmd = registry.get("template")

        # C add template
        self.assertEqual(tmpl_cmd.execute(["create", "c", "add", "add.c"], self.context), 0)
        c_file = self.context.cwd / "add.c"
        self.assertTrue(c_file.exists())
        self.assertIn("#include <stdio.h>", c_file.read_text(encoding="utf-8"))

        # C++ age template
        self.assertEqual(tmpl_cmd.execute(["create", "cpp", "age", "age.cpp"], self.context), 0)
        cpp_file = self.context.cwd / "age.cpp"
        self.assertTrue(cpp_file.exists())
        self.assertIn("#include <iostream>", cpp_file.read_text(encoding="utf-8"))

    def test_invalid_language_and_file_not_found(self):
        tmpl_cmd = registry.get("template")
        run_cmd = registry.get("runcode")

        # Invalid language
        code = tmpl_cmd.execute(["create", "unknown_lang", "add"], self.context)
        self.assertEqual(code, 1)

        # File not found for runcode
        code = run_cmd.execute(["does_not_exist.py"], self.context)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
