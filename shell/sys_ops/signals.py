"""
Signal Handling - Robust signal trapping for SIGINT (Ctrl+C), SIGTSTP (Ctrl+Z), and SIGCHLD.
Protects the interactive parent shell from crashing when child processes are interrupted.
"""

from __future__ import annotations

import os
import signal
import sys
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from shell.core.context import ShellContext


class SignalManager:
    """
    Manages low-level OS signals with cross-platform compatibility (POSIX and Windows).
    Ensures foreground child processes receive interrupts without terminating the shell.
    """

    def __init__(self, context: Optional[ShellContext] = None) -> None:
        self.context = context
        self._orig_sigint = signal.getsignal(signal.SIGINT)
        self._interrupted = False

    def setup_handlers(self, context: Optional[ShellContext] = None) -> None:
        """Configure shell signal handlers."""
        if context:
            self.context = context

        # SIGINT: Ctrl+C
        signal.signal(signal.SIGINT, self._handle_sigint)

        # SIGTSTP: Ctrl+Z (Unix only)
        if hasattr(signal, "SIGTSTP"):
            signal.signal(signal.SIGTSTP, self._handle_sigtstp)

        # SIGCHLD: Child process state change (Unix only)
        if hasattr(signal, "SIGCHLD"):
            signal.signal(signal.SIGCHLD, self._handle_sigchld)

    def restore_handlers(self) -> None:
        """Restore original default signal handlers."""
        signal.signal(signal.SIGINT, self._orig_sigint)
        if hasattr(signal, "SIGTSTP"):
            signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        if hasattr(signal, "SIGCHLD"):
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    def _handle_sigint(self, signum: int, frame: Optional[object]) -> None:
        """
        Handle Ctrl+C.
        If a foreground child process is active, delegate interruption to it.
        Otherwise, clear line and print a fresh prompt newline.
        """
        self._interrupted = True

        if self.context and self.context.foreground_pid:
            pid = self.context.foreground_pid
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(pid), signal.SIGINT)
                else:
                    os.kill(pid, signal.SIGINT)
            except (ProcessLookupError, PermissionError, OSError):
                pass
            return

        # Interactive parent shell interruption
        sys.stdout.write("\n")
        sys.stdout.flush()

    def _handle_sigtstp(self, signum: int, frame: Optional[object]) -> None:
        """Handle Ctrl+Z: Suspend current foreground child process."""
        if self.context and self.context.foreground_pid:
            pid = self.context.foreground_pid
            try:
                if os.name == "posix":
                    os.kill(pid, signal.SIGTSTP)
                    self.context.add_job(pid, f"<pid {pid}>", status="Stopped")
                    sys.stdout.write(f"\n[Job stopped] PID: {pid}\n")
                    sys.stdout.flush()
            except OSError:
                pass

    def _handle_sigchld(self, signum: int, frame: Optional[object]) -> None:
        """Reap terminated child processes on POSIX to prevent zombies."""
        if not hasattr(os, "waitpid"):
            return
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid <= 0:
                    break
                if self.context:
                    self.context.remove_job_by_pid(pid)
            except (ChildProcessError, OSError):
                break

    @property
    def was_interrupted(self) -> bool:
        """Check and reset interrupt flag."""
        val = self._interrupted
        self._interrupted = False
        return val
