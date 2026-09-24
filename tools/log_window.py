# SPDX-FileCopyrightText: 2026 Stellar Blade FBX Fix Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later

from pathlib import Path


def run_window(log_path, title):
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
        root.destroy()

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

        state["window"] = window
        state["text"] = text
        state["closed"] = False

        window.lift()
        window.focus_force()
        window.update_idletasks()

    previous_text = ""

    def refresh_log():
        nonlocal previous_text
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
    args = parser.parse_args()
    run_window(args.log_path, args.title)


if __name__ == "__main__":
    main()
