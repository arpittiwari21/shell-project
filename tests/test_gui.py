"""
Unit tests for the Tkinter desktop GUI presentation layer.
"""

import queue
import tkinter as tk
import unittest

from shell.ui.gui import QueueTextStream, ShellGUI


class TestGUI(unittest.TestCase):
    def test_queue_text_stream(self):
        q = queue.Queue()
        stream = QueueTextStream(q, tag="custom_tag")
        stream.write("hello from stream\n")
        self.assertFalse(q.empty())
        text, tag = q.get_nowait()
        self.assertEqual(text, "hello from stream\n")
        self.assertEqual(tag, "custom_tag")

    def test_gui_initialization_and_teardown(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tkinter display not available in headless environment")

        try:
            app = ShellGUI(root)
            self.assertIsNotNone(app.context)
            self.assertIsNotNone(app.parser)
            self.assertIsNotNone(app.executor)
            self.assertIsNotNone(app.cmd_entry)
            self.assertIsNotNone(app.terminal_display)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
