import json
from pathlib import Path
from typing import Any


def _atomic_write(path: Path, data: str) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        handle.write(data)
    temp_path.replace(path)


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.values: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.values = {}
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                self.values = data
            else:
                self.values = {}
        except Exception:
            self.values = {}

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(self.path, json.dumps(self.values, indent=2))
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value
        self.save()

    def update(self, values: dict[str, Any]) -> None:
        if not isinstance(values, dict):
            return
        self.values.update(values)
        self.save()
