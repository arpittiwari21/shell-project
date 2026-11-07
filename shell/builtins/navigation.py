"""
Navigation Built-in Commands - cd, pwd, dirs, pushd, popd.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

from shell.builtins.base import BaseBuiltin
from shell.builtins.registry import register_builtin

if TYPE_CHECKING:
    from shell.core.context import ShellContext


@register_builtin
class CdBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "cd"

    @property
    def description(self) -> str:
        return "Change the current working directory."

    @property
    def usage(self) -> str:
        return "cd [directory | ~ | -]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        target = args[0] if args else "~"
        try:
            context.change_dir(target)
            return 0
        except (FileNotFoundError, NotADirectoryError, ValueError) as err:
            self.write_err(context, f"{err}\n")
            return 1


@register_builtin
class PwdBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "pwd"

    @property
    def description(self) -> str:
        return "Print the absolute pathname of the current working directory."

    @property
    def usage(self) -> str:
        return "pwd"

    def execute(self, args: List[str], context: ShellContext) -> int:
        self.write(context, f"{context.cwd}\n")
        return 0


@register_builtin
class DirsBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "dirs"

    @property
    def description(self) -> str:
        return "Display the list of currently remembered directories."

    @property
    def usage(self) -> str:
        return "dirs"

    def execute(self, args: List[str], context: ShellContext) -> int:
        items = " ".join(str(p) for p in reversed(context.dir_stack))
        self.write(context, f"{items}\n")
        return 0


@register_builtin
class PushdBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "pushd"

    @property
    def description(self) -> str:
        return "Push directory onto stack and change directory."

    @property
    def usage(self) -> str:
        return "pushd <directory>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "pushd: no other directory\n")
            return 1
        try:
            context.push_dir(args[0])
            dirs = " ".join(str(p) for p in reversed(context.dir_stack))
            self.write(context, f"{dirs}\n")
            return 0
        except Exception as e:
            self.write_err(context, f"pushd: {e}\n")
            return 1


@register_builtin
class PopdBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "popd"

    @property
    def description(self) -> str:
        return "Pop the top directory off the stack and change to it."

    @property
    def usage(self) -> str:
        return "popd"

    def execute(self, args: List[str], context: ShellContext) -> int:
        try:
            new_dir = context.pop_dir()
            dirs = " ".join(str(p) for p in reversed(context.dir_stack))
            self.write(context, f"{dirs}\n")
            return 0
        except IndexError as err:
            self.write_err(context, f"{err}\n")
            return 1
        except Exception as e:
            self.write_err(context, f"popd: {e}\n")
            return 1
