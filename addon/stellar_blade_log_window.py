# SPDX-FileCopyrightText: 2026 Stellar Blade FBX Fix Maintainers
#
# SPDX-License-Identifier: GPL-2.0-or-later

import queue
import os
import subprocess
import tempfile
import threading
import time


_commands = queue.Queue()
_thread = None
_available = None
_log_path = None
_process = None


def start(title="Stellar Blade FBX Export Log"):
    global _thread, _available, _log_path, _process

    if _available is False:
        return False

    _log_path = os.path.join(tempfile.gettempdir(), "stellar_blade_fbx_export.log")
    try:
        with open(_log_path, "w", encoding="utf-8") as log_file:
            log_file.write("")
    except OSError as ex:
        print(f"Could not create Stellar Blade FBX export log file: {ex}")
        _available = False
        return False

    if _thread is None or not _thread.is_alive():
        try:
            import tkinter  # noqa: F401
        except Exception as ex:
            print(f"Tkinter log window unavailable, trying PowerShell fallback: {ex}")
            _process = _start_powershell_window(title, _log_path)
            _available = _process is not None
            return _available

        _thread = threading.Thread(target=_run_window, name="StellarBladeFBXLogWindow", daemon=True)
        _thread.start()
        _available = True

    _commands.put(("open", title))
    time.sleep(0.15)
    return True


def append(message=""):
    if _available:
        if _log_path:
            try:
                with open(_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(str(message) + "\n")
            except OSError:
                pass
        _commands.put(("append", str(message)))


def finish():
    append("")
    append("Export finished.")


def _start_powershell_window(title, log_path):
    script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "stellar_blade_log_window.ps1")
    if not os.path.exists(script_path):
        print(f"Could not find Stellar Blade FBX export log window script: {script_path}")
        return None

    powershell_paths = [
        "powershell.exe",
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
    ]

    last_error = None
    for powershell_path in powershell_paths:
        try:
            return subprocess.Popen(
                [
                    powershell_path,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    script_path,
                    "-LogPath",
                    log_path,
                    "-Title",
                    title,
                ],
                close_fds=True,
            )
        except Exception as ex:
            last_error = ex

    print(f"Could not open Stellar Blade FBX export log window: {last_error}")
    return None


def _run_window():
    import tkinter as tk
    from tkinter import scrolledtext

    root = tk.Tk()
    root.withdraw()

    state = {
        "window": None,
        "text": None,
        "closed": False,
    }

    def close_window():
        window = state["window"]
        state["closed"] = True
        state["window"] = None
        state["text"] = None
        if window is not None:
            window.destroy()

    def open_window(title):
        if state["window"] is not None:
            state["window"].destroy()

        window = tk.Toplevel(root)
        window.title(title)
        window.geometry("900x520")
        window.protocol("WM_DELETE_WINDOW", close_window)

        text = scrolledtext.ScrolledText(window, wrap="word", state="disabled")
        text.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        button_row = tk.Frame(window)
        button_row.pack(fill="x", padx=8, pady=(0, 8))

        close_button = tk.Button(button_row, text="Close", command=close_window, width=12)
        close_button.pack(side="right")

        state["window"] = window
        state["text"] = text
        state["closed"] = False

        window.lift()
        window.focus_force()
        window.update_idletasks()

    def append_line(message):
        text = state["text"]
        if text is None or state["closed"]:
            return

        text.configure(state="normal")
        text.insert("end", message + "\n")
        text.see("end")
        text.configure(state="disabled")

        window = state["window"]
        if window is not None:
            window.update_idletasks()

    def poll():
        while True:
            try:
                command, payload = _commands.get_nowait()
            except queue.Empty:
                break

            if command == "open":
                open_window(payload)
            elif command == "append":
                append_line(payload)

        root.after(50, poll)

    root.after(0, poll)
    root.mainloop()
