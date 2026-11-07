"""
System Information and Shell Utility Built-ins - system, disk, ip, clear, history, help.
Preserves and elevates the diagnostic features of the original shell project.
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
from typing import TYPE_CHECKING, List

from shell.builtins.base import BaseBuiltin
from shell.builtins.registry import register_builtin

if TYPE_CHECKING:
    from shell.core.context import ShellContext


@register_builtin
class SystemBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return "Display detailed operating system, CPU, and memory metrics."

    @property
    def usage(self) -> str:
        return "system"

    def execute(self, args: List[str], context: ShellContext) -> int:
        self.write(context, "\n--- System Information ---\n")
        self.write(context, f"  OS:           {platform.system()} {platform.release()} ({platform.version()})\n")
        self.write(context, f"  Architecture: {platform.machine()} ({platform.architecture()[0]})\n")
        self.write(context, f"  Processor:    {platform.processor() or 'Unknown'}\n")
        self.write(context, f"  Python:       {platform.python_version()}\n")

        # Memory details via psutil or fallback
        try:
            import psutil
            mem = psutil.virtual_memory()
            total_gb = round(mem.total / (1024**3), 2)
            used_gb = round(mem.used / (1024**3), 2)
            cpu_pct = psutil.cpu_percent(interval=0.2)
            self.write(context, f"  Total RAM:    {total_gb} GB\n")
            self.write(context, f"  Used RAM:     {used_gb} GB ({mem.percent}%)\n")
            self.write(context, f"  CPU Usage:    {cpu_pct}%\n")
        except ImportError:
            self.write(context, "  Memory/CPU:   (Install psutil for real-time memory/CPU usage)\n")

        self.write(context, "--------------------------\n\n")
        return 0


@register_builtin
class DiskBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "disk"

    @property
    def description(self) -> str:
        return "Display filesystem disk usage, capacity, and available space."

    @property
    def usage(self) -> str:
        return "disk [path]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        target_path = args[0] if args else str(context.cwd)
        try:
            total, used, free = shutil.disk_usage(target_path)
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            used_pct = (used / total) * 100 if total > 0 else 0

            self.write(context, f"\nDisk Space for '{target_path}':\n")
            self.write(context, f"  Total: {total_gb:>8.2f} GB\n")
            self.write(context, f"  Used:  {used_gb:>8.2f} GB ({used_pct:.1f}%)\n")
            self.write(context, f"  Free:  {free_gb:>8.2f} GB\n\n")
            return 0
        except Exception as e:
            self.write_err(context, f"disk: error checking disk space: {e}\n")
            return 1


@register_builtin
class IpBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "ip"

    @property
    def description(self) -> str:
        return "Display local network hostname, IP address, and gateway info."

    @property
    def usage(self) -> str:
        return "ip"

    def execute(self, args: List[str], context: ShellContext) -> int:
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            self.write(context, "\nNetwork Information:\n")
            self.write(context, f"  Hostname:   {hostname}\n")
            self.write(context, f"  Local IP:   {local_ip}\n")

            # Best-effort external IP lookup
            try:
                import urllib.request
                req = urllib.request.Request(
                    "https://api.ipify.org",
                    headers={"User-Agent": "myOS-Shell/1.0"}
                )
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    ext_ip = resp.read().decode("utf-8").strip()
                    self.write(context, f"  Public IP:  {ext_ip}\n")
            except Exception:
                pass

            self.write(context, "\n")
            return 0
        except Exception as e:
            self.write_err(context, f"ip: error retrieving network details: {e}\n")
            return 1


@register_builtin
class ClearBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "clear"

    @property
    def description(self) -> str:
        return "Clear the terminal screen."

    @property
    def usage(self) -> str:
        return "clear"

    def execute(self, args: List[str], context: ShellContext) -> int:
        # Standard ANSI clear sequence
        self.write(context, "\033[2J\033[H")
        return 0


@register_builtin
class HistoryBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "history"

    @property
    def description(self) -> str:
        return "Display or clear the command history list."

    @property
    def usage(self) -> str:
        return "history [-c]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if args and args[0] == "-c":
            context.history.clear()
            self.write(context, "History cleared.\n")
            return 0

        entries = context.history.get_all()
        if not entries:
            self.write(context, "No commands recorded in history.\n")
            return 0

        self.write(context, "\nCommand History:\n")
        for i, cmd in enumerate(entries, 1):
            self.write(context, f"  {i:>4}  {cmd}\n")
        self.write(context, "\n")
        return 0


@register_builtin
class HelpBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "help"

    @property
    def description(self) -> str:
        return "Display help for built-in shell commands."

    @property
    def usage(self) -> str:
        return "help [command]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        from shell.builtins.registry import registry

        if args:
            target = args[0]
            cmd = registry.get(target)
            if not cmd:
                self.write_err(context, f"help: no help topics match '{target}'. Try 'help'.\n")
                return 1

            self.write(context, f"\nCommand: {cmd.name}\n")
            self.write(context, f"  Description: {cmd.description}\n")
            self.write(context, f"  Usage:       {cmd.usage}\n")
            if cmd.aliases:
                self.write(context, f"  Aliases:     {', '.join(cmd.aliases)}\n")
            self.write(context, "\n")
            return 0

        # General help list
        all_builtins = registry.list_all()
        self.write(context, "\n" + "=" * 65 + "\n")
        self.write(context, " myOS Shell - Built-in Commands Reference\n")
        self.write(context, "=" * 65 + "\n\n")

        for name, cmd in sorted(all_builtins.items()):
            self.write(context, f"  {cmd.usage:<32} - {cmd.description}\n")

        self.write(context, "\nType 'help <command>' for specific details.\n")
        self.write(context, "External system commands and pipelines (cmd1 | cmd2) are fully supported.\n\n")
        return 0
