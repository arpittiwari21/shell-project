"""
Command Lexer and Parser - Lexical analysis, argument parsing, quote preservation,
variable expansion, pipeline identification, and I/O redirection extraction.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from shell.core.context import ShellContext


@dataclass
class Redirection:
    """Represents a file descriptor redirection."""
    source_fd: int         # 0: stdin, 1: stdout, 2: stderr, -1: both 1 and 2
    target: str            # File path or descriptor number if is_fd_dup
    mode: str              # 'r', 'w', 'a'
    is_fd_dup: bool = False
    dup_target_fd: int = -1


@dataclass
class CommandNode:
    """Represents a single executable command with its arguments and redirections."""
    args: List[str] = field(default_factory=list)
    redirections: List[Redirection] = field(default_factory=list)
    is_background: bool = False

    @property
    def command_name(self) -> str:
        return self.args[0] if self.args else ""


@dataclass
class PipelineNode:
    """Represents one or more commands chained together via pipes (|)."""
    commands: List[CommandNode] = field(default_factory=list)
    is_background: bool = False


@dataclass
class ParsedStatement:
    """Represents a pipeline accompanied by its conditional operator (;, &&, ||)."""
    pipeline: PipelineNode
    operator: str = ";"  # ';', '&&', '||'


@dataclass
class RawToken:
    """Represents a token along with its quoting characteristics."""
    value: str
    is_single_quoted: bool = False


class CommandParser:
    """
    Parses raw shell input lines into an abstract syntax tree of statements,
    pipelines, and redirected command nodes.
    """

    def __init__(self, context: Optional[ShellContext] = None) -> None:
        self.context = context

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def parse(self, input_line: str, context: Optional[ShellContext] = None) -> List[ParsedStatement]:
        """
        Parse raw line into a list of conditional statements.
        Handles comments, alias expansion, quotes, variables, pipes, and redirects.
        """
        ctx = context or self.context
        raw = input_line.strip()
        if not raw or raw.startswith("#"):
            return []

        # Alias expansion on first token if context provided
        expanded_line = self._expand_alias(raw, ctx)

        # Tokenize preserving quoted substrings
        tokens = self._tokenize(expanded_line, ctx)
        if not tokens:
            return []

        # Split into statements separated by ';', '&&', '||'
        statement_chunks = self._split_statements(tokens)

        statements: List[ParsedStatement] = []
        for op, chunk in statement_chunks:
            pipeline = self._parse_pipeline(chunk, ctx)
            if pipeline.commands:
                statements.append(ParsedStatement(pipeline=pipeline, operator=op))

        return statements

    # -------------------------------------------------------------------------
    # Alias & Variable Expansion
    # -------------------------------------------------------------------------

    def _expand_alias(self, line: str, ctx: Optional[ShellContext]) -> str:
        """Expand alias if the first word matches an alias in context."""
        if not ctx or not ctx.aliases:
            return line

        parts = line.split(maxsplit=1)
        first_word = parts[0]
        if first_word in ctx.aliases:
            replacement = ctx.aliases[first_word]
            remainder = f" {parts[1]}" if len(parts) > 1 else ""
            return replacement + remainder
        return line

    def expand_variables(self, text: str, ctx: Optional[ShellContext]) -> str:
        """
        Expands environment variables ($VAR, ${VAR}), exit code ($?),
        and tilde (~/path) within unquoted or double-quoted tokens.
        """
        if not ctx and not os.environ:
            return text

        # Expand ~ at start of string or preceded by space
        if text == "~" or text.startswith("~/") or text.startswith("~\\"):
            home = os.path.expanduser("~")
            text = home + text[1:]

        # Expand $? (last exit code)
        exit_code = str(ctx.last_exit_code if ctx else 0)
        text = text.replace("$?", exit_code)

        # Expand ${VAR}
        def replace_braced(match: re.Match) -> str:
            var_name = match.group(1)
            if ctx:
                val = ctx.get_env(var_name)
                return val if val is not None else ""
            return os.environ.get(var_name, "")

        text = re.sub(r"\$\{([A-Za-z0-9_]+)\}", replace_braced, text)

        # Expand $VAR
        def replace_simple(match: re.Match) -> str:
            var_name = match.group(1)
            if ctx:
                val = ctx.get_env(var_name)
                return val if val is not None else ""
            return os.environ.get(var_name, "")

        text = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", replace_simple, text)

        return text

    # -------------------------------------------------------------------------
    # Lexer / Tokenizer
    # -------------------------------------------------------------------------

    def _tokenize(self, line: str, ctx: Optional[ShellContext]) -> List[RawToken]:
        """
        Lexical scanner dividing line into semantic tokens:
        words, quoted strings, pipes (|), redirections (>, >>, <, 2>, etc.),
        and statement operators (;, &&, ||).
        """
        tokens: List[RawToken] = []
        i = 0
        n = len(line)

        while i < n:
            ch = line[i]

            # Skip whitespace
            if ch.isspace():
                i += 1
                continue

            # Operators
            if ch == ";" or ch == "|":
                if i + 1 < n and line[i:i+2] == "||":
                    tokens.append(RawToken("||"))
                    i += 2
                else:
                    tokens.append(RawToken(ch))
                    i += 1
                continue

            if ch == "&":
                if i + 1 < n and line[i:i+2] == "&&":
                    tokens.append(RawToken("&&"))
                    i += 2
                elif i + 1 < n and line[i:i+2] == "&>":
                    tokens.append(RawToken("&>"))
                    i += 2
                else:
                    tokens.append(RawToken("&"))
                    i += 1
                continue

            # Redirection operators: >>, >, 2>>, 2>, 2>&1, <
            if ch in "<>":
                if i + 1 < n and line[i:i+2] == ">>":
                    tokens.append(RawToken(">>"))
                    i += 2
                else:
                    tokens.append(RawToken(ch))
                    i += 1
                continue

            # Check for 2> or 2>> or 2>&1
            if ch == "2" and i + 1 < n and line[i+1] == ">":
                if i + 3 < n and line[i:i+4] == "2>&1":
                    tokens.append(RawToken("2>&1"))
                    i += 4
                elif i + 2 < n and line[i:i+3] == "2>>":
                    tokens.append(RawToken("2>>"))
                    i += 3
                else:
                    tokens.append(RawToken("2>"))
                    i += 2
                continue

            # Check for 1> or 1>>
            if ch == "1" and i + 1 < n and line[i+1] == ">":
                if i + 2 < n and line[i:i+3] == "1>>":
                    tokens.append(RawToken(">>"))
                    i += 3
                else:
                    tokens.append(RawToken(">"))
                    i += 2
                continue

            # Word / Quoted token
            current_pieces: List[str] = []
            is_pure_single_quoted = False

            # Check if token is purely enclosed in single quotes
            if ch == "'":
                end_quote = line.find("'", i + 1)
                # If closing quote exists and immediately followed by space or EOF or operator
                if end_quote != -1:
                    after_quote = end_quote + 1
                    if after_quote == n or line[after_quote].isspace() or line[after_quote] in (";", "|", "&", "<", ">"):
                        tokens.append(RawToken(line[i+1:end_quote], is_single_quoted=True))
                        i = after_quote
                        continue

            while i < n and not line[i].isspace():
                curr = line[i]

                # Stop token if an operator boundary is encountered outside quotes
                if curr in (";", "|", "&", "<", ">"):
                    break
                if curr in ("1", "2") and i + 1 < n and line[i+1] == ">":
                    break

                if curr == "'":
                    # Single quote: take literal characters until closing quote (NO variable expansion)
                    i += 1
                    while i < n and line[i] != "'":
                        current_pieces.append(line[i])
                        i += 1
                    if i < n and line[i] == "'":
                        i += 1
                elif curr == '"':
                    # Double quote: characters with variable expansion
                    i += 1
                    dq_chars = []
                    while i < n and line[i] != '"':
                        if line[i] == "\\" and i + 1 < n:
                            if line[i+1] in ('"', "\\", "$", "`"):
                                i += 1
                                dq_chars.append(line[i])
                            elif os.name == "nt":
                                dq_chars.append("\\")
                            else:
                                i += 1
                                dq_chars.append(line[i])
                        else:
                            dq_chars.append(line[i])
                        i += 1
                    if i < n and line[i] == '"':
                        i += 1
                    expanded_dq = self.expand_variables("".join(dq_chars), ctx)
                    current_pieces.append(expanded_dq)
                elif curr == "\\":
                    # Backslash escape outside quotes
                    if i + 1 < n and line[i+1] in ("'\"\\ ;|&<>$"):
                        i += 1
                        current_pieces.append(line[i])
                        i += 1
                    elif os.name == "nt":
                        current_pieces.append("\\")
                        i += 1
                    else:
                        if i + 1 < n:
                            i += 1
                            current_pieces.append(line[i])
                        i += 1
                else:
                    # Unquoted segment
                    unquoted_chars = []
                    while i < n and not line[i].isspace() and line[i] not in ("'", '"', "\\", ";", "|", "&", "<", ">"):
                        if line[i] in ("1", "2") and i + 1 < n and line[i+1] == ">":
                            break
                        unquoted_chars.append(line[i])
                        i += 1
                    expanded_uq = self.expand_variables("".join(unquoted_chars), ctx)
                    current_pieces.append(expanded_uq)

            if current_pieces:
                tokens.append(RawToken("".join(current_pieces)))

        return tokens

    # -------------------------------------------------------------------------
    # Parsing Chunks into Statements & Pipelines
    # -------------------------------------------------------------------------

    def _split_statements(self, tokens: List[RawToken]) -> List[Tuple[str, List[RawToken]]]:
        """Split token stream on ';', '&&', '||'."""
        statements: List[Tuple[str, List[RawToken]]] = []
        current: List[RawToken] = []
        prev_op = ";"

        for token in tokens:
            if not token.is_single_quoted and token.value in (";", "&&", "||"):
                if current:
                    statements.append((prev_op, current))
                    current = []
                prev_op = token.value
            else:
                current.append(token)

        if current:
            statements.append((prev_op, current))

        return statements

    def _parse_pipeline(self, tokens: List[RawToken], ctx: Optional[ShellContext]) -> PipelineNode:
        """Parse tokens separated by '|' into a PipelineNode."""
        is_background = False
        if tokens and not tokens[-1].is_single_quoted and tokens[-1].value == "&":
            is_background = True
            tokens = tokens[:-1]

        # Split by '|'
        pipe_chunks: List[List[RawToken]] = []
        current_chunk: List[RawToken] = []

        for token in tokens:
            if not token.is_single_quoted and token.value == "|":
                if current_chunk:
                    pipe_chunks.append(current_chunk)
                    current_chunk = []
            else:
                current_chunk.append(token)
        if current_chunk:
            pipe_chunks.append(current_chunk)

        commands: List[CommandNode] = []
        for chunk in pipe_chunks:
            cmd_node = self._parse_command_node(chunk, ctx)
            if is_background:
                cmd_node.is_background = True
            commands.append(cmd_node)

        return PipelineNode(commands=commands, is_background=is_background)

    def _parse_command_node(self, tokens: List[RawToken], ctx: Optional[ShellContext]) -> CommandNode:
        """Extract arguments and redirections for a single command."""
        args: List[str] = []
        redirections: List[Redirection] = []

        i = 0
        n = len(tokens)

        while i < n:
            raw_t = tokens[i]
            token = raw_t.value

            if not raw_t.is_single_quoted:
                if token == ">":
                    if i + 1 < n:
                        target = tokens[i+1].value
                        redirections.append(Redirection(source_fd=1, target=target, mode="w"))
                        i += 2
                        continue
                elif token == ">>":
                    if i + 1 < n:
                        target = tokens[i+1].value
                        redirections.append(Redirection(source_fd=1, target=target, mode="a"))
                        i += 2
                        continue
                elif token == "<":
                    if i + 1 < n:
                        target = tokens[i+1].value
                        redirections.append(Redirection(source_fd=0, target=target, mode="r"))
                        i += 2
                        continue
                elif token == "2>":
                    if i + 1 < n:
                        target = tokens[i+1].value
                        redirections.append(Redirection(source_fd=2, target=target, mode="w"))
                        i += 2
                        continue
                elif token == "2>>":
                    if i + 1 < n:
                        target = tokens[i+1].value
                        redirections.append(Redirection(source_fd=2, target=target, mode="a"))
                        i += 2
                        continue
                elif token in ("&>", ">&"):
                    if i + 1 < n:
                        target = tokens[i+1].value
                        redirections.append(Redirection(source_fd=-1, target=target, mode="w"))
                        i += 2
                        continue
                elif token == "2>&1":
                    redirections.append(Redirection(source_fd=2, target="1", mode="w", is_fd_dup=True, dup_target_fd=1))
                    i += 1
                    continue

            # Regular argument
            args.append(token)
            i += 1

        return CommandNode(args=args, redirections=redirections)
