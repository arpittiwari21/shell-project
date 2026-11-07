"""
Shell Context - Encapsulates shell runtime state according to Single Responsibility Principle.

Maintains environment variables, current working directory, exit status codes,
aliases, job tracking, history, and stream abstractions.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from shell.core.history import HistoryManager


@dataclass
class JobInfo:
    """Represents an active or background job managed by the shell."""
    job_id: int
    pid: int
    command: str
    status: str = "Running"  # Running, Stopped, Terminated, Done


class ShellContext:
    """
    Encapsulates all mutable state for the interactive shell session.
    
    Adheres to the Open-Closed Principle and Dependency Inversion:
    Executors and builtins receive this context instead of accessing global state.
    """

    def __init__(
        self,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
        stderr: Optional[TextIO] = None,
        history_file: Optional[str] = None,
    ) -> None:
        self.env: Dict[str, str] = dict(os.environ) if env is None else env.copy()
        self.shell_vars: Dict[str, str] = {}
        self.cwd: Path = Path(cwd).resolve() if cwd else Path.cwd().resolve()
        self.old_cwd: Optional[Path] = None
        self.dir_stack: List[Path] = [self.cwd]

        self.last_exit_code: int = 0
        self.is_running: bool = True
        self.foreground_pid: Optional[int] = None

        self.aliases: Dict[str, str] = {}
        self.jobs: Dict[int, JobInfo] = {}
        self._next_job_id: int = 1

        self.history: HistoryManager = HistoryManager(history_file=history_file)

        # Standard I/O stream abstraction for testing and redirection
        self.stdin: TextIO = stdin or sys.stdin
        self.stdout: TextIO = stdout or sys.stdout
        self.stderr: TextIO = stderr or sys.stderr

        # Sync process working directory
        try:
            os.chdir(self.cwd)
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # Directory & Navigation Management
    # -------------------------------------------------------------------------

    def change_dir(self, target: str) -> None:
        """
        Change working directory with support for '~', '-', and relative paths.
        Updates PWD and OLDPWD environment variables.
        """
        target_path: Path
        cleaned = target.strip()

        if not cleaned or cleaned == "~":
            target_path = Path.home()
        elif cleaned == "-":
            if self.old_cwd is None:
                raise ValueError("cd: OLDPWD not set")
            target_path = self.old_cwd
        else:
            expanded = os.path.expanduser(cleaned)
            target_path = (self.cwd / expanded).resolve()

        if not target_path.exists():
            raise FileNotFoundError(f"cd: no such file or directory: {target}")
        if not target_path.is_dir():
            raise NotADirectoryError(f"cd: not a directory: {target}")

        self.old_cwd = self.cwd
        self.cwd = target_path
        os.chdir(self.cwd)
        self.env["OLDPWD"] = str(self.old_cwd)
        self.env["PWD"] = str(self.cwd)

    def push_dir(self, target: str) -> None:
        """Push a directory onto the directory stack and change to it."""
        self.dir_stack.append(self.cwd)
        self.change_dir(target)

    def pop_dir(self) -> Path:
        """Pop a directory from the directory stack and change to it."""
        if len(self.dir_stack) <= 1:
            raise IndexError("popd: directory stack empty")
        prev = self.dir_stack.pop()
        self.change_dir(str(prev))
        return self.cwd

    # -------------------------------------------------------------------------
    # Environment & Shell Variables
    # -------------------------------------------------------------------------

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Lookup environment variable, falling back to local shell variable."""
        return self.env.get(key, self.shell_vars.get(key, default))

    def set_env(self, key: str, value: str, export: bool = True) -> None:
        """Set a variable. If export=True, syncs with OS environment."""
        if export:
            self.env[key] = value
            os.environ[key] = value
        else:
            self.shell_vars[key] = value

    def unset_env(self, key: str) -> None:
        """Remove variable from environment and local shell vars."""
        self.env.pop(key, None)
        self.shell_vars.pop(key, None)
        os.environ.pop(key, None)

    # -------------------------------------------------------------------------
    # Aliases
    # -------------------------------------------------------------------------

    def set_alias(self, name: str, command: str) -> None:
        """Set a command alias."""
        self.aliases[name.strip()] = command.strip()

    def get_alias(self, name: str) -> Optional[str]:
        """Retrieve alias expansion if registered."""
        return self.aliases.get(name.strip())

    def remove_alias(self, name: str) -> bool:
        """Remove alias; returns True if deleted, False if not present."""
        return self.aliases.pop(name.strip(), None) is not None

    # -------------------------------------------------------------------------
    # Job Control Management
    # -------------------------------------------------------------------------

    def add_job(self, pid: int, command: str, status: str = "Running") -> JobInfo:
        """Register a new background job."""
        job_id = self._next_job_id
        self._next_job_id += 1
        job = JobInfo(job_id=job_id, pid=pid, command=command, status=status)
        self.jobs[job_id] = job
        return job

    def remove_job_by_pid(self, pid: int) -> Optional[JobInfo]:
        """Remove a job by PID."""
        for jid, job in list(self.jobs.items()):
            if job.pid == pid:
                return self.jobs.pop(jid)
        return None

    def get_job(self, job_id: int) -> Optional[JobInfo]:
        """Lookup job by numeric Job ID."""
        return self.jobs.get(job_id)

    # -------------------------------------------------------------------------
    # Execution State
    # -------------------------------------------------------------------------

    def update_exit_code(self, code: int) -> None:
        """Update last exit code ($?)."""
        self.last_exit_code = code

    def terminate(self) -> None:
        """Flag shell to terminate its interactive loop."""
        self.is_running = False
