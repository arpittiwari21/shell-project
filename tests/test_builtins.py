"""
Unit tests for native shell built-in commands.
"""

import io
import os
import tempfile
import unittest
from pathlib import Path

from shell.builtins.registry import registry
from shell.core.context import ShellContext


class TestBuiltins(unittest.TestCase):
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

    def test_pwd_and_cd(self):
        pwd = registry.get("pwd")
        cd = registry.get("cd")
        self.assertIsNotNone(pwd)
        self.assertIsNotNone(cd)

        # Test pwd
        code = pwd.execute([], self.context)
        self.assertEqual(code, 0)
        self.assertIn(self.temp_dir.name, self.stdout.getvalue())

        # Create subfolder and cd
        sub = Path(self.temp_dir.name) / "sub"
        sub.mkdir()
        code = cd.execute(["sub"], self.context)
        self.assertEqual(code, 0)
        self.assertEqual(self.context.cwd, sub.resolve())

        # cd -
        code = cd.execute(["-"], self.context)
        self.assertEqual(code, 0)
        self.assertEqual(self.context.cwd, Path(self.temp_dir.name).resolve())

    def test_echo_and_env_operations(self):
        echo = registry.get("echo")
        export_cmd = registry.get("export")
        unset_cmd = registry.get("unset")

        # Echo
        echo.execute(["Hello", "World"], self.context)
        self.assertEqual(self.stdout.getvalue().strip(), "Hello World")

        # Export
        export_cmd.execute(["FOO=BAR123"], self.context)
        self.assertEqual(self.context.get_env("FOO"), "BAR123")

        # Unset
        unset_cmd.execute(["FOO"], self.context)
        self.assertIsNone(self.context.get_env("FOO"))

    def test_file_operations(self):
        touch = registry.get("touch")
        cat = registry.get("cat")
        cp = registry.get("cp")
        mv = registry.get("mv")
        rm = registry.get("rm")
        mkdir = registry.get("mkdir")

        # mkdir
        self.assertEqual(mkdir.execute(["new_dir"], self.context), 0)
        self.assertTrue((self.context.cwd / "new_dir").is_dir())

        # touch
        self.assertEqual(touch.execute(["test.txt"], self.context), 0)
        test_file = self.context.cwd / "test.txt"
        self.assertTrue(test_file.is_file())

        # write content and cat
        test_file.write_text("shell contents\n", encoding="utf-8")
        self.stdout.seek(0)
        self.stdout.truncate(0)
        self.assertEqual(cat.execute(["test.txt"], self.context), 0)
        self.assertIn("shell contents", self.stdout.getvalue())

        # cp
        self.assertEqual(cp.execute(["test.txt", "copy.txt"], self.context), 0)
        self.assertTrue((self.context.cwd / "copy.txt").is_file())

        # mv
        self.assertEqual(mv.execute(["copy.txt", "renamed.txt"], self.context), 0)
        self.assertFalse((self.context.cwd / "copy.txt").exists())
        self.assertTrue((self.context.cwd / "renamed.txt").is_file())

        # rm
        self.assertEqual(rm.execute(["renamed.txt"], self.context), 0)
        self.assertFalse((self.context.cwd / "renamed.txt").exists())

    def test_alias_management(self):
        alias = registry.get("alias")
        unalias = registry.get("unalias")

        alias.execute(["g=git status"], self.context)
        self.assertEqual(self.context.get_alias("g"), "git status")

        unalias.execute(["g"], self.context)
        self.assertIsNone(self.context.get_alias("g"))

    def test_exit_builtin(self):
        exit_cmd = registry.get("exit")
        self.assertTrue(self.context.is_running)
        code = exit_cmd.execute(["7"], self.context)
        self.assertEqual(code, 7)
        self.assertFalse(self.context.is_running)

    def test_dirs_pushd_popd(self):
        pushd = registry.get("pushd")
        popd = registry.get("popd")
        dirs = registry.get("dirs")

        sub = Path(self.temp_dir.name) / "d1"
        sub.mkdir()

        self.assertEqual(pushd.execute(["d1"], self.context), 0)
        self.assertEqual(self.context.cwd, sub.resolve())

        self.assertEqual(dirs.execute([], self.context), 0)

        self.assertEqual(popd.execute([], self.context), 0)
        self.assertEqual(self.context.cwd, Path(self.temp_dir.name).resolve())

    def test_sys_info_builtins(self):
        system = registry.get("system")
        disk = registry.get("disk")
        history = registry.get("history")
        help_cmd = registry.get("help")
        clear = registry.get("clear")

        self.assertEqual(system.execute([], self.context), 0)
        self.assertEqual(disk.execute([], self.context), 0)
        self.assertEqual(clear.execute([], self.context), 0)

        self.context.history.add("echo test1")
        self.assertEqual(history.execute([], self.context), 0)
        self.assertIn("echo test1", self.stdout.getvalue())

        self.assertEqual(help_cmd.execute([], self.context), 0)
        self.assertIn("Built-in Commands Reference", self.stdout.getvalue())
        self.assertEqual(help_cmd.execute(["cd"], self.context), 0)


if __name__ == "__main__":
    unittest.main()
