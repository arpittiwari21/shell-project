"""
Dynamic Shell Prompt Generator - user@host:path$ with ANSI color styling and git branch detection.
"""

from __future__ import annotations

import getpass
import os
import socket
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from shell.core.context import ShellContext


class PromptGenerator:
    """
    Renders an informative, colorized shell prompt.
    """

    # ANSI Colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"

    def __init__(self, use_color: bool = True) -> None:
        self.use_color = use_color
        try:
            self.user = getpass.getuser()
        except Exception:
            self.user = os.environ.get("USER", os.environ.get("USERNAME", "user"))

        try:
            self.host = socket.gethostname().split(".")[0]
        except Exception:
            self.host = "localhost"

    def render(self, context: ShellContext) -> str:
        """Generate the prompt string based on context state."""
        # Calculate pretty working directory (replace home with ~)
        try:
            home = str(Path.home())
            cwd_str = str(context.cwd)
            if cwd_str.startswith(home):
                display_path = "~" + cwd_str[len(home):]
            else:
                display_path = cwd_str
        except Exception:
            display_path = str(context.cwd)

        # Check for git branch
        git_branch = self._get_git_branch(context.cwd)
        git_part = f" ({git_branch})" if git_branch else ""

        # Last status indicator
        status_part = ""
        if context.last_exit_code != 0:
            status_part = f" [{context.last_exit_code}]"

        is_root = (getattr(os, "geteuid", lambda: -1)() == 0)
        symbol = "#" if is_root else "$"

        if not self.use_color:
            return f"{self.user}@{self.host}:{display_path}{git_part}{status_part}{symbol} "

        # Styled ANSI prompt
        user_host = f"{self.BOLD}{self.GREEN}{self.user}@{self.host}{self.RESET}"
        path = f"{self.BOLD}{self.BLUE}{display_path}{self.RESET}"
        branch_styled = f"{self.YELLOW}{git_part}{self.RESET}" if git_part else ""
        err_styled = f"{self.RED}{status_part}{self.RESET}" if status_part else ""
        sym_styled = f"{self.BOLD}{self.CYAN}{symbol}{self.RESET}"

        return f"{user_host}:{path}{branch_styled}{err_styled}{sym_styled} "

    def _get_git_branch(self, cwd: Path) -> Optional[str]:
        """Inspect directory hierarchy for .git/HEAD to extract active branch."""
        curr = cwd
        while True:
            git_head = curr / ".git" / "HEAD"
            if git_head.exists():
                try:
                    content = git_head.read_text(encoding="utf-8", errors="ignore").strip()
                    if content.startswith("ref: refs/heads/"):
                        return content[16:]
                    return content[:7]
                except OSError:
                    return None
            parent = curr.parent
            if parent == curr:
                break
            curr = parent
        return None
