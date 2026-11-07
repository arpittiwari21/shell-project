"""
Builtin Registry - Central dispatch table and dynamic loader for shell built-ins.
Implements the Registry Pattern.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Dict, List, Optional, Type

from shell.builtins.base import BaseBuiltin


class BuiltinRegistry:
    """
    Registry for dynamic registration, lookup, and documentation of builtins.
    """

    def __init__(self) -> None:
        self._commands: Dict[str, BaseBuiltin] = {}

    def register(self, builtin_instance: BaseBuiltin) -> None:
        """Register a builtin command instance under its primary name and aliases."""
        self._commands[builtin_instance.name] = builtin_instance
        for alias in builtin_instance.aliases:
            self._commands[alias] = builtin_instance

    def get(self, name: str) -> Optional[BaseBuiltin]:
        """Lookup a builtin command by name or alias."""
        return self._commands.get(name)

    def has(self, name: str) -> bool:
        """Check whether a command name is a registered builtin."""
        return name in self._commands

    def list_all(self) -> Dict[str, BaseBuiltin]:
        """Return a mapping of primary command names to their instances."""
        unique: Dict[str, BaseBuiltin] = {}
        for cmd in self._commands.values():
            if cmd.name not in unique:
                unique[cmd.name] = cmd
        return unique

    def get_names(self) -> List[str]:
        """Return list of all invocable names including aliases."""
        return sorted(self._commands.keys())


# Global default registry instance
registry = BuiltinRegistry()


def register_builtin(cls: Type[BaseBuiltin]) -> Type[BaseBuiltin]:
    """Class decorator to auto-instantiate and register a builtin command."""
    instance = cls()
    registry.register(instance)
    return cls


def load_builtins() -> BuiltinRegistry:
    """
    Dynamically discover and import all builtin modules within the package.
    Ensures all decorated builtins are registered.
    """
    import shell.builtins as builtins_pkg

    for _, module_name, _ in pkgutil.iter_modules(builtins_pkg.__path__):
        if module_name not in ("base", "registry"):
            importlib.import_module(f"shell.builtins.{module_name}")

    return registry
