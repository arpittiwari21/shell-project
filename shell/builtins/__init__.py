"""
Built-in Commands Package - Native shell command registry and implementations.
"""

from shell.builtins.base import BaseBuiltin
from shell.builtins.registry import BuiltinRegistry, register_builtin, registry, load_builtins

# Trigger loading of all builtins on import
load_builtins()

__all__ = [
    "BaseBuiltin",
    "BuiltinRegistry",
    "register_builtin",
    "registry",
    "load_builtins",
]
