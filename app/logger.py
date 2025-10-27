"""Simple GUI-aware logger used across modules."""

from __future__ import annotations

import datetime
from typing import Optional


class GuiLogger:
    """Log helper that mirrors messages to a Tkinter text widget and a file."""

    def __init__(self):
        self._root = None
        self._widget = None
        self._log_file_path: Optional[str] = None

    def configure(self, root, widget):
        """Attach the Tk root and output widget."""
        self._root = root
        self._widget = widget

    def set_log_file(self, log_file_path: Optional[str]):
        """Update the log file destination."""
        self._log_file_path = log_file_path
        if log_file_path:
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                log_file.write("=== STARTING NEW SESSION ===\n")

    def log(self, message: str):
        """Write a message to the widget and, if configured, to the log file."""
        if self._widget is not None:
            self._widget.config(state="normal")
            self._widget.insert("end", message + "\n")
            self._widget.see("end")
            self._widget.config(state="disabled")
        if self._root is not None:
            self._root.update_idletasks()
        if self._log_file_path:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self._log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"[{timestamp}] {message}\n")


LOGGER = GuiLogger()
