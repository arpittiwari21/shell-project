"""
Pipeline Runner - Inter-process communication and piped execution (cmd1 | cmd2 | cmd3).
Connects stdout of stage i to stdin of stage i+1 across arbitrary pipeline lengths.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import threading
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from shell.builtins.registry import BuiltinRegistry
    from shell.core.context import ShellContext
    from shell.core.parser import CommandNode, PipelineNode


class PipelineRunner:
    """
    Executes command pipelines with process isolation and stream forwarding.
    """

    def __init__(
        self,
        context: ShellContext,
        registry: BuiltinRegistry,
    ) -> None:
        self.context = context
        self.registry = registry

    def run_pipeline(self, pipeline: PipelineNode) -> int:
        """
        Execute a pipeline node of commands chained with pipes (|).
        Returns the exit code of the final command in the pipeline.
        """
        if not pipeline.commands:
            return 0

        # Fast path for single command without pipes
        if len(pipeline.commands) == 1:
            from shell.core.executor import CommandExecutor
            executor = CommandExecutor(self.context, self.registry)
            return executor.execute_single_command(pipeline.commands[0])

        return self._execute_chained_pipeline(pipeline.commands)

    def _execute_chained_pipeline(self, commands: List[CommandNode]) -> int:
        """
        Set up and execute a multi-stage pipeline.
        Pipes stdout of stage k to stdin of stage k+1.
        """
        num_cmds = len(commands)
        processes: List[Tuple[Optional[subprocess.Popen], Optional[threading.Thread]]] = []
        prev_read_fd: Optional[int] = None
        pipe_fds_to_close: List[int] = []

        last_exit_code = 0

        for i, cmd_node in enumerate(commands):
            is_first = (i == 0)
            is_last = (i == num_cmds - 1)

            # Create pipe for this stage unless it's the last stage
            curr_read_fd = None
            curr_write_fd = None
            if not is_last:
                r_fd, w_fd = os.pipe()
                curr_read_fd = r_fd
                curr_write_fd = w_fd
                pipe_fds_to_close.extend([r_fd, w_fd])

            # Determine stdin and stdout for this stage
            stdin_handle = prev_read_fd if not is_first else None
            stdout_handle = curr_write_fd if not is_last else None

            # Execute stage
            proc, thread = self._launch_stage(
                cmd_node=cmd_node,
                stdin_fd=stdin_handle,
                stdout_fd=stdout_handle,
            )
            processes.append((proc, thread))

            # Close the write end in the parent process so EOF propagates
            if curr_write_fd is not None:
                try:
                    os.close(curr_write_fd)
                except OSError:
                    pass

            # Close previous read end in parent
            if prev_read_fd is not None:
                try:
                    os.close(prev_read_fd)
                except OSError:
                    pass

            prev_read_fd = curr_read_fd

        # Close any remaining read fd
        if prev_read_fd is not None:
            try:
                os.close(prev_read_fd)
            except OSError:
                pass

        # Wait for all processes and threads in the pipeline to complete
        for proc, thread in processes:
            if proc is not None:
                code = proc.wait()
                last_exit_code = code
            if thread is not None:
                thread.join()

        return last_exit_code

    def _launch_stage(
        self,
        cmd_node: CommandNode,
        stdin_fd: Optional[int],
        stdout_fd: Optional[int],
    ) -> Tuple[Optional[subprocess.Popen], Optional[threading.Thread]]:
        """Launch a single pipeline stage as a subprocess or isolated thread."""
        from shell.sys_ops.io_redirect import IORedirector

        cmd_name = cmd_node.command_name
        builtin = self.registry.get(cmd_name)

        if builtin:
            # Run builtin in an isolated worker thread connected to the pipes
            def builtin_worker():
                in_stream = None
                out_stream = None
                orig_in = self.context.stdin
                orig_out = self.context.stdout
                try:
                    if stdin_fd is not None:
                        in_stream = os.fdopen(os.dup(stdin_fd), "r", encoding="utf-8", errors="replace")
                        self.context.stdin = in_stream
                    if stdout_fd is not None:
                        out_stream = os.fdopen(os.dup(stdout_fd), "w", encoding="utf-8", errors="replace")
                        self.context.stdout = out_stream

                    # Apply any explicit command redirections
                    with IORedirector.apply_context_streams(cmd_node.redirections, self.context):
                        builtin.execute(cmd_node.args[1:], self.context)
                finally:
                    if in_stream:
                        try:
                            in_stream.close()
                        except OSError:
                            pass
                    if out_stream:
                        try:
                            out_stream.flush()
                            out_stream.close()
                        except OSError:
                            pass
                    self.context.stdin = orig_in
                    self.context.stdout = orig_out

            thread = threading.Thread(target=builtin_worker, daemon=True)
            thread.start()
            return None, thread

        else:
            # External command
            import shutil
            resolved_bin = None
            if os.path.isfile(cmd_name) or (os.name == "nt" and any(os.path.isfile(cmd_name + ext) for ext in ("", ".exe", ".bat", ".cmd"))):
                resolved_bin = cmd_name
            else:
                resolved_bin = shutil.which(cmd_name, path=self.context.env.get("PATH")) or cmd_name

            redir_in, redir_out, redir_err, opened_fds = IORedirector.get_subprocess_handles(
                cmd_node.redirections, self.context
            )
            final_stdin = redir_in if redir_in is not None else (stdin_fd if stdin_fd is not None else None)
            final_stdout = redir_out if redir_out is not None else (stdout_fd if stdout_fd is not None else None)
            final_stderr = redir_err if redir_err is not None else None

            cmd_args = [resolved_bin] + cmd_node.args[1:]
            proc = subprocess.Popen(
                cmd_args,
                stdin=final_stdin,
                stdout=final_stdout,
                stderr=final_stderr,
                cwd=str(self.context.cwd),
                env=self.context.env,
                shell=False,
            )

            # Close duplicated file descriptors opened by redirection helper
            for fd in opened_fds:
                try:
                    os.close(fd)
                except OSError:
                    pass

            return proc, None
