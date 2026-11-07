"""
Command History Management - Handles in-memory recall and persistent disk storage.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional


class HistoryManager:
    """
    Manages interactive shell history with bounded memory and optional disk persistence.
    """

    def __init__(
        self,
        history_file: Optional[str] = None,
        max_entries: int = 1000,
    ) -> None:
        self.max_entries: int = max_entries
        self.history: List[str] = []
        self._cursor: int = 0

        if history_file:
            self.history_file: Optional[Path] = Path(history_file).expanduser().resolve()
        else:
            self.history_file = Path.home() / ".shell_project_history"

        self.load()

    def add(self, command: str) -> None:
        """Add a command line to history if non-empty and not duplicate of previous."""
        cmd = command.strip()
        if not cmd:
            return

        # Avoid duplicate consecutive entries
        if not self.history or self.history[-1] != cmd:
            self.history.append(cmd)
            if len(self.history) > self.max_entries:
                self.history.pop(0)

        self._cursor = len(self.history)
        self.save()

    def get_all(self) -> List[str]:
        """Return all recorded command entries."""
        return list(self.history)

    def get(self, index: int) -> Optional[str]:
        """Get 1-based or 0-based entry."""
        if 0 <= index < len(self.history):
            return self.history[index]
        return None

    def search(self, prefix: str) -> List[str]:
        """Search commands matching prefix."""
        return [cmd for cmd in self.history if cmd.startswith(prefix)]

    def clear(self) -> None:
        """Clear all history in memory and truncate history file."""
        self.history.clear()
        self._cursor = 0
        if self.history_file and self.history_file.exists():
            try:
                self.history_file.write_text("", encoding="utf-8")
            except OSError:
                pass

    def load(self) -> None:
        """Load history lines from disk."""
        if not self.history_file or not self.history_file.exists():
            return
        try:
            with open(self.history_file, "r", encoding="utf-8", errors="replace") as f:
                lines = [line.strip() for line in f if line.strip()]
                self.history = lines[-self.max_entries:]
                self._cursor = len(self.history)
        except OSError:
            pass

    def save(self) -> None:
        """Save history lines to disk."""
        if not self.history_file:
            return
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                for line in self.history:
                    f.write(f"{line}\n")
        except OSError:
            pass

    def __len__(self) -> int:
        return len(self.history)
