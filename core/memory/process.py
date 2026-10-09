import ctypes
import ctypes.wintypes as wintypes
import struct
import time
from typing import Optional

PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260),
    ]


class MemoryManager:
    def __init__(self) -> None:
        self.kernel32 = ctypes.windll.kernel32
        self.ntdll = ctypes.WinDLL("ntdll.dll")
        self.ntdll.NtReadVirtualMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.ntdll.NtReadVirtualMemory.restype = ctypes.c_long
        self.kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.kernel32.ReadProcessMemory.restype = wintypes.BOOL

    def read_memory(self, handle: int, address: int, size: int) -> Optional[bytes]:
        data = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        status = self.ntdll.NtReadVirtualMemory(handle, ctypes.c_void_p(address), ctypes.byref(data), size, ctypes.byref(bytes_read))
        if status == 0:
            return data.raw[:bytes_read.value]
        return None

    def read_int32(self, handle: int, address: int) -> Optional[int]:
        data = self.read_memory(handle, address, 4)
        if data is None or len(data) < 4:
            return None
        return int.from_bytes(data, "little", signed=True)

    def read_uint64(self, handle: int, address: int) -> Optional[int]:
        data = self.read_memory(handle, address, 8)
        if data is None or len(data) < 8:
            return None
        return int.from_bytes(data, "little")

    def read_float(self, handle: int, address: int) -> Optional[float]:
        data = self.read_memory(handle, address, 4)
        if data is None or len(data) < 4:
            return None
        return struct.unpack("<f", data)[0]


class ProcessManager:
    def __init__(self) -> None:
        self.kernel32 = ctypes.windll.kernel32

    def find_process_by_name(self, process_name: str) -> Optional[int]:
        snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == -1:
            return None
        try:
            pe32 = PROCESSENTRY32()
            pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if self.kernel32.Process32First(snapshot, ctypes.byref(pe32)):
                while True:
                    if pe32.szExeFile.decode("utf-8", errors="ignore").lower() == process_name.lower():
                        return pe32.th32ProcessID
                    if not self.kernel32.Process32Next(snapshot, ctypes.byref(pe32)):
                        break
            return None
        finally:
            self.kernel32.CloseHandle(snapshot)

    def list_processes(self):
        result = []
        snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == -1:
            return result
        try:
            pe32 = PROCESSENTRY32()
            pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if self.kernel32.Process32First(snapshot, ctypes.byref(pe32)):
                while True:
                    try:
                        name = pe32.szExeFile.decode("utf-8", errors="ignore")
                    except Exception:
                        name = ""
                    result.append({"pid": int(pe32.th32ProcessID), "name": name})
                    if not self.kernel32.Process32Next(snapshot, ctypes.byref(pe32)):
                        break
            return result
        finally:
            self.kernel32.CloseHandle(snapshot)

    def get_module_base(self, pid: int, module_name: str) -> Optional[int]:
        snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
        if snapshot == -1:
            return None
        try:
            me32 = MODULEENTRY32()
            me32.dwSize = ctypes.sizeof(MODULEENTRY32)
            if self.kernel32.Module32First(snapshot, ctypes.byref(me32)):
                while True:
                    if me32.szModule.decode("utf-8", errors="ignore").lower() == module_name.lower():
                        return int(ctypes.cast(me32.modBaseAddr, ctypes.c_void_p).value)
                    if not self.kernel32.Module32Next(snapshot, ctypes.byref(me32)):
                        break
            return None
        finally:
            self.kernel32.CloseHandle(snapshot)

    def get_module_path(self, pid: int, module_name: str) -> Optional[str]:
        snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
        if snapshot == -1:
            return None
        try:
            me32 = MODULEENTRY32()
            me32.dwSize = ctypes.sizeof(MODULEENTRY32)
            if self.kernel32.Module32First(snapshot, ctypes.byref(me32)):
                while True:
                    if me32.szModule.decode("utf-8", errors="ignore").lower() == module_name.lower():
                        return me32.szExePath.decode("utf-8", errors="ignore")
                    if not self.kernel32.Module32Next(snapshot, ctypes.byref(me32)):
                        break
            return None
        finally:
            self.kernel32.CloseHandle(snapshot)

    def open_process(self, pid: int):
        handle = self.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if handle:
            return handle
        handle = self.kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        return handle if handle else None


class ProcessConnection:
    def __init__(self) -> None:
        self.mem = MemoryManager()
        self.proc_mgr = ProcessManager()
        self.kernel32 = ctypes.windll.kernel32
        self.process_handle = None
        self.module_base = 0
        self.pid = 0
        self.process_name = "RobloxPlayerBeta.exe"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.detach()

    def attach_process(self, process_name: str, module_name: str, target_pid: int | None = None, poll_interval: float = 1.0) -> bool:
        self.detach()
        while True:
            if self.try_attach_process(process_name, module_name, target_pid):
                return True
            time.sleep(poll_interval)

    def try_attach_process(self, process_name: str, module_name: str, target_pid: int | None = None) -> bool:
        pid = target_pid if target_pid is not None else self.proc_mgr.find_process_by_name(process_name)
        if not pid:
            return False
        handle = self.proc_mgr.open_process(pid)
        if not handle:
            return False
        base = self.proc_mgr.get_module_base(pid, module_name)
        if not base:
            self.kernel32.CloseHandle(handle)
            return False
        old_handle = self.process_handle
        self.process_handle = handle
        self.pid = pid
        self.module_base = base
        self.process_name = process_name
        if old_handle and old_handle != handle:
            self.kernel32.CloseHandle(old_handle)
        return True

    def read_uint64(self, address: int) -> Optional[int]:
        if not self.process_handle:
            return None
        return self.mem.read_uint64(self.process_handle, address)

    def read_int32(self, address: int) -> Optional[int]:
        if not self.process_handle:
            return None
        return self.mem.read_int32(self.process_handle, address)

    def read_float(self, address: int) -> Optional[float]:
        if not self.process_handle:
            return None
        return self.mem.read_float(self.process_handle, address)

    def detach(self) -> None:
        if self.process_handle:
            self.kernel32.CloseHandle(self.process_handle)
        self.process_handle = None
        self.module_base = 0
        self.pid = 0
