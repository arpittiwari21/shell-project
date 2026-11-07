"""
Unit and integration tests for CommandExecutor (process execution, redirection, conditionals).
"""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

from shell.builtins.registry import registry
from shell.core.context import ShellContext
from shell.core.executor import CommandExecutor
from shell.core.parser import CommandParser


class TestCommandExecutor(unittest.TestCase):
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
        self.parser = CommandParser(self.context)
        self.executor = CommandExecutor(self.context, registry)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.temp_dir.cleanup()

    def test_output_redirection(self):
        # Builtin with stdout redirection
        stmts = self.parser.parse("echo 'antigravity shell' > output.txt", self.context)
        code = self.executor.execute_statements(stmts)
        self.assertEqual(code, 0)

        out_file = self.context.cwd / "output.txt"
        self.assertTrue(out_file.exists())
        self.assertEqual(out_file.read_text(encoding="utf-8").strip(), "antigravity shell")

    def test_append_redirection(self):
        out_file = self.context.cwd / "log.txt"
        out_file.write_text("line 1\n", encoding="utf-8")

        stmts = self.parser.parse("echo 'line 2' >> log.txt", self.context)
        code = self.executor.execute_statements(stmts)
        self.assertEqual(code, 0)

        lines = out_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines, ["line 1", "line 2"])

    def test_input_redirection(self):
        in_file = self.context.cwd / "input.txt"
        in_file.write_text("hello from input\n", encoding="utf-8")

        stmts = self.parser.parse("cat < input.txt", self.context)
        code = self.executor.execute_statements(stmts)
        self.assertEqual(code, 0)
        self.assertIn("hello from input", self.stdout.getvalue())

    def test_conditional_and_operator(self):
        # && operator: second runs only if first succeeds
        stmts = self.parser.parse("echo step1 && echo step2", self.context)
        self.executor.execute_statements(stmts)
        val = self.stdout.getvalue()
        self.assertIn("step1", val)
        self.assertIn("step2", val)

        # First fails: second must NOT run
        self.stdout.seek(0)
        self.stdout.truncate(0)
        stmts = self.parser.parse("cd non_existent_dir_12345 && echo should_not_run", self.context)
        self.executor.execute_statements(stmts)
        self.assertNotIn("should_not_run", self.stdout.getvalue())

    def test_conditional_or_operator(self):
        # || operator: second runs only if first fails
        stmts = self.parser.parse("cd non_existent_dir_12345 || echo fallback_executed", self.context)
        self.executor.execute_statements(stmts)
        self.assertIn("fallback_executed", self.stdout.getvalue())

    def test_command_not_found(self):
        stmts = self.parser.parse("nonexistent_binary_xyz123 arg", self.context)
        code = self.executor.execute_statements(stmts)
        self.assertEqual(code, 127)
        self.assertIn("command not found", self.stderr.getvalue())

    def test_external_command_execution(self):
        # Execute python as external command
        stmts = self.parser.parse(f'{sys.executable} -c "import sys; sys.exit(42)"', self.context)
        code = self.executor.execute_statements(stmts)
        self.assertEqual(code, 42)
        self.assertEqual(self.context.last_exit_code, 42)


if __name__ == "__main__":
    unittest.main()
