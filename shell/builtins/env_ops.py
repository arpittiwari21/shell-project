"""
Environment and Variable Built-ins - export, set, unset, env, alias, aliases, unalias, echo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from shell.builtins.base import BaseBuiltin
from shell.builtins.registry import register_builtin

if TYPE_CHECKING:
    from shell.core.context import ShellContext


@register_builtin
class ExportBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "export"

    @property
    def description(self) -> str:
        return "Set export attribute for shell variables and update environment."

    @property
    def usage(self) -> str:
        return "export [NAME[=VALUE]...]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            for k in sorted(context.env.keys()):
                self.write(context, f"export {k}=\"{context.env[k]}\"\n")
            return 0

        for item in args:
            if "=" in item:
                k, _, v = item.partition("=")
                context.set_env(k.strip(), v.strip(), export=True)
            else:
                existing = context.get_env(item)
                if existing is not None:
                    context.set_env(item, existing, export=True)
        return 0


@register_builtin
class SetBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "set"

    @property
    def description(self) -> str:
        return "Set or display shell variables."

    @property
    def usage(self) -> str:
        return "set [NAME=VALUE...]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            # Display all shell and environment variables
            all_vars = {**context.shell_vars, **context.env}
            for k in sorted(all_vars.keys()):
                self.write(context, f"{k}={all_vars[k]}\n")
            return 0

        for item in args:
            if "=" in item:
                k, _, v = item.partition("=")
                context.set_env(k.strip(), v.strip(), export=False)
        return 0


@register_builtin
class UnsetBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "unset"

    @property
    def description(self) -> str:
        return "Unset values and attributes of environment or shell variables."

    @property
    def usage(self) -> str:
        return "unset <NAME...>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "unset: not enough arguments\n")
            return 1

        for name in args:
            context.unset_env(name)
        return 0


@register_builtin
class EnvBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "env"

    @property
    def description(self) -> str:
        return "Print all exported environment variables."

    @property
    def usage(self) -> str:
        return "env"

    def execute(self, args: List[str], context: ShellContext) -> int:
        for k in sorted(context.env.keys()):
            self.write(context, f"{k}={context.env[k]}\n")
        return 0


@register_builtin
class AliasBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "alias"

    @property
    def description(self) -> str:
        return "Define or display aliases."

    @property
    def usage(self) -> str:
        return "alias [name[='command']...]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            if not context.aliases:
                self.write(context, "No aliases defined.\n")
                return 0
            for k in sorted(context.aliases.keys()):
                self.write(context, f"alias {k}='{context.aliases[k]}'\n")
            return 0

        for item in args:
            if "=" in item:
                name, _, val = item.partition("=")
                name = name.strip()
                val = val.strip().strip("'\"")
                context.set_alias(name, val)
                self.write(context, f"Alias set: {name} -> '{val}'\n")
            else:
                val = context.get_alias(item)
                if val:
                    self.write(context, f"alias {item}='{val}'\n")
                else:
                    self.write_err(context, f"alias: {item}: not found\n")
        return 0


@register_builtin
class AliasesBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "aliases"

    @property
    def description(self) -> str:
        return "List all defined aliases."

    @property
    def usage(self) -> str:
        return "aliases"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not context.aliases:
            self.write(context, "No aliases set.\n")
            return 0

        self.write(context, "\nSaved Aliases:\n")
        for name in sorted(context.aliases.keys()):
            self.write(context, f"  {name:<15} -> {context.aliases[name]}\n")
        self.write(context, "\n")
        return 0


@register_builtin
class UnaliasBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "unalias"

    @property
    def description(self) -> str:
        return "Remove alias definition."

    @property
    def usage(self) -> str:
        return "unalias <name...>"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "unalias: usage: unalias <name...>\n")
            return 1

        exit_code = 0
        for name in args:
            if not context.remove_alias(name):
                self.write_err(context, f"unalias: {name}: not found\n")
                exit_code = 1
        return exit_code


@register_builtin
class EchoBuiltin(BaseBuiltin):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Write arguments to standard output."

    @property
    def usage(self) -> str:
        return "echo [-n] [-e] [arg...]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        newline = True
        escapes = False
        tokens: List[str] = []

        for arg in args:
            if arg == "-n":
                newline = False
            elif arg == "-e":
                escapes = True
            else:
                tokens.append(arg)

        output = " ".join(tokens)
        if escapes:
            output = output.encode().decode("unicode_escape", errors="replace")

        if newline:
            output += "\n"

        self.write(context, output)
        return 0
