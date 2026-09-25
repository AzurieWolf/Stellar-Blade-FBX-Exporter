# SPDX-FileCopyrightText: 2026 Stellar Blade FBX Fix Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later

from pathlib import Path
import ctypes
from ctypes import wintypes
import sys
import json


class ParentProcess:
    """Keep a handle to the launching Blender instance, even if its PID is reused."""

    def __init__(self, pid):
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        # SYNCHRONIZE only: no access to Blender's memory or ability to stop it.
        self.handle = self.kernel32.OpenProcess(0x00100000, False, pid)

    def is_alive(self):
        return bool(self.handle) and self.kernel32.WaitForSingleObject(self.handle, 0) == 0x102

    def close(self):
        if self.handle:
            self.kernel32.CloseHandle(self.handle)
            self.handle = None


def show_in_taskbar(window):
    if sys.platform != "win32":
        return
    # Tk's override-redirect windows normally use WS_EX_TOOLWINDOW. Explicitly
    # request a taskbar button on the native wrapper before mapping it again.
    window.update_idletasks()
    window.withdraw()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.SetWindowPos.restype = wintypes.BOOL
    hwnd = user32.GetAncestor(window.winfo_id(), 2)  # GA_ROOT: Tk's native wrapper.
    if not hwnd:
        raise ctypes.WinError(ctypes.get_last_error())
    styles = user32.GetWindowLongPtrW(hwnd, -20)
    ctypes.set_last_error(0)
    previous = user32.SetWindowLongPtrW(hwnd, -20, (styles & ~0x80) | 0x40000)
    if not previous and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0037)
    window.deiconify()


def run_window(log_path, title, parent=None, control_path=None):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.withdraw()
    assets = Path(__file__).resolve().parent
    root.iconbitmap(default=str(assets / "logwin.ico"))
    title_icon = tk.PhotoImage(master=root, file=str(assets / "logwin.png"))
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
        if state["closed"]:
            return
        window = state["window"]
        state["closed"] = True
        state["window"] = None
        state["text"] = None
        if window is not None:
            window.destroy()
        root.destroy()

    def open_window(title):
        if state["window"] is not None:
            state["window"].destroy()

        window = tk.Toplevel(root)
        window.title(title)
        window.iconbitmap(str(assets / "logwin.ico"))
        window.overrideredirect(True)
        window.configure(background="#484848")
        x = max(0, (window.winfo_screenwidth() - 900) // 2)
        y = max(0, (window.winfo_screenheight() - 520) // 2)
        window.geometry(f"900x520+{x}+{y}")
        window.protocol("WM_DELETE_WINDOW", close_window)
        window.bind("<Alt-F4>", lambda event: close_window())

        surface = tk.Frame(window, background=background)
        surface.pack(fill="both", expand=True, padx=1, pady=1)
        titlebar = tk.Label(surface, text=title, image=title_icon, compound="left",
                            anchor="w", padx=4, pady=9,
                            background=background, foreground=foreground,
                            font=("Segoe UI", 10))
        titlebar.pack(fill="x", padx=8)
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

        copy_reset = None

        def reset_copy_label():
            nonlocal copy_reset
            copy_reset = None
            if copy_button.winfo_exists():
                copy_button.configure(text="Copy Log")

        def copy_log():
            nonlocal copy_reset
            refresh_log()
            root.clipboard_clear()
            root.clipboard_append(text.get("1.0", "end-1c"))
            copy_button.configure(text="Copied")
            if copy_reset is not None:
                root.after_cancel(copy_reset)
            copy_reset = root.after(2000, reset_copy_label)

        copy_button = tk.Button(button_row, text="Copy Log", command=copy_log, width=12,
                                background="#545454", foreground=foreground,
                                activebackground="#646464", activeforeground="#ffffff",
                                relief="flat", borderwidth=0, highlightthickness=0,
                                font=("Segoe UI", 10), pady=3)
        copy_button.pack(side="right", padx=(0, 8))

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

        def reset_log(new_title):
            nonlocal copy_reset
            if copy_reset is not None:
                root.after_cancel(copy_reset)
                copy_reset = None
            copy_button.configure(text="Copy Log")
            window.title(new_title)
            titlebar.configure(text=new_title)
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.configure(state="disabled")
            # Restore a minimized window without replacing it or its geometry.
            if sys.platform == "win32":
                user32 = ctypes.WinDLL("user32")
                user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
                user32.GetAncestor.restype = wintypes.HWND
                user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
                user32.SetForegroundWindow.argtypes = [wintypes.HWND]
                user32.SetForegroundWindow.restype = wintypes.BOOL
                hwnd = user32.GetAncestor(window.winfo_id(), 2)
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
            window.lift()
            window.focus_force()

        state["reset_log"] = reset_log
        state["window"] = window
        state["text"] = text
        state["closed"] = False

        show_in_taskbar(window)
        window.lift()
        window.focus_force()
        window.update_idletasks()

    previous_text = ""

    def refresh_log():
        nonlocal previous_text, log_path
        if control_path is not None:
            try:
                request = json.loads(control_path.read_text(encoding="utf-8"))
                next_path = Path(request["log_path"])
                next_title = request["title"]
            except (OSError, ValueError, KeyError, TypeError):
                return
            if next_path != log_path:
                log_path = next_path
                previous_text = ""
                state["reset_log"](next_title)
        try:
            content = log_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            # The exporter may be between writes; retry on the next tick.
            return
        if content == previous_text:
            return
        text = state["text"]
        if text is None:
            return
        follow_end = text.yview()[1] >= 0.999
        text.configure(state="normal")
        if content.startswith(previous_text):
            text.insert("end", content[len(previous_text):])
        else:
            text.delete("1.0", "end")
            text.insert("end", content)
        previous_text = content
        if follow_end:
            text.see("end")
        text.configure(state="disabled")

    def poll():
        if parent is not None and not parent.is_alive():
            close_window()
            return
        refresh_log()
        root.after(100, poll)

    open_window(title)
    root.after(0, poll)
    root.mainloop()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stellar Blade FBX export log viewer")
    parser.add_argument("--log-path", type=Path, required=True)
    parser.add_argument("--title", default="Stellar Blade FBX Export Log")
    parser.add_argument("--parent-pid", type=int, help="Close when this Blender process exits")
    parser.add_argument("--control-path", type=Path, help="Requests to reuse this log window")
    args = parser.parse_args()
    parent = ParentProcess(args.parent_pid) if args.parent_pid is not None else None
    try:
        if parent is None or parent.is_alive():
            run_window(args.log_path, args.title, parent, args.control_path)
    finally:
        if parent is not None:
            parent.close()


if __name__ == "__main__":
    main()
