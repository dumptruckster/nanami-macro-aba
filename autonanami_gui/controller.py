import ctypes
import shutil
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from core.automation.macro import RobloxMacro
from core.helpers.config import ConfigStore
from core.helpers.paths import get_bundled_sound_path, get_bundled_sounds_dir, get_data_dir, get_exe_sounds_dir, get_offsets_path, get_sounds_dir
from core.memory.process import ProcessConnection
from core.offsets.loader import RobloxOffsets

DEFAULT_SOUND = "osu-hit-sound.mp3"
SKILL_KEYS = {"1", "2", "4"}
SOUND_ON_KEY_PRESS = ("1", "2", "3", "4")
HIT_SOUND_TRIGGERS = ("hit", "keypress")


class AutomationController(QObject):
    log_message = Signal(str, str)
    state_changed = Signal(dict)
    gui_toggle_requested = Signal()
    hit_landed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.already_shut_down = False
        self.stop_event = threading.Event()
        self.attach_lock = threading.Lock()
        self.attach_is_underway = False
        self.macro_key_is_down = False
        self.gui_key_is_down = False
        self._last_macro_toggle = 0.0
        self._last_gui_toggle = 0.0
        self.sound_keys_are_down = False
        self.warned_about_a_bad_sound = False
        self.carried_old_settings_over = False
        self.versions_we_already_checked = set()
        self.times_we_checked_on_roblox = 0

        self.config = ConfigStore(get_data_dir() / "config.json")
        self.carry_over_old_settings()

        self.connection = ProcessConnection()
        self.offsets = RobloxOffsets(get_offsets_path())
        self.offsets.load()

        self._app_state = {
            "attached": False,
            "running": False,
            "pid": None,
            "moduleBase": "N/A",
            "keybind": str(self.config.get("keybind", "F1")),
            "guiKeybind": str(self.config.get("gui_keybind", "Insert")),
            "showKeybind": bool(self.config.get("show_keybind", False)),
            "autoAttach": bool(self.config.get("auto_attach", False)),
            "showOverlay": bool(self.config.get("show_overlay", False)),
            "silentLaunch": bool(self.config.get("silent_launch", False)),
            "toggleSound": bool(self.config.get("toggle_sound", True)),
            "successRateEnabled": bool(self.config.get("success_rate_enabled", False)),
            "successRate": max(0, min(100, int(self.config.get("success_rate", 100)))),
            "hitSound": str(self.config.get("hit_sound", DEFAULT_SOUND)),
            "hitSoundTrigger": str(self.config.get("hit_sound_trigger", "hit")),
        }

        self.macro = RobloxMacro(self.connection, self.offsets, hotkey=self._app_state["keybind"])
        self.macro.on_hit = self.when_a_hit_lands
        self.give_the_macro_the_success_rate()

        self.make_sure_the_hit_sound_exists()
        self.sound_output = None
        self.sound_player = None

        self.roblox_check_timer = QTimer(self)
        self.roblox_check_timer.setInterval(2000)
        self.roblox_check_timer.timeout.connect(self.check_up_on_roblox)
        self.roblox_check_timer.start()

        self.attach_retry_timer = QTimer(self)
        self.attach_retry_timer.setInterval(2000)
        self.attach_retry_timer.timeout.connect(self.keep_trying_to_attach)
        if self._app_state["autoAttach"]:
            self.attach_retry_timer.start()

        self.loop_thread = threading.Thread(target=self.run_the_loop, daemon=True)
        self.loop_thread.start()

        QTimer.singleShot(0, self.send_state_to_the_ui)

    def get_state(self):
        return dict(self._app_state)

    def send_state_to_the_ui(self):
        self.state_changed.emit(self.get_state())

    def log(self, message, level="info"):
        self.log_message.emit(str(message), str(level))

    def carry_over_old_settings(self):
        if self.config.values:
            return
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).resolve().parent / "config.json")
        candidates.append(Path(__file__).resolve().parents[1] / "config.json")
        for candidate in candidates:
            if candidate == self.config.path or not candidate.is_file():
                continue
            old_settings = ConfigStore(candidate)
            if old_settings.values:
                self.config.values = dict(old_settings.values)
                self.config.save()
                self.carried_old_settings_over = True
                return

    def sound_folders(self):
        folders = []
        try:
            exe_sounds = get_exe_sounds_dir()
        except Exception:
            exe_sounds = None
        if exe_sounds is not None:
            folders.append(exe_sounds)
        folders.append(get_sounds_dir())
        return folders

    def make_sure_the_hit_sound_exists(self):
        if not self._app_state.get("hitSound"):
            self._app_state["hitSound"] = DEFAULT_SOUND
        if not self.sound_file_to_use().is_file():
            self._app_state["hitSound"] = DEFAULT_SOUND

    def list_sounds(self):
        names = []
        folders = []
        try:
            bundled = get_bundled_sounds_dir()
        except Exception:
            bundled = None
        if bundled is not None:
            folders.append(bundled)
        folders.extend(self.sound_folders())
        for folder in folders:
            try:
                files = sorted(folder.iterdir())
            except Exception:
                continue
            for path in files:
                if path.is_file() and path.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"):
                    if path.name not in names:
                        names.append(path.name)
        return names

    def sound_file_to_use(self):
        name = str(self._app_state.get("hitSound") or "")
        if name:
            for folder in self.sound_folders():
                candidate = folder / name
                if candidate.is_file():
                    return candidate
            bundled = Path(get_bundled_sound_path(name))
            if bundled.is_file():
                return bundled
        return Path(get_bundled_sound_path(DEFAULT_SOUND))

    def get_the_sound_player(self):
        if self.sound_player is None:
            self.sound_output = QAudioOutput(self)
            self.sound_output.setVolume(1.0)
            self.sound_player = QMediaPlayer(self)
            self.sound_player.setAudioOutput(self.sound_output)
            self.sound_player.errorOccurred.connect(self.the_sound_did_not_play)
            self.hit_landed.connect(self.play_the_hit_sound)
            sound = self.sound_file_to_use()
            if sound.is_file():
                self.sound_player.setSource(QUrl.fromLocalFile(str(sound)))
        return self.sound_player

    def the_sound_did_not_play(self, _error, _message):
        if self.warned_about_a_bad_sound:
            return
        self.warned_about_a_bad_sound = True
        self.log("That sound file didn't play — mp3 and wav are your safest bets.", "warning")

    def when_a_hit_lands(self):
        if self._app_state["hitSoundTrigger"] == "hit":
            self.hit_landed.emit()

    def play_the_hit_sound(self):
        if not self._app_state["toggleSound"]:
            return
        try:
            player = self.get_the_sound_player()
            if player is None:
                return
            player.stop()
            player.play()
        except Exception:
            pass

    def preview_hit_sound(self):
        try:
            player = self.get_the_sound_player()
            if player is None:
                return
            player.stop()
            player.play()
        except Exception:
            pass

    def set_hit_sound(self, source):
        src = Path(str(source))
        if not src.is_file():
            self.log("That file doesn't exist anymore — pick another one.", "warning")
            return False
        destination = self.sound_folders()[0] / src.name
        try:
            if src.resolve() != destination.resolve():
                shutil.copy2(src, destination)
        except Exception:
            self.log("Couldn't copy that sound into the sounds folder.", "error")
            return False
        return self.set_hit_sound_name(destination.name)

    def set_hit_sound_name(self, name):
        wanted = str(name or "")
        if not wanted:
            return False
        found = None
        for folder in self.sound_folders():
            candidate = folder / wanted
            if candidate.is_file():
                found = candidate
                break
        if found is None:
            bundled = Path(get_bundled_sound_path(wanted))
            if bundled.is_file():
                found = bundled
        if found is None:
            return False
        self._app_state["hitSound"] = found.name
        self.config.set("hit_sound", found.name)
        try:
            player = self.get_the_sound_player()
            if player is not None:
                player.setSource(QUrl.fromLocalFile(str(found)))
        except Exception:
            pass
        self.warned_about_a_bad_sound = False
        self.send_state_to_the_ui()
        self.log(f"Hit sound set to {found.name}.", "success")
        return True

    def set_hit_sound_trigger(self, when):
        choice = when if when in HIT_SOUND_TRIGGERS else "hit"
        if self._app_state["hitSoundTrigger"] == choice:
            return
        self._app_state["hitSoundTrigger"] = choice
        self.config.set("hit_sound_trigger", choice)
        self.send_state_to_the_ui()
        self.log("Hit sound now plays " + ("on every landed hit." if choice == "hit" else "when you press 1, 2, 3 or 4."), "info")

    def open_sounds_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.sound_folders()[0])))

    def list_pids(self):
        try:
            processes = self.connection.proc_mgr.list_processes()
        except Exception:
            return []
        roblox = [
            {"pid": int(p.get("pid", 0)), "name": str(p.get("name") or "")}
            for p in processes
            if "robloxplayerbeta" in str(p.get("name") or "").lower()
        ]
        return sorted(roblox, key=lambda item: item["pid"])

    def attach_to_pid(self, pid=None, quiet=False):
        if self._app_state["attached"] or self.already_shut_down:
            return
        with self.attach_lock:
            if self.attach_is_underway:
                return
            self.attach_is_underway = True
        target = int(pid) if pid else None
        if not quiet:
            if target:
                self.log(f"Attaching to PID {target}...", "info")
            else:
                self.log("Looking for a Roblox process...", "info")
        threading.Thread(target=self.attach_in_the_background, args=(target, quiet), daemon=True).start()

    def attach_in_the_background(self, target, quiet):
        success = False
        try:
            pid = target or self.connection.proc_mgr.find_process_by_name("RobloxPlayerBeta.exe")
            if pid:
                self.make_the_data_match_the_game(self.read_the_game_version(int(pid)))
                handle = None
                base = None
                try:
                    handle = self.connection.proc_mgr.open_process(int(pid))
                    if handle:
                        base = self.connection.proc_mgr.get_module_base(int(pid), "RobloxPlayerBeta.exe")
                except Exception:
                    handle = None
                    base = None
                if handle and base:
                    old_handle = self.connection.process_handle
                    self.connection.process_handle = handle
                    self.connection.pid = int(pid)
                    self.connection.module_base = int(base)
                    if old_handle and old_handle != handle:
                        try:
                            self.connection.kernel32.CloseHandle(old_handle)
                        except Exception:
                            pass
                    success = True
                else:
                    if handle:
                        try:
                            self.connection.kernel32.CloseHandle(handle)
                        except Exception:
                            pass
                    try:
                        success = self.connection.try_attach_process(
                            "RobloxPlayerBeta.exe",
                            "RobloxPlayerBeta.exe",
                            int(target) if target else None,
                        )
                    except Exception:
                        success = False
        except Exception:
            success = False

        if self.stop_event.is_set():
            if success:
                self.connection.detach()
            with self.attach_lock:
                self.attach_is_underway = False
            return

        try:
            if success:
                module_base = int(self.connection.module_base or 0)
                self._app_state["attached"] = True
                self._app_state["pid"] = int(self.connection.pid)
                self._app_state["moduleBase"] = hex(module_base) if module_base else "N/A"
                self.send_state_to_the_ui()
                self.log(f"Attached to Roblox (PID {self.connection.pid}).", "success")
                if not self._app_state["running"]:
                    self.start_macro()
            elif not quiet:
                self.log("Couldn't attach — is Roblox actually running?", "error")
        finally:
            with self.attach_lock:
                self.attach_is_underway = False

    def detach(self, quiet=False):
        if self._app_state["running"]:
            self.stop_macro()
        try:
            self.connection.detach()
        except Exception:
            pass
        self.macro.reset()
        self._app_state["attached"] = False
        self._app_state["pid"] = None
        self._app_state["moduleBase"] = "N/A"
        self.send_state_to_the_ui()
        if not quiet:
            self.log("Detached.", "info")

    def start_macro(self):
        if not self._app_state["attached"]:
            self.log("Attach to Roblox first.", "warning")
            return
        if self._app_state["running"]:
            return
        try:
            self.macro.hotkey = self.macro.normalize_key(self._app_state["keybind"])
        except Exception:
            self.macro.hotkey = self._app_state["keybind"]
        self._app_state["running"] = True
        self.send_state_to_the_ui()
        self.log("Macro is running — go crazy you dirty little slut you.", "success")

    def stop_macro(self):
        if not self._app_state["running"]:
            return
        self._app_state["running"] = False
        self.send_state_to_the_ui()
        self.log("Macro stopped.", "info")

    def set_keybind(self, key):
        try:
            chosen = self.macro.normalize_key(key or "F1")
        except Exception:
            chosen = key or "F1"
        self._app_state["keybind"] = chosen
        self.macro.hotkey = chosen
        self.config.set("keybind", chosen)
        try:
            self.macro_key_is_down = self.macro._is_key_down(chosen)
        except Exception:
            self.macro_key_is_down = False
        self.send_state_to_the_ui()

    def set_gui_keybind(self, key):
        try:
            chosen = self.macro.normalize_key(key or "Insert")
        except Exception:
            chosen = key or "Insert"
        self._app_state["guiKeybind"] = chosen
        self.config.set("gui_keybind", chosen)
        try:
            self.gui_key_is_down = self.macro._is_key_down(chosen)
        except Exception:
            self.gui_key_is_down = False
        self.send_state_to_the_ui()

    def set_show_keybind(self, show):
        self._app_state["showKeybind"] = bool(show)
        self.config.set("show_keybind", bool(show))
        self.send_state_to_the_ui()

    def set_auto_attach(self, enabled):
        self._app_state["autoAttach"] = bool(enabled)
        self.config.set("auto_attach", bool(enabled))
        if enabled:
            self.attach_retry_timer.start()
        else:
            self.attach_retry_timer.stop()
        self.send_state_to_the_ui()

    def set_show_overlay(self, enabled):
        self._app_state["showOverlay"] = bool(enabled)
        self.config.set("show_overlay", bool(enabled))
        self.send_state_to_the_ui()

    def set_silent_launch(self, enabled):
        self._app_state["silentLaunch"] = bool(enabled)
        self.config.set("silent_launch", bool(enabled))
        self.send_state_to_the_ui()

    def set_toggle_sound(self, enabled):
        self._app_state["toggleSound"] = bool(enabled)
        self.config.set("toggle_sound", bool(enabled))
        self.send_state_to_the_ui()

    def set_success_rate_enabled(self, enabled):
        self._app_state["successRateEnabled"] = bool(enabled)
        self.config.set("success_rate_enabled", bool(enabled))
        self.give_the_macro_the_success_rate()
        self.send_state_to_the_ui()

    def set_success_rate(self, value):
        try:
            rate = max(0, min(100, int(value)))
        except Exception:
            rate = 100
        self._app_state["successRate"] = rate
        self.config.set("success_rate", rate)
        self.give_the_macro_the_success_rate()
        self.send_state_to_the_ui()

    def give_the_macro_the_success_rate(self):
        self.macro.success_rate_enabled = bool(self._app_state["successRateEnabled"])
        self.macro.success_rate = max(0, min(100, int(self._app_state["successRate"])))

    def read_the_game_version(self, pid):
        try:
            path = self.connection.proc_mgr.get_module_path(int(pid), "RobloxPlayerBeta.exe")
            return self.offsets.client_version_from_path(path)
        except Exception:
            return ""

    def make_the_data_match_the_game(self, version):
        if version == self.offsets.client_version or version in self.versions_we_already_checked:
            return
        self.versions_we_already_checked.add(version)
        saved_values = dict(self.offsets.values)
        saved_version = self.offsets.client_version
        saved_source = self.offsets.source
        try:
            self.offsets.refresh(get_offsets_path(), None, version)
        except Exception:
            pass
        if not self.offsets.has_required():
            self.offsets.values = saved_values
            self.offsets.client_version = saved_version
            self.offsets.source = saved_source
            self.versions_we_already_checked.discard(version)
        self.macro.reset()

    def match_the_game_and_say_so(self, version):
        self.make_the_data_match_the_game(version)
        if self.stop_event.is_set():
            return
        if version and self.offsets.client_version == version:
            self.log(f"Roblox updated — resynced for {version}.", "info")

    def look_for_a_new_game_version(self):
        pid = self.connection.pid
        if not pid:
            return
        version = self.read_the_game_version(int(pid))
        if version == self.offsets.client_version or version in self.versions_we_already_checked:
            return
        threading.Thread(target=self.match_the_game_and_say_so, args=(version,), daemon=True).start()

    def overlay_position(self):
        try:
            hwnd = self.macro._find_roblox_hwnd()
        except Exception:
            return None
        if not hwnd:
            return None
        try:
            import win32gui

            x, y = win32gui.ClientToScreen(hwnd, (16, 104))
            return QPoint(int(x), int(y))
        except Exception:
            return None

    def run_the_loop(self):
        while not self.stop_event.is_set():
            busy = self._app_state["attached"] and self._app_state["running"]
            try:
                self.watch_for_key_presses()
                if busy:
                    self.macro.run_tick()
            except Exception:
                pass
            self.stop_event.wait(0.001)

    def watch_for_key_presses(self):
        try:
            macro_down = bool(self._app_state["keybind"]) and self.macro._is_key_down(self._app_state["keybind"])
        except Exception:
            macro_down = False
        now = time.monotonic()
        if macro_down and not self.macro_key_is_down:
            self.macro_key_is_down = True
            if now - self._last_macro_toggle >= 0.15:
                self._last_macro_toggle = now
                self.toggle_the_macro()
        elif not macro_down:
            self.macro_key_is_down = False

        try:
            gui_down = bool(self._app_state["guiKeybind"]) and self.macro._is_key_down(self._app_state["guiKeybind"])
        except Exception:
            gui_down = False
        if gui_down and not self.gui_key_is_down:
            self.gui_key_is_down = True
            if now - self._last_gui_toggle >= 0.15:
                self._last_gui_toggle = now
                self.gui_toggle_requested.emit()
        elif not gui_down:
            self.gui_key_is_down = False

        if self._app_state["hitSoundTrigger"] == "keypress":
            try:
                pressing = any(self.macro._is_key_down(k) for k in SOUND_ON_KEY_PRESS)
            except Exception:
                pressing = False
            if pressing and not self.sound_keys_are_down:
                self.sound_keys_are_down = True
                self.hit_landed.emit()
            elif not pressing:
                self.sound_keys_are_down = False

    def toggle_the_macro(self):
        if not self._app_state["attached"]:
            return
        if self._app_state["running"]:
            if self._app_state["keybind"] not in SKILL_KEYS:
                self.stop_macro()
        else:
            self.start_macro()

    def keep_trying_to_attach(self):
        if self._app_state["attached"] or self.already_shut_down:
            return
        with self.attach_lock:
            if self.attach_is_underway:
                return
        pids = self.list_pids()
        if pids:
            newest = max(pids, key=lambda item: item["pid"])
            self.attach_to_pid(newest["pid"], quiet=True)

    def check_up_on_roblox(self):
        if not self._app_state["attached"] or self.already_shut_down:
            return
        if not self.roblox_is_still_running():
            self.log("Roblox closed — detached.", "warning")
            self.detach(quiet=True)
            return
        self.times_we_checked_on_roblox += 1
        if self.times_we_checked_on_roblox % 5 == 0:
            self.look_for_a_new_game_version()

    def roblox_is_still_running(self):
        handle = self.connection.process_handle
        if not handle:
            return False
        try:
            import ctypes.wintypes as wintypes

            code = wintypes.DWORD(0)
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259
        except Exception:
            return True

    def shutdown(self):
        if self.already_shut_down:
            return
        self.already_shut_down = True
        self.stop_event.set()
        try:
            self.roblox_check_timer.stop()
            self.attach_retry_timer.stop()
        except Exception:
            pass
        if self.loop_thread is not None and self.loop_thread.is_alive() and self.loop_thread is not threading.current_thread():
            self.loop_thread.join(timeout=1.0)
        try:
            self.macro.cleanup()
        except Exception:
            pass
        try:
            self.connection.detach()
        except Exception:
            pass
        self._app_state["attached"] = False
        self._app_state["running"] = False
        self._app_state["pid"] = None
        self._app_state["moduleBase"] = "N/A"
        try:
            if self.sound_player is not None:
                self.sound_player.stop()
        except Exception:
            pass
