"""
BaseBuiltin Interface - Abstract class for all native shell built-in commands.
Follows the Open-Closed Principle and Strategy Pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from shell.core.context import ShellContext


class BaseBuiltin(ABC):
    """
    Abstract interface for shell built-in commands.
    
    Every built-in encapsulates its own logic, argument validation, and help text.
    New commands can be added seamlessly by extending this class and registering it,
    without altering the core execution engine.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The primary command name (e.g. 'cd', 'export')."""
        pass

    @property
    def aliases(self) -> List[str]:
        """Alternative invocation names for this builtin (e.g. ['quit'] for 'exit')."""
        return []

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description of the command."""
        pass

    @property
    def usage(self) -> str:
        """Usage syntax pattern."""
        return f"{self.name} [args...]"

    @abstractmethod
    def execute(self, args: List[str], context: ShellContext) -> int:
        """
        Execute the built-in command within the given shell context.
        
        Args:
            args: Command arguments excluding the command name itself.
            context: The shared ShellContext object.
            
        Returns:
            Exit code integer (0 for success, non-zero on failure).
        """
        pass

    def write(self, context: ShellContext, message: str) -> None:
        """Convenience method to write message to context's stdout."""
        try:
            context.stdout.write(message)
            context.stdout.flush()
        except OSError:
            pass

    def write_err(self, context: ShellContext, message: str) -> None:
        """Convenience method to write error message to context's stderr."""
        try:
            context.stderr.write(message)
            context.stderr.flush()
        except OSError:
            pass
