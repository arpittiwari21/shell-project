"""
Shell Project - Main REPL Entry Point and Loop Orchestrator.
Coordinates signal trapping, lexical parsing, command execution, and interactive UI.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from shell import __author__, __version__
from shell.builtins.registry import registry
from shell.core.context import ShellContext
from shell.core.executor import CommandExecutor
from shell.core.parser import CommandParser
from shell.sys_ops.signals import SignalManager
from shell.ui.completer import ShellCompleter
from shell.ui.prompt import PromptGenerator


def display_welcome_banner(context: ShellContext) -> None:
    """Print welcoming banner honoring original shell metadata."""
    banner = f"""
===================================================================
   myOS Shell v{__version__} - High Performance Operating System Shell
   Architecture: Clean Modular Design | Author: {__author__}
   Type 'help' to inspect builtins, or execute native system tools.
===================================================================
"""
    context.stdout.write(banner)
    context.stdout.flush()


def run_repl(context: ShellContext) -> int:
    """Execute the interactive Read-Eval-Print Loop."""
    parser = CommandParser(context)
    executor = CommandExecutor(context, registry)
    prompt_gen = PromptGenerator(use_color=True)
    signal_mgr = SignalManager(context)
    signal_mgr.setup_handlers()

    completer = ShellCompleter(context, registry)
    completer.install()

    display_welcome_banner(context)

    while context.is_running:
        try:
            prompt_str = prompt_gen.render(context)
            line = input(prompt_str)
        except KeyboardInterrupt:
            # Ctrl+C pressed in interactive mode: clear line and re-prompt
            sys.stdout.write("\n")
            sys.stdout.flush()
            continue
        except EOFError:
            # Ctrl+D: exit shell
            sys.stdout.write("\nexit\n")
            sys.stdout.flush()
            break

        if not line.strip():
            continue

        # Record non-empty command in history
        context.history.add(line)

        try:
            statements = parser.parse(line, context)
            executor.execute_statements(statements)
        except Exception as e:
            context.stderr.write(f"myOS: error: {e}\n")
            context.stderr.flush()
            context.update_exit_code(1)

    signal_mgr.restore_handlers()
    return context.last_exit_code


def run_command_string(command_str: str, context: Optional[ShellContext] = None) -> int:
    """Run a command string non-interactively (e.g. python -m shell.main -c 'ls -l')."""
    ctx = context or ShellContext()
    parser = CommandParser(ctx)
    executor = CommandExecutor(ctx, registry)

    statements = parser.parse(command_str, ctx)
    return executor.execute_statements(statements)


def run_script_file(file_path: str, context: Optional[ShellContext] = None) -> int:
    """Run commands from a script file line-by-line."""
    ctx = context or ShellContext()
    parser = CommandParser(ctx)
    executor = CommandExecutor(ctx, registry)

    last_code = 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                statements = parser.parse(stripped, ctx)
                last_code = executor.execute_statements(statements)
                if not ctx.is_running:
                    break
        return last_code
    except OSError as e:
        sys.stderr.write(f"myOS: cannot open script '{file_path}': {e}\n")
        return 1


def main() -> None:
    """CLI argument entry point."""
    arg_parser = argparse.ArgumentParser(
        description="myOS Modular Unix-like Operating System Shell in Python",
        add_help=True,
    )
    arg_parser.add_argument("-c", "--command", nargs=argparse.REMAINDER, help="Execute command string and exit")
    arg_parser.add_argument("-g", "--gui", action="store_true", help="Launch Tkinter desktop graphical terminal interface")
    arg_parser.add_argument("-v", "--version", action="version", version=f"myOS Shell v{__version__}")
    arg_parser.add_argument("script", nargs="?", help="Optional shell script file to execute")

    args, unknown = arg_parser.parse_known_args()

    if args.gui:
        from shell.ui.gui import launch_gui
        launch_gui()
        sys.exit(0)

    context = ShellContext()

    if args.command:
        cmd_str = " ".join(args.command)
        code = run_command_string(cmd_str, context)
        sys.exit(code)
    elif args.script:
        code = run_script_file(args.script, context)
        sys.exit(code)
    else:
        code = run_repl(context)
        sys.exit(code)


if __name__ == "__main__":
    main()
