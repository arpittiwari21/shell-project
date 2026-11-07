"""
Tab Completion - Autocompletion for builtin commands, binaries in PATH, and filesystem paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from shell.builtins.registry import BuiltinRegistry
    from shell.core.context import ShellContext


class ShellCompleter:
    """
    Readline-compatible autocompleter for command names and filesystem paths.
    """

    def __init__(
        self,
        context: ShellContext,
        registry: BuiltinRegistry,
    ) -> None:
        self.context = context
        self.registry = registry
        self._matches: List[str] = []

    def complete(self, text: str, state: int) -> Optional[str]:
        """
        Readline completer callback.
        Returns the state-th completion candidate for text, or None when exhausted.
        """
        if state == 0:
            self._matches = self._calculate_matches(text)

        if state < len(self._matches):
            return self._matches[state]
        return None

    def _calculate_matches(self, text: str) -> List[str]:
        """Find matching command names or filesystem paths."""
        try:
            import readline
            line_buffer = readline.get_line_buffer()
        except ImportError:
            line_buffer = text

        tokens = line_buffer.lstrip().split()
        is_first_word = len(tokens) <= 1 and not line_buffer.endswith(" ")

        if is_first_word:
            # Complete commands (builtins + PATH executables)
            matches = set()
            # 1. Built-in command names
            for name in self.registry.get_names():
                if name.startswith(text):
                    matches.add(name)

            # 2. PATH binaries
            path_dirs = self.context.env.get("PATH", "").split(os.pathsep)
            for d in path_dirs:
                if os.path.isdir(d):
                    try:
                        for entry in os.listdir(d):
                            if entry.startswith(text):
                                matches.add(entry)
                    except OSError:
                        pass

            return sorted(matches)

        else:
            # Complete filesystem paths
            return self._complete_paths(text)

    def _complete_paths(self, text: str) -> List[str]:
        """Complete file or directory paths."""
        results: List[str] = []

        raw_path = os.path.expanduser(text)
        if not text:
            search_dir = self.context.cwd
            prefix = ""
            base_dir_str = ""
        elif "/" in text or "\\" in text:
            # Split dirname and basename
            split_char = "/" if "/" in text else "\\"
            parts = text.rsplit(split_char, 1)
            base_dir_str = parts[0] + split_char
            prefix = parts[1]
            search_dir = (self.context.cwd / os.path.expanduser(parts[0])).resolve()
        else:
            search_dir = self.context.cwd
            prefix = text
            base_dir_str = ""

        if not search_dir.is_dir():
            return []

        try:
            for item in sorted(os.listdir(search_dir)):
                if item.startswith(prefix):
                    full_item = search_dir / item
                    suffix = "/" if full_item.is_dir() else ""
                    results.append(f"{base_dir_str}{item}{suffix}")
        except OSError:
            pass

        return results

    def install(self) -> bool:
        """Attempt to register completer with readline."""
        try:
            try:
                import readline
            except ImportError:
                import pyreadline3 as readline  # Windows fallback

            readline.set_completer(self.complete)
            readline.parse_and_bind("tab: complete")
            return True
        except Exception:
            return False
