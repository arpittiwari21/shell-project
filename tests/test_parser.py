"""
Unit tests for shell.core.parser (Lexer, Tokenizer, Variable Expansion, AST generation).
"""

import io
import unittest
from shell.core.context import ShellContext
from shell.core.parser import CommandParser


class TestCommandParser(unittest.TestCase):
    def setUp(self):
        self.context = ShellContext(
            stdin=io.StringIO(),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            history_file=None,
        )
        self.context.set_env("GREETING", "Hello")
        self.context.set_env("TARGET", "World")
        self.parser = CommandParser(self.context)

    def test_simple_command(self):
        stmts = self.parser.parse("echo foo bar", self.context)
        self.assertEqual(len(stmts), 1)
        cmd = stmts[0].pipeline.commands[0]
        self.assertEqual(cmd.command_name, "echo")
        self.assertEqual(cmd.args, ["echo", "foo", "bar"])

    def test_single_quotes_preservation(self):
        stmts = self.parser.parse("echo 'hello world $GREETING'", self.context)
        cmd = stmts[0].pipeline.commands[0]
        self.assertEqual(cmd.args, ["echo", "hello world $GREETING"])

    def test_double_quotes_and_variable_expansion(self):
        stmts = self.parser.parse('echo "$GREETING, ${TARGET}!"', self.context)
        cmd = stmts[0].pipeline.commands[0]
        self.assertEqual(cmd.args, ["echo", "Hello, World!"])

    def test_exit_code_expansion(self):
        self.context.update_exit_code(42)
        stmts = self.parser.parse("echo last exit was $?", self.context)
        cmd = stmts[0].pipeline.commands[0]
        self.assertEqual(cmd.args, ["echo", "last", "exit", "was", "42"])

    def test_alias_expansion(self):
        self.context.set_alias("ll", "ls -la")
        stmts = self.parser.parse("ll /tmp", self.context)
        cmd = stmts[0].pipeline.commands[0]
        self.assertEqual(cmd.args, ["ls", "-la", "/tmp"])

    def test_pipeline_parsing(self):
        stmts = self.parser.parse("cat file.txt | grep 'pattern' | wc -l", self.context)
        self.assertEqual(len(stmts), 1)
        commands = stmts[0].pipeline.commands
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[0].args, ["cat", "file.txt"])
        self.assertEqual(commands[1].args, ["grep", "pattern"])
        self.assertEqual(commands[2].args, ["wc", "-l"])

    def test_redirection_parsing(self):
        stmts = self.parser.parse("echo hello > out.txt 2> err.log < in.txt", self.context)
        cmd = stmts[0].pipeline.commands[0]
        self.assertEqual(cmd.args, ["echo", "hello"])
        self.assertEqual(len(cmd.redirections), 3)

        # Verify redirections
        redirs = {r.source_fd: r for r in cmd.redirections}
        self.assertIn(1, redirs)
        self.assertEqual(redirs[1].target, "out.txt")
        self.assertEqual(redirs[1].mode, "w")

        self.assertIn(2, redirs)
        self.assertEqual(redirs[2].target, "err.log")

        self.assertIn(0, redirs)
        self.assertEqual(redirs[0].target, "in.txt")
        self.assertEqual(redirs[0].mode, "r")

    def test_append_redirection(self):
        stmts = self.parser.parse("echo line >> log.txt", self.context)
        cmd = stmts[0].pipeline.commands[0]
        self.assertEqual(len(cmd.redirections), 1)
        self.assertEqual(cmd.redirections[0].mode, "a")
        self.assertEqual(cmd.redirections[0].target, "log.txt")

    def test_statement_chaining(self):
        stmts = self.parser.parse("mkdir test && cd test ; ls || echo fail", self.context)
        self.assertEqual(len(stmts), 4)
        self.assertEqual(stmts[0].operator, ";")
        self.assertEqual(stmts[0].pipeline.commands[0].command_name, "mkdir")
        self.assertEqual(stmts[1].operator, "&&")
        self.assertEqual(stmts[1].pipeline.commands[0].command_name, "cd")
        self.assertEqual(stmts[2].operator, ";")
        self.assertEqual(stmts[2].pipeline.commands[0].command_name, "ls")
        self.assertEqual(stmts[3].operator, "||")
        self.assertEqual(stmts[3].pipeline.commands[0].command_name, "echo")

    def test_background_flag(self):
        stmts = self.parser.parse("sleep 10 &", self.context)
        self.assertTrue(stmts[0].pipeline.is_background)
        self.assertTrue(stmts[0].pipeline.commands[0].is_background)


if __name__ == "__main__":
    unittest.main()
