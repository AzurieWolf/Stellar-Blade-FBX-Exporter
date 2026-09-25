"""Windows integration check: python test_log_window_process.py path/to/viewer.exe."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys
import tempfile
import time

viewer = Path(sys.argv[1]).resolve()
command = [str(viewer)] if viewer.suffix == '.exe' else [sys.executable, str(viewer)]
user32 = ctypes.WinDLL('user32', use_last_error=True)
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

def find_window(process):
    found = []
    @callback_type
    def collect(hwnd, unused):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f'Viewer exited early: {process.returncode}: {process.communicate()}')
        user32.EnumWindows(collect, 0)
        if found:
            hwnd = found[0]
            styles = user32.GetWindowLongPtrW(hwnd, -20)
            if styles & 0x40000 and not styles & 0x80:
                return hwnd
            found.clear()
        time.sleep(0.1)
    raise AssertionError('No taskbar app window appeared')

processes = []
with tempfile.TemporaryDirectory(prefix='stellar_log_owner_') as directory:
    log = Path(directory) / 'test.log'
    log.write_text('Parent lifetime verification\n', encoding='utf-8')
    def start_viewer(parent=None):
        args = command + ['--log-path', str(log), '--title', 'Log lifetime test']
        if parent is not None:
            args += ['--parent-pid', str(parent)]
        process = subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(process)
        return process
    try:
        owners = [subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdin.read()'],
                                   stdin=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW) for _ in range(2)]
        processes.extend(owners)
        viewers = [start_viewer(owner.pid) for owner in owners]
        windows = [find_window(process) for process in viewers]
        user32.ShowWindow(windows[0], 6)
        time.sleep(0.2)
        assert user32.IsIconic(windows[0]), 'Taskbar minimize failed'
        user32.ShowWindow(windows[0], 9)
        time.sleep(0.2)
        assert not user32.IsIconic(windows[0]), 'Taskbar restore failed'
        owners[0].stdin.close()
        assert owners[0].wait(timeout=5) == 0
        assert viewers[0].wait(timeout=5) == 0
        assert viewers[1].poll() is None, 'Unrelated viewer closed'
        owners[1].terminate()
        owners[1].wait(timeout=5)
        assert viewers[1].wait(timeout=5) == 0
        orphan = start_viewer(owners[0].pid)
        assert orphan.wait(timeout=5) == 0, 'Exited parent should not leave an orphan window'
        standalone = start_viewer()
        hwnd = find_window(standalone)
        user32.PostMessageW(hwnd, 0x10, 0, 0)
        assert standalone.wait(timeout=5) == 0
        print('PASS: taskbar flags, minimize/restore, independent owners, normal exit, terminated owner, exited owner and standalone close.')
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
