import os
import sys
from pathlib import Path


def get_project_root() -> Path:
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parents[2]


def get_offsets_path() -> Path:
    return get_project_root() / "core" / "offsets" / "offsets.json"


def get_asset_path(name: str) -> str:
    root = get_project_root()
    candidate = root / name
    if candidate.exists():
        return str(candidate)
    return str((root / name).resolve())


def get_bundled_sound_path(name: str) -> str:
    candidate = get_project_root() / "sounds" / name
    if candidate.exists():
        return str(candidate)
    return get_asset_path(name)


def get_bundled_sounds_dir() -> Path | None:
    candidate = get_project_root() / "sounds"
    if candidate.is_dir():
        return candidate
    return None


def get_data_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / ".autonanami"
    path = base / "AutoNanami"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_sounds_dir() -> Path:
    path = get_data_dir() / "sounds"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_exe_sounds_dir() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    path = Path(sys.executable).resolve().parent / "sounds"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        return None
    return path
