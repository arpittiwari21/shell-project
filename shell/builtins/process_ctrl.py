"""
Process Control Built-ins - exit, kill, ps, jobs, fg, bg.
Manages job table, signals, and session termination.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from typing import TYPE_CHECKING, List

from shell.builtins.base import BaseBuiltin
from shell.builtins.registry import register_builtin

if TYPE_CHECKING:
    from shell.core.context import ShellContext


@register_builtin
class ExitBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "exit"

    @property
    def aliases(self) -> List[str]:
        return ["quit"]

    @property
    def description(self) -> str:
        return "Exit the interactive shell session."

    @property
    def usage(self) -> str:
        return "exit [code]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        code = 0
        if args:
            try:
                code = int(args[0])
            except ValueError:
                self.write_err(context, "exit: numeric argument required\n")
                code = 2

        self.write(context, "Exiting shell...\n")
        context.update_exit_code(code)
        context.terminate()
        return code


@register_builtin
class KillBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "kill"

    @property
    def description(self) -> str:
        return "Send a signal to a process (default: SIGTERM)."

    @property
    def usage(self) -> str:
        return "kill [-signal] <pid...>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "kill: usage: kill [-signal] <pid...>\n")
            return 1

        sig = signal.SIGTERM
        pids: List[int] = []

        for arg in args:
            if arg.startswith("-"):
                sig_str = arg[1:]
                if sig_str.isdigit():
                    sig = int(sig_str)
                elif hasattr(signal, f"SIG{sig_str.upper()}"):
                    sig = getattr(signal, f"SIG{sig_str.upper()}")
                else:
                    self.write_err(context, f"kill: invalid signal specification: {arg}\n")
                    return 1
            else:
                try:
                    pids.append(int(arg))
                except ValueError:
                    self.write_err(context, f"kill: invalid PID: '{arg}'\n")
                    return 1

        exit_code = 0
        for pid in pids:
            try:
                os.kill(pid, sig)
                self.write(context, f"Process {pid} sent signal {sig}.\n")
                context.remove_job_by_pid(pid)
            except ProcessLookupError:
                self.write_err(context, f"kill: ({pid}) - No such process\n")
                exit_code = 1
            except PermissionError:
                self.write_err(context, f"kill: ({pid}) - Operation not permitted\n")
                exit_code = 1
            except Exception as e:
                self.write_err(context, f"kill: ({pid}) - {e}\n")
                exit_code = 1

        return exit_code


@register_builtin
class PsBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "ps"

    @property
    def description(self) -> str:
        return "Report a snapshot of active system processes."

    @property
    def usage(self) -> str:
        return "ps"

    def execute(self, args: List[str], context: ShellContext) -> int:
        self.write(context, f"\n{'PID':>8}  {'NAME'}\n")
        self.write(context, "=" * 40 + "\n")

        # Try psutil if available
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    self.write(context, f"{proc.info['pid']:>8}  {proc.info['name']}\n")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self.write(context, "\n")
            return 0
        except ImportError:
            pass

        # Fallback to system tools
        try:
            if os.name == "nt":
                output = subprocess.check_output(["tasklist"], text=True, errors="replace")
            else:
                output = subprocess.check_output(["ps", "-e"], text=True, errors="replace")
            self.write(context, output + "\n")
            return 0
        except Exception as e:
            self.write_err(context, f"ps: unable to retrieve processes: {e}\n")
            return 1


@register_builtin
class JobsBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "jobs"

    @property
    def description(self) -> str:
        return "List active background jobs managed by the shell."

    @property
    def usage(self) -> str:
        return "jobs"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not context.jobs:
            self.write(context, "No active background jobs.\n")
            return 0

        for jid, job in context.jobs.items():
            self.write(context, f"[{jid}]  PID:{job.pid:<8} {job.status:<12} {job.command}\n")
        return 0


@register_builtin
class FgBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "fg"

    @property
    def description(self) -> str:
        return "Bring a background job to foreground."

    @property
    def usage(self) -> str:
        return "fg [job_id]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not context.jobs:
            self.write_err(context, "fg: no current jobs\n")
            return 1

        jid = int(args[0]) if args and args[0].isdigit() else next(iter(context.jobs))
        job = context.jobs.get(jid)
        if not job:
            self.write_err(context, f"fg: %{jid}: no such job\n")
            return 1

        self.write(context, f"{job.command}\n")
        context.foreground_pid = job.pid
        if hasattr(signal, "SIGCONT"):
            try:
                os.kill(job.pid, signal.SIGCONT)
            except OSError:
                pass

        try:
            if os.name == "posix":
                _, status = os.waitpid(job.pid, 0)
                code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 0
            else:
                code = 0
            context.remove_job_by_pid(job.pid)
            return code
        except Exception:
            return 0
        finally:
            context.foreground_pid = None


@register_builtin
class BgBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "bg"

    @property
    def description(self) -> str:
        return "Resume a stopped background job in the background."

    @property
    def usage(self) -> str:
        return "bg [job_id]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not context.jobs:
            self.write_err(context, "bg: no current jobs\n")
            return 1

        jid = int(args[0]) if args and args[0].isdigit() else next(iter(context.jobs))
        job = context.jobs.get(jid)
        if not job:
            self.write_err(context, f"bg: %{jid}: no such job\n")
            return 1

        job.status = "Running"
        if hasattr(signal, "SIGCONT"):
            try:
                os.kill(job.pid, signal.SIGCONT)
            except OSError:
                pass

        self.write(context, f"[{job.job_id}] {job.command} &\n")
        return 0
