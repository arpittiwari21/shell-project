"""
Presentation layer: prompt generation and tab autocompletion.
"""

from shell.ui.prompt import PromptGenerator
from shell.ui.completer import ShellCompleter

__all__ = [
    "PromptGenerator",
    "ShellCompleter",
]
