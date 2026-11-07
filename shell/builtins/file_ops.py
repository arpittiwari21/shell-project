"""
File Operation Built-in Commands - ls, cat, touch, rm, mkdir, cp, mv, find, recent.
Provides native, high-performance implementations of fundamental filesystem tasks.
"""

from __future__ import annotations

import os
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List

from shell.builtins.base import BaseBuiltin
from shell.builtins.registry import register_builtin

if TYPE_CHECKING:
    from shell.core.context import ShellContext


@register_builtin
class LsBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "ls"

    @property
    def description(self) -> str:
        return "List directory contents with optional detail flags (-a, -l)."

    @property
    def usage(self) -> str:
        return "ls [-a] [-l] [path...]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        show_all = False
        long_format = False
        paths: List[str] = []

        for arg in args:
            if arg == "-a":
                show_all = True
            elif arg == "-l":
                long_format = True
            elif arg == "-la" or arg == "-al":
                show_all = True
                long_format = True
            elif not arg.startswith("-"):
                paths.append(arg)

        target_dirs = paths if paths else ["."]

        for target in target_dirs:
            resolved = (context.cwd / target).resolve()
            if not resolved.exists():
                self.write_err(context, f"ls: cannot access '{target}': No such file or directory\n")
                return 1

            if resolved.is_file():
                self.write(context, f"{resolved.name}\n")
                continue

            try:
                entries = sorted(os.listdir(resolved))
                if not show_all:
                    entries = [e for e in entries if not e.startswith(".")]

                if len(target_dirs) > 1:
                    self.write(context, f"{target}:\n")

                if long_format:
                    for item in entries:
                        item_path = resolved / item
                        try:
                            st = item_path.stat()
                            mode = stat.filemode(st.st_mode)
                            size = st.st_size
                            mtime = datetime.fromtimestamp(st.st_mtime).strftime("%b %d %H:%M")
                            self.write(context, f"{mode} {size:>8} {mtime} {item}\n")
                        except OSError:
                            self.write(context, f"{item}\n")
                else:
                    output = "  ".join(entries)
                    if output:
                        self.write(context, f"{output}\n")

                if len(target_dirs) > 1:
                    self.write(context, "\n")
            except Exception as e:
                self.write_err(context, f"ls: {e}\n")
                return 1

        return 0


@register_builtin
class CatBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "cat"

    @property
    def aliases(self) -> List[str]:
        return ["view"]

    @property
    def description(self) -> str:
        return "Concatenate and display file contents."

    @property
    def usage(self) -> str:
        return "cat <file...>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            # Read from stdin
            content = context.stdin.read()
            self.write(context, content)
            return 0

        exit_code = 0
        for filename in args:
            resolved = (context.cwd / filename).resolve()
            if not resolved.exists():
                self.write_err(context, f"cat: {filename}: No such file or directory\n")
                exit_code = 1
                continue
            if resolved.is_dir():
                self.write_err(context, f"cat: {filename}: Is a directory\n")
                exit_code = 1
                continue

            try:
                with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                    self.write(context, f.read())
            except Exception as e:
                self.write_err(context, f"cat: {filename}: {e}\n")
                exit_code = 1

        return exit_code


@register_builtin
class TouchBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "touch"

    @property
    def aliases(self) -> List[str]:
        return ["create"]

    @property
    def description(self) -> str:
        return "Update file timestamps or create empty files."

    @property
    def usage(self) -> str:
        return "touch <file...>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "touch: missing file operand\n")
            return 1

        exit_code = 0
        for filename in args:
            resolved = (context.cwd / filename).resolve()
            try:
                resolved.touch(exist_ok=True)
            except Exception as e:
                self.write_err(context, f"touch: cannot touch '{filename}': {e}\n")
                exit_code = 1

        return exit_code


@register_builtin
class MkdirBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "mkdir"

    @property
    def description(self) -> str:
        return "Create directories."

    @property
    def usage(self) -> str:
        return "mkdir [-p] <directory...>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "mkdir: missing operand\n")
            return 1

        parents = "-p" in args
        dirs = [a for a in args if a != "-p"]

        exit_code = 0
        for d in dirs:
            resolved = (context.cwd / d).resolve()
            try:
                resolved.mkdir(parents=parents, exist_ok=parents)
            except FileExistsError:
                self.write_err(context, f"mkdir: cannot create directory '{d}': File exists\n")
                exit_code = 1
            except Exception as e:
                self.write_err(context, f"mkdir: {e}\n")
                exit_code = 1

        return exit_code


