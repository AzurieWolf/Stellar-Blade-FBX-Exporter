"""Run with Python on Windows after building the log viewer."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import subprocess
import sys
import time

project = Path(__file__).resolve().parents[1]
if len(sys.argv) > 1:
    project = Path(sys.argv[1]).resolve()
worker = r'''
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location('log_bridge', sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
for line in sys.stdin:
    title = line.strip()
    assert m.start(title)
    empty = m._log_path.read_text() == ''
    m.append(title)
    print(json.dumps([m._process.pid, str(m._log_path), empty]), flush=True)
'''
u = ctypes.WinDLL('user32')
callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
u.EnumWindows.argtypes = [callback, wintypes.LPARAM]
u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u.IsWindowVisible.argtypes = [wintypes.HWND]
u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
def windows(pid):
    result = []
    @callback
    def collect(hwnd, unused):
        owner = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and u.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(hwnd, title, 256)
            result.append((hwnd, title.value))
        return True
    u.EnumWindows(collect, 0)
    return result

def wait_title(pid, title):
    for _ in range(100):
        found = windows(pid)
        if len(found) == 1 and found[0][1] == title:
            return found[0][0]
        time.sleep(.1)
    raise AssertionError((pid, title, windows(pid)))

def request(owner, title):
    owner.stdin.write(title + '\n')
    owner.stdin.flush()
    response = json.loads(owner.stdout.readline())
    assert response[2], 'New operation did not start with an empty log'
    return response

owners = []
try:
    for _ in range(2):
        owners.append(subprocess.Popen([sys.executable, '-u', '-c', worker,
            str(project / 'addon/stellar_blade_log_window.py')], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW))
    first = request(owners[0], 'Export one')
    wait_title(first[0], 'Export one')
    time.sleep(.3)
    hwnd = wait_title(first[0], 'Export one')
    other = request(owners[1], 'Other Blender')
    wait_title(other[0], 'Other Blender')
    assert first[0] != other[0]
    second = request(owners[0], 'Import two')
    assert first[0] == second[0], 'Viewer was not reused'
    assert first[1] != second[1], 'Operation did not get a fresh log'
    assert wait_title(second[0], 'Import two') == hwnd, 'Native window was replaced'
    wait_title(other[0], 'Other Blender')
    for i in range(5):
        assert request(owners[0], 'Rapid export')[0] == first[0]
    wait_title(first[0], 'Rapid export')
    u.PostMessageW(hwnd, 0x10, 0, 0)
    time.sleep(1)
    reopened = request(owners[0], 'Reopened')
    assert reopened[0] != first[0]
    wait_title(reopened[0], 'Reopened')
    owners[0].stdin.close()
    owners[0].wait(timeout=5)
    time.sleep(.5)
    assert not windows(reopened[0])
    wait_title(other[0], 'Other Blender')
    print('PASS: reuse same window, fresh logs, title updates, rapid requests, separate owners, reopen and parent exit.')
finally:
    for owner in owners:
        if owner.poll() is None:
            owner.terminate()
        owner.wait(timeout=5)

