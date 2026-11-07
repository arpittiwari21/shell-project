"""
Command Executor - Orchestrates statement flow, process creation, redirection, and built-in dispatch.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from shell.builtins.registry import BuiltinRegistry
    from shell.core.context import ShellContext
    from shell.core.parser import CommandNode, ParsedStatement, PipelineNode


class CommandExecutor:
    """
    Executes parsed statements, coordinating builtin command dispatch,
    piping, external process spawning, and exit status tracking.
    """

    def __init__(
        self,
        context: ShellContext,
        registry: BuiltinRegistry,
    ) -> None:
        self.context = context
        self.registry = registry

    def execute_statements(self, statements: List[ParsedStatement]) -> int:
        """
        Execute a sequence of parsed statements with conditional chaining (;, &&, ||).
        """
        last_exit = 0

        for i, stmt in enumerate(statements):
            op = stmt.operator

            # Conditional short-circuiting
            if i > 0:
                if op == "&&" and last_exit != 0:
                    continue
                if op == "||" and last_exit == 0:
                    continue

            last_exit = self.execute_pipeline(stmt.pipeline)
            self.context.update_exit_code(last_exit)

            # Check if an exit/quit builtin was invoked
            if not self.context.is_running:
                break

        return last_exit

    def execute_pipeline(self, pipeline: PipelineNode) -> int:
        """Execute a pipeline, handling background '&' execution if flagged."""
        if pipeline.is_background:
            def bg_worker():
                from shell.sys_ops.pipelines import PipelineRunner
                runner = PipelineRunner(self.context, self.registry)
                runner.run_pipeline(pipeline)

            cmd_str = " | ".join(" ".join(c.args) for c in pipeline.commands)
            thread = threading.Thread(target=bg_worker, daemon=True)
            thread.start()
            # Register pseudo job
            job = self.context.add_job(pid=thread.ident or 0, command=cmd_str, status="Running")
            self.context.stdout.write(f"[{job.job_id}] {cmd_str} &\n")
            self.context.stdout.flush()
            return 0

        from shell.sys_ops.pipelines import PipelineRunner
        runner = PipelineRunner(self.context, self.registry)
        return runner.run_pipeline(pipeline)

    def execute_single_command(self, cmd_node: CommandNode) -> int:
        """
        Execute an un-piped command, dispatching to either a registered builtin
        or spawning an external process with proper I/O redirection.
        """
        if not cmd_node.args:
            return 0

        cmd_name = cmd_node.command_name
        args = cmd_node.args[1:]

        # 1. Built-in command dispatch
        builtin = self.registry.get(cmd_name)
        if builtin:
            from shell.sys_ops.io_redirect import IORedirector
            try:
                with IORedirector.apply_context_streams(cmd_node.redirections, self.context):
                    code = builtin.execute(args, self.context)
                    self.context.update_exit_code(code)
                    return code
            except Exception as e:
                self.context.stderr.write(f"{cmd_name}: error during execution: {e}\n")
                self.context.stderr.flush()
                self.context.update_exit_code(1)
                return 1

        # 2. External command dispatch
        return self._execute_external(cmd_node)

    def _execute_external(self, cmd_node: CommandNode) -> int:
        """
        Spawns external process using controlled process isolation.
        Traps SIGINT, manages redirection handles, and returns exit code.
        """
        from shell.sys_ops.io_redirect import IORedirector

        cmd_name = cmd_node.command_name

        # Resolve binary path
        resolved_bin = None
        if os.path.isfile(cmd_name) or (os.name == "nt" and any(os.path.isfile(cmd_name + ext) for ext in ("", ".exe", ".bat", ".cmd"))):
            resolved_bin = cmd_name
        else:
            resolved_bin = shutil.which(cmd_name, path=self.context.env.get("PATH"))

        if not resolved_bin:
            self.context.stderr.write(f"myOS: {cmd_name}: command not found\n")
            self.context.stderr.flush()
            self.context.update_exit_code(127)
            return 127

        stdin_fd, stdout_fd, stderr_fd, opened_fds = IORedirector.get_subprocess_handles(
            cmd_node.redirections, self.context
        )

        try:
            # POSIX fork/exec execution path when available and not in background
            if os.name == "posix" and not cmd_node.is_background:
                return self._posix_fork_exec(cmd_node, resolved_bin, stdin_fd, stdout_fd, stderr_fd)

            # Portable subprocess execution (Windows and fallback)
            proc = subprocess.Popen(
                [resolved_bin] + cmd_node.args[1:],
                stdin=stdin_fd,
                stdout=stdout_fd,
                stderr=stderr_fd,
                cwd=str(self.context.cwd),
                env=self.context.env,
                shell=False,
            )

            if cmd_node.is_background:
                job = self.context.add_job(proc.pid, " ".join(cmd_node.args), status="Running")
                self.context.stdout.write(f"[{job.job_id}] {proc.pid}\n")
                self.context.stdout.flush()
                return 0

            # Foreground execution with PID tracking for signal handling
            self.context.foreground_pid = proc.pid
            try:
                exit_code = proc.wait()
            except KeyboardInterrupt:
                exit_code = 130
            finally:
                self.context.foreground_pid = None

            self.context.update_exit_code(exit_code)
            return exit_code

        except PermissionError:
            self.context.stderr.write(f"myOS: {cmd_name}: permission denied\n")
            self.context.stderr.flush()
            self.context.update_exit_code(126)
            return 126
        except Exception as e:
            self.context.stderr.write(f"myOS: {cmd_name}: execution failure: {e}\n")
            self.context.stderr.flush()
            self.context.update_exit_code(1)
            return 1
        finally:
            for fd in opened_fds:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _posix_fork_exec(
        self,
        cmd_node: CommandNode,
        executable: str,
        stdin_fd: Optional[int],
        stdout_fd: Optional[int],
        stderr_fd: Optional[int],
    ) -> int:
        """Low-level POSIX process creation using fork and execvp."""
        pid = os.fork()

        if pid == 0:
            # --- Child Process ---
            try:
                # Reset signal handlers in child
                import signal
                signal.signal(signal.SIGINT, signal.SIG_DFL)

                # Duplicate redirected file descriptors
                if stdin_fd is not None:
                    os.dup2(stdin_fd, 0)
                if stdout_fd is not None:
                    os.dup2(stdout_fd, 1)
                if stderr_fd is not None:
                    os.dup2(stderr_fd, 2)

                # Execute binary
                os.execvpe(executable, [cmd_node.command_name] + cmd_node.args[1:], self.context.env)
            except Exception as e:
                sys.stderr.write(f"child exec error: {e}\n")
                sys.exit(127)
        else:
            # --- Parent Process ---
            self.context.foreground_pid = pid
            try:
                _, status = os.waitpid(pid, 0)
                if os.WIFEXITED(status):
                    return os.WEXITSTATUS(status)
                elif os.WIFSIGNALED(status):
                    return 128 + os.WTERMSIG(status)
                return 1
            except KeyboardInterrupt:
                return 130
            finally:
                self.context.foreground_pid = None