@register_builtin
class RmBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "rm"

    @property
    def description(self) -> str:
        return "Remove files or directories."

    @property
    def usage(self) -> str:
        return "rm [-r] [-f] <file/dir...>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "rm: missing operand\n")
            return 1

        recursive = "-r" in args or "-rf" in args
        force = "-f" in args or "-rf" in args
        targets = [a for a in args if not a.startswith("-")]

        exit_code = 0
        for t in targets:
            resolved = (context.cwd / t).resolve()
            if not resolved.exists():
                if not force:
                    self.write_err(context, f"rm: cannot remove '{t}': No such file or directory\n")
                    exit_code = 1
                continue

            try:
                if resolved.is_dir():
                    if recursive:
                        shutil.rmtree(resolved)
                    else:
                        self.write_err(context, f"rm: cannot remove '{t}': Is a directory\n")
                        exit_code = 1
                else:
                    resolved.unlink()
            except Exception as e:
                self.write_err(context, f"rm: cannot remove '{t}': {e}\n")
                exit_code = 1

        return exit_code


@register_builtin
class CpBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "cp"

    @property
    def description(self) -> str:
        return "Copy files and directories."

    @property
    def usage(self) -> str:
        return "cp [-r] <source> <destination>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        recursive = "-r" in args
        targets = [a for a in args if a != "-r"]

        if len(targets) < 2:
            self.write_err(context, "cp: missing destination file operand after source\n")
            return 1

        src = (context.cwd / targets[0]).resolve()
        dest = (context.cwd / targets[1]).resolve()

        if not src.exists():
            self.write_err(context, f"cp: cannot stat '{targets[0]}': No such file or directory\n")
            return 1

        try:
            if src.is_dir():
                if not recursive:
                    self.write_err(context, f"cp: -r not specified; omitting directory '{targets[0]}'\n")
                    return 1
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)
            return 0
        except Exception as e:
            self.write_err(context, f"cp: {e}\n")
            return 1


@register_builtin
class MvBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "mv"

    @property
    def description(self) -> str:
        return "Move (rename) files and directories."

    @property
    def usage(self) -> str:
        return "mv <source> <destination>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if len(args) < 2:
            self.write_err(context, "mv: missing destination file operand\n")
            return 1

        src = (context.cwd / args[0]).resolve()
        dest = (context.cwd / args[1]).resolve()

        if not src.exists():
            self.write_err(context, f"mv: cannot stat '{args[0]}': No such file or directory\n")
            return 1

        try:
            shutil.move(str(src), str(dest))
            return 0
        except Exception as e:
            self.write_err(context, f"mv: {e}\n")
            return 1


@register_builtin
class FindBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "find"

    @property
    def description(self) -> str:
        return "Search for files recursively in a directory tree."

    @property
    def usage(self) -> str:
        return "find [path] <name_pattern>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "find: missing search pattern\n")
            return 1

        if len(args) == 1:
            search_dir = context.cwd
            pattern = args[0]
        else:
            search_dir = (context.cwd / args[0]).resolve()
            pattern = args[1]

        found_count = 0
        for root, dirs, files in os.walk(search_dir):
            for name in files + dirs:
                if pattern in name:
                    rel_path = os.path.relpath(os.path.join(root, name), context.cwd)
                    self.write(context, f"{rel_path}\n")
                    found_count += 1

        if found_count == 0:
            self.write(context, f"find: '{pattern}': no matches found\n")
        return 0


@register_builtin
class RecentBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "recent"

    @property
    def description(self) -> str:
        return "Show the N most recently modified files in the current directory."

    @property
    def usage(self) -> str:
        return "recent [N=5]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        n = 5
        if args:
            try:
                n = int(args[0])
            except ValueError:
                self.write_err(context, "recent: argument must be an integer count\n")
                return 1

        try:
            files = []
            for item in context.cwd.iterdir():
                if item.is_file():
                    try:
                        files.append((item.name, item.stat().st_mtime))
                    except OSError:
                        pass

            files.sort(key=lambda x: x[1], reverse=True)

            self.write(context, f"\n{min(n, len(files))} Most Recently Modified Files:\n")
            for i, (name, mtime) in enumerate(files[:n], 1):
                date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                self.write(context, f"  {i}. {name:<25} (Modified: {date_str})\n")
            self.write(context, "\n")
            return 0
        except Exception as e:
            self.write_err(context, f"recent: {e}\n")
            return 1
