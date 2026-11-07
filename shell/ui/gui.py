"""
Tkinter Desktop GUI Presentation Layer for myOS Shell.
Connects the modular ShellContext, CommandParser, and CommandExecutor to a modern graphical interface.
"""

from __future__ import annotations

import io
import os
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional

from shell import __author__, __version__
from shell.builtins.registry import registry
from shell.core.context import ShellContext
from shell.core.executor import CommandExecutor
from shell.core.parser import CommandParser
from shell.ui.completer import ShellCompleter


class QueueTextStream(io.TextIOBase):
    """
    Thread-safe stream wrapper that directs output to a Python queue
    for asynchronous, non-blocking rendering in Tkinter.
    """

    def __init__(self, out_queue: queue.Queue, tag: str = "normal") -> None:
        super().__init__()
        self.queue = out_queue
        self.tag = tag

    def write(self, s: str) -> int:
        if s:
            self.queue.put((s, self.tag))
        return len(s)

    def flush(self) -> None:
        pass


class ShellGUI:
    """
    Modern Tkinter-based terminal desktop window for myOS Shell.
    Uses One Dark color scheme, multi-threaded command execution,
    and direct integration with the modular shell core.
    """

    # Color Palette (One Dark Theme)
    BG_DARK = "#21252b"
    BG_TERMINAL = "#282c34"
    FG_TEXT = "#abb2bf"
    COLOR_BLUE = "#61afef"
    COLOR_GREEN = "#98c379"
    COLOR_RED = "#e06c75"
    COLOR_YELLOW = "#e5c07b"
    COLOR_PURPLE = "#c678dd"
    COLOR_CYAN = "#56b6c2"
    COLOR_BUTTON = "#3e4451"
    COLOR_BUTTON_ACTIVE = "#4b5263"

    ANSI_COLOR_MAP = {
        "30": "#282c34",
        "31": COLOR_RED,
        "32": COLOR_GREEN,
        "33": COLOR_YELLOW,
        "34": COLOR_BLUE,
        "35": COLOR_PURPLE,
        "36": COLOR_CYAN,
        "37": "#abb2bf",
    }

    def __init__(self, root: Optional[tk.Tk] = None) -> None:
        self.root = root or tk.Tk()
        self.root.title(f"myOS Shell v{__version__} - Graphical Terminal")
        self.root.geometry("960x640")
        self.root.minsize(700, 450)
        self.root.configure(bg=self.BG_DARK)

        # Thread-safe queue for worker-to-UI communication
        self.output_queue: queue.Queue = queue.Queue()

        # Connect modular shell runtime state
        self.stdout_stream = QueueTextStream(self.output_queue, tag="stdout")
        self.stderr_stream = QueueTextStream(self.output_queue, tag="stderr")
        self.context = ShellContext(
            stdout=self.stdout_stream,
            stderr=self.stderr_stream,
        )
        self.parser = CommandParser(self.context)
        self.executor = CommandExecutor(self.context, registry)
        self.completer = ShellCompleter(self.context, registry)

        self.history_index: int = len(self.context.history)

        self._build_ui()
        self._configure_tags()
        self._display_welcome()
        self._update_directory_label()

        # Start queue polling loop
        self.root.after(50, self._process_output_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self) -> None:
        """Construct the Tkinter layout."""
        # Top toolbar
        toolbar = tk.Frame(self.root, bg=self.BG_DARK, pady=6, padx=10)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        buttons = [
            ("Help", lambda: self.submit_command("help")),
            ("Clear", self.clear_terminal),
            ("New Program...", self._open_code_dialog),
            ("System Info", lambda: self.submit_command("system")),
            ("Disk Space", lambda: self.submit_command("disk")),
            ("Processes", lambda: self.submit_command("ps")),
            ("Recent Files", lambda: self.submit_command("recent")),
            ("Browse Directory...", self._open_file_dialog),
        ]

        for text, cmd in buttons:
            btn = tk.Button(
                toolbar,
                text=text,
                command=cmd,
                bg=self.COLOR_BUTTON,
                fg=self.FG_TEXT,
                activebackground=self.COLOR_BUTTON_ACTIVE,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                padx=10,
                pady=4,
                font=("Consolas", 9, "bold"),
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=3)

        # Directory status bar
        self.dir_frame = tk.Frame(self.root, bg=self.BG_DARK, padx=12, pady=2)
        self.dir_frame.pack(fill=tk.X, side=tk.TOP)

        self.dir_label = tk.Label(
            self.dir_frame,
            text="",
            bg=self.BG_DARK,
            fg=self.COLOR_BLUE,
            anchor="w",
            font=("Consolas", 10),
        )
        self.dir_label.pack(fill=tk.X)

        # Terminal Output area
        output_frame = tk.Frame(self.root, bg=self.BG_DARK, padx=10, pady=4)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.terminal_display = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            bg=self.BG_TERMINAL,
            fg=self.FG_TEXT,
            font=("Consolas", 11),
            insertbackground=self.FG_TEXT,
            relief=tk.FLAT,
            bd=5,
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)
        self.terminal_display.config(state=tk.DISABLED)

        # Input command frame
        input_frame = tk.Frame(self.root, bg=self.BG_DARK, padx=10, pady=8)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.prompt_label = tk.Label(
            input_frame,
            text="myOS> ",
            bg=self.BG_DARK,
            fg=self.COLOR_CYAN,
            font=("Consolas", 11, "bold"),
        )
        self.prompt_label.pack(side=tk.LEFT)

        self.cmd_entry = tk.Entry(
            input_frame,
            bg=self.BG_TERMINAL,
            fg=self.FG_TEXT,
            insertbackground=self.FG_TEXT,
            font=("Consolas", 11),
            relief=tk.FLAT,
            bd=6,
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self.cmd_entry.focus_set()

        # Keyboard shortcuts
        self.cmd_entry.bind("<Return>", self._on_enter_pressed)
        self.cmd_entry.bind("<Up>", self._on_history_up)
        self.cmd_entry.bind("<Down>", self._on_history_down)
        self.cmd_entry.bind("<Tab>", self._on_tab_complete)

    def _configure_tags(self) -> None:
        """Define styling tags for text display."""
        d = self.terminal_display
        d.tag_configure("stdout", foreground=self.FG_TEXT)
        d.tag_configure("stderr", foreground=self.COLOR_RED)
        d.tag_configure("banner", foreground=self.COLOR_BLUE, font=("Consolas", 11, "bold"))
        d.tag_configure("command_prompt", foreground=self.COLOR_CYAN, font=("Consolas", 11, "bold"))
        d.tag_configure("command_text", foreground=self.COLOR_YELLOW)
        d.tag_configure("success", foreground=self.COLOR_GREEN)

        for code, color in self.ANSI_COLOR_MAP.items():
            d.tag_configure(f"ansi_{code}", foreground=color)

    def _display_welcome(self) -> None:
        """Output welcoming banner."""
        banner_text = (
            f"===================================================================\n"
            f"  myOS Shell v{__version__} Graphical Terminal Interface\n"
            f"  Modular Architecture | Author: {__author__}\n"
            f"  Type 'help' to inspect built-in commands or run any system command.\n"
            f"===================================================================\n\n"
        )
        self._append_text(banner_text, "banner")

    def _update_directory_label(self) -> None:
        """Update working directory indicator."""
        self.dir_label.config(text=f"Current Directory: {self.context.cwd}")

    def clear_terminal(self) -> None:
        """Clear all content from the terminal display."""
        self.terminal_display.config(state=tk.NORMAL)
        self.terminal_display.delete(1.0, tk.END)
        self.terminal_display.config(state=tk.DISABLED)

    def _open_file_dialog(self) -> None:
        """Open graphical folder browser and cd to selected directory."""
        chosen = filedialog.askdirectory(initialdir=str(self.context.cwd))
        if chosen:
            self.submit_command(f'cd "{chosen}"')

    def _open_code_dialog(self) -> None:
        """Open graphical dialog to generate and execute predefined code templates."""
        from shell.builtins.code_ops import CODE_TEMPLATES

        dialog = tk.Toplevel(self.root)
        dialog.title("Code Studio - Create & Run Predefined Program")
        dialog.geometry("540x360")
        dialog.resizable(False, False)
        dialog.configure(bg=self.BG_DARK)
        dialog.transient(self.root)
        dialog.grab_set()

        title_lbl = tk.Label(
            dialog,
            text="Generate Code Template & Execute",
            bg=self.BG_DARK,
            fg=self.COLOR_CYAN,
            font=("Consolas", 12, "bold"),
            pady=10,
        )
        title_lbl.pack(fill=tk.X)

        form_frame = tk.Frame(dialog, bg=self.BG_DARK, padx=20, pady=5)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Language dropdown
        tk.Label(form_frame, text="Programming Language:", bg=self.BG_DARK, fg=self.FG_TEXT, font=("Consolas", 10)).grid(row=0, column=0, sticky="w", pady=6)
        lang_var = tk.StringVar(value="python")
        lang_combo = ttk.Combobox(
            form_frame,
            textvariable=lang_var,
            values=["python", "c", "cpp", "java", "javascript"],
            state="readonly",
            font=("Consolas", 10),
            width=28,
        )
        lang_combo.grid(row=0, column=1, sticky="w", pady=6)

        # Template dropdown
        tk.Label(form_frame, text="Predefined Program:", bg=self.BG_DARK, fg=self.FG_TEXT, font=("Consolas", 10)).grid(row=1, column=0, sticky="w", pady=6)
        tmpl_var = tk.StringVar(value="add")
        tmpl_combo = ttk.Combobox(
            form_frame,
            textvariable=tmpl_var,
            values=["add", "age", "hello"],
            state="readonly",
            font=("Consolas", 10),
            width=28,
        )
        tmpl_combo.grid(row=1, column=1, sticky="w", pady=6)

        # Target filename entry
        tk.Label(form_frame, text="Target Filename:", bg=self.BG_DARK, fg=self.FG_TEXT, font=("Consolas", 10)).grid(row=2, column=0, sticky="w", pady=6)
        file_var = tk.StringVar(value="add_numbers.py")
        file_entry = tk.Entry(
            form_frame,
            textvariable=file_var,
            bg=self.BG_TERMINAL,
            fg=self.FG_TEXT,
            insertbackground=self.FG_TEXT,
            font=("Consolas", 10),
            relief=tk.FLAT,
            bd=4,
            width=30,
        )
        file_entry.grid(row=2, column=1, sticky="w", pady=6)

        # Description / Info box
        desc_label = tk.Label(
            form_frame,
            text="Template: Function calculating the sum of two numbers.",
            bg=self.BG_TERMINAL,
            fg=self.COLOR_GREEN,
            font=("Consolas", 9),
            wraplength=480,
            justify=tk.LEFT,
            padx=8,
            pady=8,
        )
        desc_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=12)

        def on_selection_change(*args):
            l = lang_var.get()
            t = tmpl_var.get()
            if l in CODE_TEMPLATES and t in CODE_TEMPLATES[l]:
                fname, _ = CODE_TEMPLATES[l][t]
                file_var.set(fname)
                if t == "add":
                    desc_label.config(text=f"Template: {l.capitalize()} program calculating the sum of two numbers.")
                elif t == "age":
                    desc_label.config(text=f"Template: {l.capitalize()} program evaluating age validation & voting eligibility (>= 18).")
                elif t == "hello":
                    desc_label.config(text=f"Template: {l.capitalize()} starter Hello World program.")

        lang_combo.bind("<<ComboboxSelected>>", on_selection_change)
        tmpl_combo.bind("<<ComboboxSelected>>", on_selection_change)

        btn_frame = tk.Frame(dialog, bg=self.BG_DARK, pady=12)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def create_only():
            l = lang_var.get()
            t = tmpl_var.get()
            fn = file_var.get().strip() or "output.code"
            dialog.destroy()
            self.submit_command(f'template create {l} {t} "{fn}"')

        def create_and_run():
            l = lang_var.get()
            t = tmpl_var.get()
            fn = file_var.get().strip() or "output.code"
            dialog.destroy()
            self.submit_command(f'template create {l} {t} "{fn}" && runcode "{fn}"')

        create_btn = tk.Button(
            btn_frame,
            text="Create File",
            command=create_only,
            bg=self.COLOR_BUTTON,
            fg=self.FG_TEXT,
            relief=tk.FLAT,
            padx=12,
            pady=4,
            font=("Consolas", 10, "bold"),
            cursor="hand2",
        )
        create_btn.pack(side=tk.RIGHT, padx=12)

        run_btn = tk.Button(
            btn_frame,
            text="Create & Execute Now",
            command=create_and_run,
            bg=self.COLOR_BLUE,
            fg="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            font=("Consolas", 10, "bold"),
            cursor="hand2",
        )
        run_btn.pack(side=tk.RIGHT, padx=6)

    def submit_command(self, cmd_text: str) -> None:
        """Insert and run a command programmatically."""
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, cmd_text)
        self._on_enter_pressed()

    def _on_enter_pressed(self, event: Optional[tk.Event] = None) -> None:
        """Process entered command line."""
        command = self.cmd_entry.get().strip()
        if not command:
            return

        # Record in history
        self.context.history.add(command)
        self.history_index = len(self.context.history)

        # Print command echo to display
        self._append_text("myOS> ", "command_prompt")
        self._append_text(f"{command}\n", "command_text")

        self.cmd_entry.delete(0, tk.END)

        if command.lower() in ("exit", "quit"):
            self._append_text("Exiting shell...\n", "success")
            self.root.after(600, self.root.destroy)
            return

        # Execute asynchronously in background worker thread
        threading.Thread(target=self._run_command_worker, args=(command,), daemon=True).start()

    def _run_command_worker(self, command_line: str) -> None:
        """Worker thread executing the command through parser and executor."""
        try:
            statements = self.parser.parse(command_line, self.context)
            self.executor.execute_statements(statements)
        except Exception as e:
            self.output_queue.put((f"myOS: execution error: {e}\n", "stderr"))
        finally:
            # Signal queue that command execution finished
            self.output_queue.put((None, "DONE"))

    def _process_output_queue(self) -> None:
        """Polls queue on main thread to safely update Tkinter widgets."""
        while not self.output_queue.empty():
            try:
                item = self.output_queue.get_nowait()
                text, tag = item
                if tag == "DONE":
                    self._update_directory_label()
                elif text:
                    self._render_ansi_text(text, default_tag=tag)
            except queue.Empty:
                break

        # Re-schedule next check
        self.root.after(40, self._process_output_queue)

    def _render_ansi_text(self, raw_text: str, default_tag: str = "stdout") -> None:
        """Parse ANSI color escape sequences and insert with corresponding Tkinter tags."""
        ansi_regex = re.compile(r"\033\[([0-9;]+)m")
        segments = ansi_regex.split(raw_text)

        current_tag = default_tag
        for i, segment in enumerate(segments):
            if i % 2 == 1:
                # ANSI code
                codes = segment.split(";")
                for code in codes:
                    if code == "0":
                        current_tag = default_tag
                    elif code in self.ANSI_COLOR_MAP:
                        current_tag = f"ansi_{code}"
            else:
                if segment:
                    self._append_text(segment, current_tag)

    def _append_text(self, text: str, tag: str) -> None:
        """Thread-safe append text to display."""
        self.terminal_display.config(state=tk.NORMAL)
        self.terminal_display.insert(tk.END, text, tag)
        self.terminal_display.see(tk.END)
        self.terminal_display.config(state=tk.DISABLED)

    def _on_history_up(self, event: tk.Event) -> str:
        """Recall previous command in history."""
        hist = self.context.history.get_all()
        if not hist:
            return "break"
        if self.history_index > 0:
            self.history_index -= 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, hist[self.history_index])
        return "break"

    def _on_history_down(self, event: tk.Event) -> str:
        """Recall next command in history."""
        hist = self.context.history.get_all()
        if not hist:
            return "break"
        if self.history_index < len(hist) - 1:
            self.history_index += 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, hist[self.history_index])
        else:
            self.history_index = len(hist)
            self.cmd_entry.delete(0, tk.END)
        return "break"

    def _on_tab_complete(self, event: tk.Event) -> str:
        """Autocompletion on Tab key."""
        current_text = self.cmd_entry.get()
        cursor_pos = self.cmd_entry.index(tk.INSERT)
        prefix = current_text[:cursor_pos]

        matches = self.completer._calculate_matches(prefix)
        if matches:
            if len(matches) == 1:
                match = matches[0]
                self.cmd_entry.delete(0, tk.END)
                self.cmd_entry.insert(0, match + " ")
            else:
                # Show candidate completions in terminal
                self._append_text(f"\nSuggestions: {'  '.join(matches[:15])}\n", "stdout")
        return "break"

    def _on_closing(self) -> None:
        """Prompt confirmation before destroying window."""
        self.root.destroy()

    def run(self) -> None:
        """Start the Tkinter GUI main loop."""
        self.root.mainloop()


def launch_gui() -> None:
    """Convenience launcher for the GUI."""
    app = ShellGUI()
    app.run()


if __name__ == "__main__":
    launch_gui()
