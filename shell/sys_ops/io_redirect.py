"""
I/O Redirection - Handles file descriptor duplication and stream redirections (<, >, >>, 2>, &>).
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, TextIO, Tuple

if TYPE_CHECKING:
    from shell.core.context import ShellContext
    from shell.core.parser import Redirection


class IORedirector:
    """
    Manages input/output/error streams for commands, providing both Python stream
    redirection (for builtins) and low-level OS file descriptor redirection (for external processes).
    """

    @staticmethod
    def get_subprocess_handles(
        redirections: List[Redirection],
        context: ShellContext,
    ) -> Tuple[Optional[int], Optional[int], Optional[int], List[int]]:
        """
        Open files corresponding to redirections and return (stdin_fd, stdout_fd, stderr_fd, opened_fds).
        The caller is responsible for closing opened_fds after process launch.
        """
        stdin_fd: Optional[int] = None
        stdout_fd: Optional[int] = None
        stderr_fd: Optional[int] = None
        opened_fds: List[int] = []

        for redir in redirections:
            target_path = redir.target
            # Resolve relative to context cwd
            resolved = str(context.cwd / target_path) if not os.path.isabs(target_path) else target_path

            if redir.source_fd == 0:  # <
                fd = os.open(resolved, os.O_RDONLY)
                stdin_fd = fd
                opened_fds.append(fd)

            elif redir.source_fd == 1:  # >, >>
                flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if redir.mode == "a" else os.O_TRUNC)
                fd = os.open(resolved, flags, 0o666)
                stdout_fd = fd
                opened_fds.append(fd)

            elif redir.source_fd == 2:  # 2>, 2>>
                if redir.is_fd_dup and redir.dup_target_fd == 1:
                    stderr_fd = stdout_fd or sys.stdout.fileno()
                else:
                    flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if redir.mode == "a" else os.O_TRUNC)
                    fd = os.open(resolved, flags, 0o666)
                    stderr_fd = fd
                    opened_fds.append(fd)

            elif redir.source_fd == -1:  # &> (both stdout and stderr)
                flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
                fd = os.open(resolved, flags, 0o666)
                stdout_fd = fd
                stderr_fd = fd
                opened_fds.append(fd)

        return stdin_fd, stdout_fd, stderr_fd, opened_fds

    @staticmethod
    @contextmanager
    def apply_context_streams(
        redirections: List[Redirection],
        context: ShellContext,
    ) -> Generator[None, None, None]:
        """
        Context manager that temporarily points context.stdin, context.stdout,
        context.stderr to opened files for the duration of a builtin command execution.
        """
        orig_stdin = context.stdin
        orig_stdout = context.stdout
        orig_stderr = context.stderr

        opened_files: List[TextIO] = []

        try:
            for redir in redirections:
                target_path = redir.target
                resolved = (context.cwd / target_path).resolve() if not os.path.isabs(target_path) else os.path.abspath(target_path)

                if redir.source_fd == 0:  # <
                    f = open(resolved, "r", encoding="utf-8", errors="replace")
                    opened_files.append(f)
                    context.stdin = f

                elif redir.source_fd == 1:  # >, >>
                    f = open(resolved, redir.mode, encoding="utf-8", errors="replace")
                    opened_files.append(f)
                    context.stdout = f

                elif redir.source_fd == 2:  # 2>, 2>>
                    if redir.is_fd_dup and redir.dup_target_fd == 1:
                        context.stderr = context.stdout
                    else:
                        f = open(resolved, redir.mode, encoding="utf-8", errors="replace")
                        opened_files.append(f)
                        context.stderr = f

                elif redir.source_fd == -1:  # &>
                    f = open(resolved, "w", encoding="utf-8", errors="replace")
                    opened_files.append(f)
                    context.stdout = f
                    context.stderr = f

            yield

        finally:
            # Flush and close all opened redirection files
            for f in opened_files:
                try:
                    f.flush()
                    f.close()
                except OSError:
                    pass

            context.stdin = orig_stdin
            context.stdout = orig_stdout
            context.stderr = orig_stderr
