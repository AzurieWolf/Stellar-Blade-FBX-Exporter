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
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as ex:
            last_error = ex

    print(f"Could not open Stellar Blade FBX export log window: {last_error}")
    return None


def _run_window():
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.withdraw()
    # Fixed palette matching Blender's default dark theme.
    background, field, foreground = "#303030", "#242424", "#d4d4d4"
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Log.Vertical.TScrollbar", background="#545454",
                    troughcolor=field, bordercolor=field, arrowcolor=foreground,
                    lightcolor="#545454", darkcolor="#545454")
    style.map("Log.Vertical.TScrollbar", background=[("active", "#646464")])

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
        window.overrideredirect(True)
        window.configure(background="#484848")
        x = max(0, (window.winfo_screenwidth() - 900) // 2)
        y = max(0, (window.winfo_screenheight() - 520) // 2)
        window.geometry(f"900x520+{x}+{y}")
        window.protocol("WM_DELETE_WINDOW", close_window)
        window.bind("<Alt-F4>", lambda event: close_window())

        surface = tk.Frame(window, background=background)
        surface.pack(fill="both", expand=True, padx=1, pady=1)
        titlebar = tk.Label(surface, text=title, anchor="w", padx=12, pady=9,
                            background=background, foreground=foreground,
                            font=("Segoe UI", 10))
        titlebar.pack(fill="x")
        drag = {}

        def begin_drag(event):
            drag.update(x=event.x_root - window.winfo_x(), y=event.y_root - window.winfo_y())

        def move_window(event):
            window.geometry(f"{event.x_root - drag['x']:+d}{event.y_root - drag['y']:+d}")

        titlebar.bind("<ButtonPress-1>", begin_drag)
        titlebar.bind("<B1-Motion>", move_window)

        button_row = tk.Frame(surface, background=background)
        button_row.pack(side="bottom", fill="x", padx=8, pady=8)

        grip = tk.Label(button_row, text="\u25e2", background=background,
                        foreground="#777777", cursor="size_nw_se")
        grip.pack(side="right", padx=(8, 0), anchor="s")
        resize = {}

        def begin_resize(event):
            resize.update(x=event.x_root, y=event.y_root,
                          width=window.winfo_width(), height=window.winfo_height())

        def resize_window(event):
            width = max(480, resize["width"] + event.x_root - resize["x"])
            height = max(280, resize["height"] + event.y_root - resize["y"])
            window.geometry(f"{width}x{height}")

        grip.bind("<ButtonPress-1>", begin_resize)
        grip.bind("<B1-Motion>", resize_window)
        close_button = tk.Button(button_row, text="Close", command=close_window, width=12,
                                 background="#545454", foreground=foreground,
                                 activebackground="#646464", activeforeground="#ffffff",
                                 relief="flat", borderwidth=0, highlightthickness=0,
                                 font=("Segoe UI", 10), pady=3)
        close_button.pack(side="right")

        text_frame = tk.Frame(surface, background=field)
        text_frame.pack(fill="both", expand=True, padx=8)
        text = tk.Text(text_frame, wrap="word", state="disabled", background=field,
                       foreground=foreground, insertbackground=foreground,
                       selectbackground="#4772b3", selectforeground="#ffffff",
                       relief="flat", borderwidth=0, highlightthickness=0,
                       padx=10, pady=8, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview,
                                  style="Log.Vertical.TScrollbar")
        scrollbar.pack(side="right", fill="y")
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(fill="both", expand=True)

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
