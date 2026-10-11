import ctypes
import random
import time
from ctypes import wintypes
from typing import List, Optional

from core.memory.process import ProcessConnection
from core.offsets.loader import RobloxOffsets

_KEY_ALIASES = {
    "esc": "Escape",
    "return": "Enter",
    "ctrl": "Control",
    "controlleft": "Control",
    "controlright": "Control",
    "shiftleft": "Shift",
    "shiftright": "Shift",
    "altleft": "Alt",
    "altright": "Alt",
    "metaleft": "Meta",
    "metaright": "Meta",
    "left": "ArrowLeft",
    "right": "ArrowRight",
    "up": "ArrowUp",
    "down": "ArrowDown",
    "del": "Delete",
    "ins": "Insert",
}

_KEY_VK_CODES = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "NUMPADENTER": 0x0D,
    "SHIFT": 0x10,
    "CONTROL": 0x11,
    "ALT": 0x12,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "ARROWLEFT": 0x25,
    "ARROWUP": 0x26,
    "ARROWRIGHT": 0x27,
    "ARROWDOWN": 0x28,
    "PRINTSCREEN": 0x2C,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "META": 0x5B,
    "CONTEXTMENU": 0x5D,
    "NUMPAD0": 0x60,
    "NUMPAD1": 0x61,
    "NUMPAD2": 0x62,
    "NUMPAD3": 0x63,
    "NUMPAD4": 0x64,
    "NUMPAD5": 0x65,
    "NUMPAD6": 0x66,
    "NUMPAD7": 0x67,
    "NUMPAD8": 0x68,
    "NUMPAD9": 0x69,
    "NUMPADMULTIPLY": 0x6A,
    "NUMPADADD": 0x6B,
    "NUMPADSUBTRACT": 0x6D,
    "NUMPADDECIMAL": 0x6E,
    "NUMPADDIVIDE": 0x6F,
    "NUMLOCK": 0x90,
    "SCROLLLOCK": 0x91,
    "SEMICOLON": 0xBA,
    "EQUAL": 0xBB,
    "COMMA": 0xBC,
    "MINUS": 0xBD,
    "PERIOD": 0xBE,
    "SLASH": 0xBF,
    "BACKQUOTE": 0xC0,
    "BRACKETLEFT": 0xDB,
    "BACKSLASH": 0xDC,
    "BRACKETRIGHT": 0xDD,
    "QUOTE": 0xDE,
}

_KEY_DISPLAY_FIXES = {
    "Arrowleft": "ArrowLeft",
    "Arrowright": "ArrowRight",
    "Arrowup": "ArrowUp",
    "Arrowdown": "ArrowDown",
    "Pageup": "PageUp",
    "Pagedown": "PageDown",
    "Capslock": "CapsLock",
    "Printscreen": "PrintScreen",
    "Contextmenu": "ContextMenu",
    "Numlock": "NumLock",
    "Scrolllock": "ScrollLock",
    "Bracketleft": "BracketLeft",
    "Bracketright": "BracketRight",
}

_KEY_DISPLAY_NAMES = {}
for _code in _KEY_VK_CODES:
    _display = _code.title()
    for _rough, _fixed in _KEY_DISPLAY_FIXES.items():
        _display = _display.replace(_rough, _fixed)
    _KEY_DISPLAY_NAMES[_code.lower()] = _display

CLICK_COOLDOWN = 0.2
SKILL_KEY_COOLDOWN = 0.2
MISS_OFFSET_MIN = 18
MISS_OFFSET_MAX = 72

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        class _MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
            ]
        _fields_ = [("mi", _MOUSEINPUT)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT)]

