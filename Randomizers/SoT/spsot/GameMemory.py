"""
Talking to the running game: find its process, list its writable memory, read and write bytes.

Two backends, same interface:
  * LinuxMemory   - Linux / Steam Deck / Proton. Wine processes show up in /proc like any other process.
  * WindowsMemory - Windows, through the Win32 API (ctypes). UNTESTED: written from the Win32 docs.
"""
import os
import sys
from typing import Iterator, Optional, Tuple

GAME_EXE = "south park - the stick of truth.exe"
MAX_ADDRESS = 0x7F0000000000      # skip kernel-ish / vdso ranges on Linux


class ProcessMemory:
    pid: int = -1

    def regions(self) -> Iterator[Tuple[int, int]]:
        """Yield (start, end) of every committed, writable memory region."""
        raise NotImplementedError

    def read(self, addr: int, size: int) -> bytes:
        """Read bytes; returns b'' if the memory cannot be read."""
        raise NotImplementedError

    def write(self, addr: int, data: bytes) -> bool:
        raise NotImplementedError

    def alive(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        pass


# --------------------------------------------------------------------------- Linux
class LinuxMemory(ProcessMemory):
    def __init__(self, pid: int):
        self.pid = pid
        self._f = open(f"/proc/{pid}/mem", "r+b", buffering=0)

    def regions(self):
        with open(f"/proc/{self.pid}/maps") as f:
            for line in f:
                parts = line.split()
                # line format: "start-end perms offset dev inode path"  (perms is column 1, NOT column 0)
                if len(parts) < 2 or not parts[1].startswith("rw"):
                    continue
                a, b = parts[0].split("-")
                start, end = int(a, 16), int(b, 16)
                if start >= MAX_ADDRESS:
                    continue
                yield start, end

    def read(self, addr, size):
        try:
            self._f.seek(addr)
            return self._f.read(size) or b""
        except (OSError, ValueError, OverflowError):
            return b""

    def write(self, addr, data):
        try:
            self._f.seek(addr)
            self._f.write(data)
            return True
        except (OSError, ValueError, OverflowError):
            return False

    def alive(self):
        return os.path.exists(f"/proc/{self.pid}")

    def close(self):
        try:
            self._f.close()
        except OSError:
            pass


def _find_pid_linux() -> Optional[int]:
    best_pid, best_rss = None, 0
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode("utf-8", "ignore").lower()
            if GAME_EXE not in cmd:
                continue
            # skip the launcher processes that merely mention the exe name
            if any(bad in cmd for bad in ("steam.exe", "proton", "steam-runtime")):
                continue
            rss = 0
            with open(f"/proc/{name}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss = int("".join(ch for ch in line if ch.isdigit()) or 0)
                        break
            if rss > best_rss:                  # the real game is the biggest matching process
                best_pid, best_rss = int(name), rss
        except OSError:
            continue
    return best_pid


# --------------------------------------------------------------------------- Windows
class WindowsMemory(ProcessMemory):
    def __init__(self, pid: int):
        import ctypes
        from ctypes import wintypes
        self.pid = pid
        self._ct = ctypes
        self._wt = wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._k32 = k32
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                          ctypes.POINTER(ctypes.c_size_t)]
        k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                           ctypes.POINTER(ctypes.c_size_t)]
        k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        k32.VirtualQueryEx.restype = ctypes.c_size_t
        # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION
        self._h = k32.OpenProcess(0x0400 | 0x0010 | 0x0020 | 0x0008, False, pid)
        if not self._h:
            raise OSError(f"OpenProcess failed (error {ctypes.get_last_error()}); try running the client as administrator")

        class MBI(ctypes.Structure):
            _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                        ("AllocationProtect", wintypes.DWORD), ("PartitionId", wintypes.WORD),
                        ("RegionSize", ctypes.c_size_t), ("State", wintypes.DWORD),
                        ("Protect", wintypes.DWORD), ("Type", wintypes.DWORD)]
        self._MBI = MBI

    def regions(self):
        ct = self._ct
        addr = 0
        mbi = self._MBI()
        while addr < 0x80000000:            # the game is a 32-bit process
            if not self._k32.VirtualQueryEx(self._h, ct.c_void_p(addr), ct.byref(mbi), ct.sizeof(mbi)):
                break
            size = mbi.RegionSize or 0x1000
            writable = mbi.Protect & (0x04 | 0x08 | 0x40 | 0x80)       # RW, WRITECOPY, EXEC_RW, EXEC_WRITECOPY
            if mbi.State == 0x1000 and writable and not (mbi.Protect & 0x101):   # committed, no GUARD/NOACCESS
                yield addr, addr + size
            addr += size

    def read(self, addr, size):
        ct = self._ct
        buf = ct.create_string_buffer(size)
        got = ct.c_size_t(0)
        if not self._k32.ReadProcessMemory(self._h, ct.c_void_p(addr), buf, size, ct.byref(got)):
            return buf.raw[:got.value] if got.value else b""
        return buf.raw[:got.value]

    def write(self, addr, data):
        ct = self._ct
        wrote = ct.c_size_t(0)
        return bool(self._k32.WriteProcessMemory(self._h, ct.c_void_p(addr), data, len(data), ct.byref(wrote)))

    def alive(self):
        ct = self._ct
        code = self._wt.DWORD(0)
        self._k32.GetExitCodeProcess(self._h, ct.byref(code))
        return code.value == 259             # STILL_ACTIVE

    def close(self):
        if getattr(self, "_h", None):
            self._k32.CloseHandle(self._h)
            self._h = None


def _find_pid_windows() -> Optional[int]:
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)       # TH32CS_SNAPPROCESS
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    found = None
    ok = k32.Process32FirstW(snap, ctypes.byref(entry))
    while ok:
        if entry.szExeFile.lower() == GAME_EXE:
            found = int(entry.th32ProcessID)
            break
        ok = k32.Process32NextW(snap, ctypes.byref(entry))
    k32.CloseHandle(snap)
    return found


# --------------------------------------------------------------------------- public helpers
def find_game_pid() -> Optional[int]:
    return _find_pid_windows() if sys.platform == "win32" else _find_pid_linux()


def open_memory(pid: int) -> ProcessMemory:
    return WindowsMemory(pid) if sys.platform == "win32" else LinuxMemory(pid)
