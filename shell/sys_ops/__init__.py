"""
Low-level operating system operations: signal trapping, file descriptor redirections, and pipelines.
"""

from shell.sys_ops.signals import SignalManager
from shell.sys_ops.io_redirect import IORedirector
from shell.sys_ops.pipelines import PipelineRunner

__all__ = [
    "SignalManager",
    "IORedirector",
    "PipelineRunner",
]