class RobloxMacro:
    def __init__(self, connection: ProcessConnection, offsets: RobloxOffsets, hotkey: str = "1") -> None:
        self.connection = connection
        self.offsets = offsets
        self.hotkey = hotkey or "1"
        self.success_rate_enabled = False
        self.success_rate = 100
        self.on_hit = None
        self.debounce = False
        self.current_ui_addr = 0
        self.is_searching = False
        self.search_end_time = 0.0
        self._skill_key_cooldown_until = 0.0
        self._last_search_time = 0.0
        self._click_cooldown_until = 0.0
        self._cut_ui = 0
        self._cut_plan = ""
        self._cut_margin = 0.0
        self._cut_inside = False
        self._workspace_addr = 0
        self._workspace_cache_time = 0.0
        self._roblox_hwnd_cache: Optional[int] = None
        self._roblox_hwnd_cache_time = 0.0

    def reset(self) -> None:
        self.debounce = False
        self.current_ui_addr = 0
        self.is_searching = False
        self.search_end_time = 0.0
        self._skill_key_cooldown_until = 0.0
        self._last_search_time = 0.0
        self._click_cooldown_until = 0.0
        self._cut_ui = 0
        self._cut_plan = ""
        self._cut_margin = 0.0
        self._cut_inside = False
        self._workspace_addr = 0
        self._workspace_cache_time = 0.0
        self._roblox_hwnd_cache = None
        self._roblox_hwnd_cache_time = 0.0

    def cleanup(self) -> None:
        self._roblox_hwnd_cache = None

    def normalize_key(self, key: str) -> str:
        if key == " ":
            return "Space"
        name = str(key or "").strip()
        if not name:
            return ""
        alias = _KEY_ALIASES.get(name.lower())
        if alias:
            return alias
        if len(name) == 1:
            return name.upper()
        if name.lower().startswith("f") and name[1:].isdigit():
            return name.upper()
        display = _KEY_DISPLAY_NAMES.get(name.lower())
        if display is None:
            return name
        if name != name.lower() and name != name.upper():
            return name
        return display

    def run_tick(self, cooldown: float = CLICK_COOLDOWN) -> None:
        if not self.connection.process_handle:
            return
        now = time.monotonic()
        if self.debounce and now >= self._click_cooldown_until:
            self.debounce = False
            self.current_ui_addr = 0
        if now >= self._skill_key_cooldown_until and self._any_skill_key_down():
            self.is_searching = True
            self.search_end_time = now + 10.0
            self.current_ui_addr = 0
            self._last_search_time = 0.0
            self._skill_key_cooldown_until = now + SKILL_KEY_COOLDOWN
        if self.is_searching:
            if now > self.search_end_time:
                self.is_searching = False
            elif now - self._last_search_time >= 0.015:
                self._last_search_time = now
                ui_addr = self._find_nanami_ui_addr()
                if ui_addr:
                    self.current_ui_addr = ui_addr
                    self.is_searching = False
                    self.debounce = False
        if self.current_ui_addr and not self.debounce:
            self._evaluate_ui(self.current_ui_addr, cooldown)

    def _any_skill_key_down(self) -> bool:
        return any(self._is_key_down(k) for k in ("1", "2", "4"))

    def _is_key_down(self, key: str) -> bool:
        try:
            vk = self._virtual_key(key)
            if vk is None:
                return False
            return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
        except Exception:
            return False

    def _virtual_key(self, key: str) -> int | None:
        name = self.normalize_key(key)
        upper = name.upper()
        if len(name) == 1:
            if name.isalnum():
                return ord(upper)
            value = int(ctypes.windll.user32.VkKeyScanW(name))
            return None if value == -1 else value & 0xFF
        if upper.startswith("F") and upper[1:].isdigit():
            num = int(upper[1:])
            if 1 <= num <= 24:
                return 0x70 + num - 1
        return _KEY_VK_CODES.get(upper)

    def _find_nanami_ui_addr(self) -> int:
        workspace_addr = self._get_workspace_addr()
        if not workspace_addr:
            return 0
        return self._walk_tree(workspace_addr, max_depth=8)

    def _walk_tree(self, instance_addr: int, max_depth: int, current_depth: int = 0) -> int:
        if current_depth > max_depth or not instance_addr:
            return 0
        name = self._read_instance_name(instance_addr)
        if name == "NanamiCutGUI" and self._read_instance_class(instance_addr) == "BillboardGui":
            return instance_addr
        for child in self._read_child_list(instance_addr):
            found = self._walk_tree(child, max_depth, current_depth + 1)
            if found:
                return found
        return 0

    def _read_instance_name(self, addr: int) -> str:
        name_off = self.offsets.get("Instance_Name", 0x70)
        if not name_off:
            return ""
        container = addr + name_off
        name_ptr = self.connection.read_uint64(container)
        if name_ptr and name_ptr != container:
            direct = self._read_game_string(name_ptr)
            if direct:
                return direct
        if name_ptr:
            inner_off = self.offsets.get("Instance_NameInner", 8)
            if inner_off:
                inner_addr = name_ptr + inner_off
                inner = self._read_game_string(inner_addr)
                if inner:
                    return inner
                inner_ptr = self.connection.read_uint64(inner_addr)
                if inner_ptr:
                    inner = self._read_c_string(inner_ptr)
                    if inner:
                        return inner
        inline = self._read_game_string(container)
        if inline:
            return inline
        return ""

    def _read_instance_class(self, addr: int) -> str:
        class_desc_off = self.offsets.get("Instance_ClassDescriptor", 0x18)
        class_name_off = self.offsets.get("Instance_ClassDescriptorToClassName", 0x8)
        class_desc_ptr = self.connection.read_uint64(addr + class_desc_off)
        if not class_desc_ptr:
            return ""
        class_name_ptr = self.connection.read_uint64(class_desc_ptr + class_name_off)
        if not class_name_ptr:
            return ""
        return self._read_game_string(class_name_ptr)

    def _read_child_list(self, addr: int) -> List[int]:
        children_off = self.offsets.get("Instance_Children", 0x78)
        children_end_off = self.offsets.get("Instance_ChildrenEnd", 0x8)
        child_start = self.connection.read_uint64(addr + children_off)
        if not child_start:
            return []
        child_end = self.connection.read_uint64(child_start + children_end_off)
        if not child_end:
            return []
        children: List[int] = []
        ptr = self.connection.read_uint64(child_start)
        if not ptr:
            return []
        max_children = 8192
        count = 0
        while ptr != child_end and count < max_children:
            child_addr = self.connection.read_uint64(ptr)
            if child_addr:
                children.append(int(child_addr))
            ptr += 0x10
            count += 1
        return children

    def _read_game_string(self, address: int) -> str:
        if not address or not self.connection.process_handle:
            return ""
        for length_off in (0x18, 0x10):
            try:
                length = self.connection.read_int32(address + length_off)
                if length is None or length <= 0 or length >= 4096:
                    continue
                read_addr = address
                if length >= 16:
                    read_addr = self.connection.read_uint64(address)
                    if not read_addr:
                        continue
                data = self.connection.mem.read_memory(self.connection.process_handle, read_addr, length)
                if not data:
                    continue
                text = data.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
                if text:
                    return text
            except Exception:
                continue
        try:
            data = self.connection.mem.read_memory(self.connection.process_handle, address, 256)
            if not data:
                return ""
            return data.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _read_c_string(self, address: int, max_length: int = 4096) -> str:
        if not address or not self.connection.process_handle:
            return ""
        data = bytearray()
        try:
            while len(data) < max_length:
                chunk = self.connection.mem.read_memory(
                    self.connection.process_handle,
                    address + len(data),
                    min(64, max_length - len(data)),
                )
                if not chunk:
                    break
                null_index = chunk.find(b"\x00")
                if null_index >= 0:
                    data.extend(chunk[:null_index])
                    break
                data.extend(chunk)
                if len(chunk) < 64:
                    break
            return bytes(data).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _get_data_model(self) -> int:
        base = self.connection.module_base
        if not base:
            return 0
        fake_ptr_off = self.offsets.get("FakeDataModelPointer")
        fake_to_dm_off = self.offsets.get("FakeDataModelToDataModel")
        if not fake_ptr_off or not fake_to_dm_off:
            return 0
        fake_dm = self.connection.read_uint64(base + fake_ptr_off)
        if not fake_dm:
            return 0
        return int(self.connection.read_uint64(fake_dm + fake_to_dm_off) or 0)

    def _get_workspace_addr(self) -> int:
        now = time.monotonic()
        if self._workspace_addr and (now - self._workspace_cache_time) < 2.0:
            return self._workspace_addr
        dm_ptr = self._get_data_model()
        if not dm_ptr:
            self._workspace_addr = 0
            return 0
        ws_off = self.offsets.get("DataModel_Workspace", 0)
        if ws_off:
            ws_ptr = self.connection.read_uint64(dm_ptr + ws_off)
            if ws_ptr:
                self._workspace_addr = int(ws_ptr)
                self._workspace_cache_time = now
                return self._workspace_addr
        for child in self._read_child_list(dm_ptr):
            if self._read_instance_class(child) == "Workspace":
                self._workspace_addr = child
                self._workspace_cache_time = now
                return child
        self._workspace_addr = 0
        return 0

    def _evaluate_ui(self, ui_addr: int, cooldown: float) -> None:
        children = self._read_child_list(ui_addr)
        main_bar = 0
        for child in children:
            if self._read_instance_name(child) == "MainBar":
                main_bar = child
                break
        if not main_bar:
            self.current_ui_addr = 0
            self.is_searching = True
            self.search_end_time = time.monotonic() + 3.0
            return
        goal = 0
        cutter = 0
        for child in self._read_child_list(main_bar):
            name = self._read_instance_name(child)
            if name == "Goal":
                goal = child
            elif name == "Cutter":
                cutter = child
        if not goal or not cutter:
            return
        goal_x, cutter_x, size_x = self._read_goal_metrics(goal, cutter)
        if size_x <= 0:
            return
        if ui_addr != self._cut_ui or not self._cut_plan:
            self._cut_ui = ui_addr
            self._cut_inside = False
            self._cut_plan, self._cut_margin = self._roll_cut_plan(size_x)
        distance = abs(goal_x - cutter_x)
        threshold = size_x / 2.0
        if distance <= threshold:
            self._cut_inside = True
        if self._cut_plan == "early":
            fire = distance <= threshold + self._cut_margin
        elif self._cut_plan == "late":
            fire = self._cut_inside and threshold < distance <= threshold + self._cut_margin
        else:
            fire = distance <= threshold
        if not fire:
            return
        hit = self._cut_plan == "hit"
        self.debounce = True
        self._cut_ui = 0
        self._cut_plan = ""
        if hit:
            if self._click_mouse():
                self._notify_hit()
        else:
            self._apply_miss_offset()
            self._click_mouse()
        self._click_cooldown_until = time.monotonic() + max(0.0, float(cooldown))

    def _notify_hit(self) -> None:
        if self.on_hit is None:
            return
        try:
            self.on_hit()
        except Exception:
            pass

    def _should_hit_click(self) -> bool:
        if not self.success_rate_enabled:
            return True
        rate = max(0, min(100, int(self.success_rate)))
        if rate >= 100:
            return True
        if rate <= 0:
            return False
        return random.randint(1, 100) <= rate

    def _roll_cut_plan(self, size_x: float) -> tuple[str, float]:
        if self._should_hit_click():
            return "hit", 0.0
        side = random.choice(("early", "late"))
        margin = max(1.0, float(size_x) * random.uniform(0.15, 0.5))
        return side, margin

    def _apply_miss_offset(self) -> None:
        try:
            point = POINT()
            if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
                return
            spread = MISS_OFFSET_MIN + (100 - max(0, min(100, int(self.success_rate)))) * (MISS_OFFSET_MAX - MISS_OFFSET_MIN) // 100
            offset_x = random.randint(-spread, spread)
            offset_y = random.randint(-spread, spread)
            if offset_x == 0 and offset_y == 0:
                offset_x = random.choice([-spread, spread])
            ctypes.windll.user32.SetCursorPos(point.x + offset_x, point.y + offset_y)
        except Exception:
            pass

    def _read_goal_metrics(self, goal: int, cutter: int) -> tuple[float, float, float]:
        frame_pos_x = self.offsets.get("FramePositionX")
        frame_pos_off_x = self.offsets.get("FramePositionOffsetX")
        frame_size_x = self.offsets.get("FrameSizeX")
        frame_size_off_x = self.offsets.get("FrameSizeOffsetX")
        goal_x = float(self.connection.read_float(goal + frame_pos_x) or 0.0)
        cutter_x = float(self.connection.read_float(cutter + frame_pos_x) or 0.0)
        size_x = float(self.connection.read_float(goal + frame_size_x) or 0.0)
        if goal_x == 0.0:
            goal_x = float(self.connection.read_int32(goal + frame_pos_off_x) or 0)
            cutter_x = float(self.connection.read_int32(cutter + frame_pos_off_x) or 0)
            size_x = float(self.connection.read_int32(goal + frame_size_off_x) or 0)
        return goal_x, cutter_x, size_x

    def _find_roblox_hwnd(self) -> int:
        now = time.monotonic()
        if self._roblox_hwnd_cache and (now - self._roblox_hwnd_cache_time) < 3.0:
            try:
                if ctypes.windll.user32.IsWindow(self._roblox_hwnd_cache):
                    return self._roblox_hwnd_cache
            except Exception:
                pass
            self._roblox_hwnd_cache = None
        try:
            import win32gui
            import win32process
        except Exception:
            return 0
        if not self.connection.pid:
            return 0
        found: list[tuple[int, int]] = []
        def callback(hwnd, _lparam):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                if win32gui.IsIconic(hwnd):
                    return True
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == self.connection.pid:
                    left, top, right, bottom = win32gui.GetClientRect(hwnd)
                    area = max(0, right - left) * max(0, bottom - top)
                    if area:
                        found.append((area, hwnd))
            except Exception:
                pass
            return True
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            return 0
        hwnd = max(found)[1] if found else 0
        if hwnd:
            self._roblox_hwnd_cache = hwnd
            self._roblox_hwnd_cache_time = now
        return hwnd

    def _click_mouse(self) -> bool:
        try:
            hwnd = self._find_roblox_hwnd()
            if not hwnd or ctypes.windll.user32.GetForegroundWindow() != hwnd:
                return False
            inputs = (INPUT * 2)()
            inputs[0].type = 0
            inputs[0].mi.dwFlags = 0x0002
            inputs[1].type = 0
            inputs[1].mi.dwFlags = 0x0004
            ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
            return True
        except Exception:
            return False
