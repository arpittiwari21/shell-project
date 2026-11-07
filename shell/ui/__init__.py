"""
Presentation layer: prompt generation and tab autocompletion.
"""

from shell.ui.prompt import PromptGenerator
from shell.ui.completer import ShellCompleter
from shell.ui.gui import ShellGUI, launch_gui

__all__ = [
    "PromptGenerator",
    "ShellCompleter",
    "ShellGUI",
    "launch_gui",
]
