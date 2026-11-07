"""
Integration tests for PipelineRunner (IPC pipes and chained commands).
"""

import io
import os
import sys
import tempfile
import unittest

from shell.builtins.registry import registry
from shell.core.context import ShellContext
from shell.core.parser import CommandParser
from shell.sys_ops.pipelines import PipelineRunner


class TestPipelines(unittest.TestCase):
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
        self.runner = PipelineRunner(self.context, registry)

    def tearDown(self):
        import os
        os.chdir(self.orig_cwd)
        self.temp_dir.cleanup()

    def test_pipeline_with_python_filter(self):
        # Pipeline: echo "modular architecture" | python -c "import sys; print(sys.stdin.read().upper().strip())"
        py_code = "import sys; print(sys.stdin.read().upper().strip())"
        cmd_line = f'{sys.executable} -c "print(\'modular architecture\')" | {sys.executable} -c "{py_code}"'

        stmts = self.parser.parse(cmd_line, self.context)
        self.assertEqual(len(stmts), 1)

        code = self.runner.run_pipeline(stmts[0].pipeline)
        self.assertEqual(code, 0)

    def test_multi_stage_pipeline(self):
        # 3 stage pipeline with python filter
        cmd_line = (
            f'{sys.executable} -c "print(\'one\\ntwo\\nthree\')" | '
            f'{sys.executable} -c "import sys; lines = [l for l in sys.stdin if \'t\' in l]; sys.stdout.write(\'\'.join(lines))" | '
            f'{sys.executable} -c "import sys; print(len(sys.stdin.readlines()))"'
        )

        stmts = self.parser.parse(cmd_line, self.context)
        code = self.runner.run_pipeline(stmts[0].pipeline)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
