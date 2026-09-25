# SPDX-FileCopyrightText: 2026 Stellar Blade FBX Fix Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Blender-side log writer and launcher for the standalone log viewer."""

from pathlib import Path
import os
import json
import ctypes
from ctypes import wintypes
import subprocess
import tempfile

_log_path = None
_process = None
_control_path = None


def start(title="Stellar Blade FBX Export Log"):
    global _log_path, _process, _control_path
    _log_path = None
    addon_path = Path(__file__).resolve().parent
    executable = addon_path / "log_window" / "StellarBladeExportLog.exe"
    # Support running the add-on directly from a source checkout after building.
    if not executable.is_file() and (addon_path.parent / "tools" / "log_window.py").is_file():
        executable = addon_path.parent / "dist" / "StellarBladeExportLog" / executable.name
    if not executable.is_file():
        print("Export log viewer is missing. Run [Build Log Window].bat or install a packaged release.")
        return False
    try:
        with tempfile.NamedTemporaryFile(prefix="stellar_blade_fbx_", suffix=".log", delete=False) as log_file:
            log_path = Path(log_file.name)
        if _control_path is None:
            with tempfile.NamedTemporaryFile(prefix="stellar_blade_viewer_", suffix=".json", delete=False) as control:
                _control_path = Path(control.name)
        # Publish a fresh log as one atomic update so the viewer never reads a
        # partially written request, even while Blender is busy importing/exporting.
        pending = _control_path.with_suffix(".tmp")
        pending.write_text(json.dumps({"log_path": str(log_path), "title": title}), encoding="utf-8")
        if os.name == "nt" and _process is not None and _process.poll() is None:
            # Blender owns the foreground when the user starts the operation.
            # Grant the existing viewer permission before it reads the request.
            user32 = ctypes.WinDLL("user32")
            user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
            user32.AllowSetForegroundWindow.restype = wintypes.BOOL
            user32.AllowSetForegroundWindow(_process.pid)
        pending.replace(_control_path)
        if _process is not None and _process.poll() is None:
            _log_path = log_path
            return True
        _process = subprocess.Popen(
            [str(executable), "--log-path", str(log_path), "--title", title,
             "--parent-pid", str(os.getpid()), "--control-path", str(_control_path)],
            cwd=str(executable.parent), close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _log_path = log_path
        return True
    except OSError as exc:
        print(f"Could not open Stellar Blade FBX export log window: {exc}")
        return False


def append(message=""):
    if _log_path is not None:
        try:
            with _log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(str(message) + "\n")
        except OSError as exc:
            print(f"Could not write export log: {exc}")


def finish():
    append("")
    append("Export finished.")
