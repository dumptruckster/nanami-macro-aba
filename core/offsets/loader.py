import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, Optional

IMTHEO_OFFSETS_URL = "https://offsets.imtheo.lol/offsets.json"
IMTHEO_VERSIONED_OFFSETS_URL = "https://offsets.imtheo.lol/{version}/offsets.json"
IMTHEO_USER_AGENT = "AutoNanami/1.0"
CLIENT_VERSION_RE = re.compile(r"version-[0-9a-zA-Z-]+")


class RobloxOffsets:
    REQUIRED_OFFSETS = (
        "FakeDataModelPointer",
        "FakeDataModelToDataModel",
        "FramePositionX",
        "FrameSizeX",
        "Instance_Name",
        "Instance_Children",
    )

    def __init__(self, offset_path: str | Path | None = None) -> None:
        self.offset_path = Path(offset_path or Path(__file__).resolve().parent / "offsets.json")
        self.values: Dict[str, int] = {}
        self.client_version = ""
        self.source = "none"
        self._memory_cache: Dict[str, Dict[str, object]] = {}

    def load(self, offset_path: str | Path | None = None) -> bool:
        path = Path(offset_path or self.offset_path)
        if not path.exists():
            return False
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return False
        if not isinstance(data, dict):
            return False
        parsed, version = self._parse_payload(data)
        if not self._has_required_values(parsed):
            return False
        self._replace_values(parsed, version, f"json:{path.name}")
        self.offset_path = path
        return True

    def load_from_imtheo(
        self,
        url: str = IMTHEO_OFFSETS_URL,
        timeout: float = 8.0,
        expected_version: str | None = None,
    ) -> bool:
        expected = self.normalize_client_version(expected_version)
        request_url = IMTHEO_VERSIONED_OFFSETS_URL.format(version=expected) if expected else url
        try:
            request = urllib.request.Request(request_url, headers={"User-Agent": IMTHEO_USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return False
        if not isinstance(data, dict):
            return False
        parsed, version = self._parse_payload(data)
        version = self.normalize_client_version(version)
        if expected and version != expected:
            return False
        if not self._has_required_values(parsed):
            return False
        self._replace_values(parsed, version, "imtheo")
        return True

    def refresh(
        self,
        bundled_path: str | Path | None = None,
        cache_path: str | Path | None = None,
        target_version: str | None = None,
    ) -> str:
        bundled = Path(bundled_path) if bundled_path else self.offset_path
        cached_values = dict(self.values)
        cached_version = self.client_version
        cached_source = self.source
        target = self.normalize_client_version(target_version)
        use_cache = cache_path is not None
        cache_key = target or "latest"

        if self.load_from_imtheo(expected_version=target or None):
            if use_cache:
                self._store_memory_cache(cache_key)
            return self.source

        if use_cache and self._load_memory_cache(cache_key):
            if not target or self.client_version == target:
                self.source = f"cache:{cache_key}"
                return self.source

        if bundled.exists() and self.load(bundled):
            if not target or self.client_version == target:
                return self.source

        if (
            cached_values
            and self._has_required_values(cached_values)
            and (not target or self.normalize_client_version(cached_version) == target)
        ):
            self.values = cached_values
            self.client_version = cached_version
            self.source = cached_source
            return self.source

        self.values = {}
        self.client_version = target
        self.source = "none"
        return "none"

    def _store_memory_cache(self, key: str) -> None:
        self._memory_cache[key] = {
            "values": dict(self.values),
            "client_version": self.client_version,
        }

    def _load_memory_cache(self, key: str) -> bool:
        entry = self._memory_cache.get(key)
        if not entry:
            return False
        values = entry.get("values")
        if not isinstance(values, dict) or not self._has_required_values(values):
            return False
        self.values = dict(values)
        self.client_version = str(entry.get("client_version") or "")
        return True

    def _merge_values(self, values: Dict[str, int]) -> None:
        self.values.update(values)
        if "FramePositionX" in values and "FramePositionOffsetX" not in self.values:
            self.values["FramePositionOffsetX"] = int(values["FramePositionX"]) + 4
        if "FrameSizeX" in values and "FrameSizeOffsetX" not in self.values:
            self.values["FrameSizeOffsetX"] = int(values["FrameSizeX"]) + 4

    def _replace_values(self, values: Dict[str, int], version: str, source: str) -> None:
        self.values = {}
        self._merge_values(values)
        self.client_version = version
        self.source = source

    def _parse_payload(self, data: Dict[str, object]) -> tuple[Dict[str, int], str]:
        parsed: Dict[str, int] = {}
        flat_keys = (
            "FakeDataModelPointer",
            "FakeDataModelToDataModel",
            "DataModel_Workspace",
            "FramePositionX",
            "FramePositionOffsetX",
            "FrameSizeX",
            "FrameSizeOffsetX",
            "Instance_Name",
            "Instance_NameInner",
            "Instance_ClassDescriptor",
            "Instance_ClassDescriptorToClassName",
            "Instance_Children",
            "Instance_ChildrenEnd",
            "Instance_Parent",
        )
        for key in flat_keys:
            value = self._coerce_int(data.get(key))
            if value is not None:
                parsed[key] = value

        blocks = data.get("Offsets")
        if not isinstance(blocks, dict):
            blocks = data
        namespace_maps = {
            "FakeDataModel": {
                "Pointer": "FakeDataModelPointer",
                "RealDataModel": "FakeDataModelToDataModel",
            },
            "DataModel": {
                "Workspace": "DataModel_Workspace",
            },
            "GuiObject": {
                "Position": "FramePositionX",
                "Size": "FrameSizeX",
            },
            "Instance": {
                "NameContainer": "Instance_Name",
                "ClassDescriptor": "Instance_ClassDescriptor",
                "ClassName": "Instance_ClassDescriptorToClassName",
                "ChildrenStart": "Instance_Children",
                "ChildrenEnd": "Instance_ChildrenEnd",
                "Parent": "Instance_Parent",
            },
        }
        instance_raw: Dict[str, object] = {}
        for namespace, mapping in namespace_maps.items():
            values = blocks.get(namespace)
            if not isinstance(values, dict):
                continue
            if namespace == "Instance":
                for source_key in ("Name", "NameContainer"):
                    raw_value = values.get(source_key)
                    if raw_value is not None:
                        instance_raw[source_key] = raw_value
            for source_key, target_key in mapping.items():
                value = self._coerce_int(values.get(source_key))
                if value is not None:
                    parsed[target_key] = value
        self._resolve_instance_offsets(parsed, instance_raw)

        version = data.get("Roblox Version") or data.get("ClientVersion") or data.get("client_version") or ""
        return parsed, self.normalize_client_version(str(version))

    def _resolve_instance_offsets(
        self,
        parsed: Dict[str, int],
        instance_raw: Dict[str, object] | None = None,
    ) -> None:
        name_container = self._coerce_int((instance_raw or {}).get("NameContainer"))
        legacy_name = self._coerce_int((instance_raw or {}).get("Name"))
        if name_container is not None and name_container >= 0x10:
            parsed["Instance_Name"] = name_container
        elif legacy_name is not None and legacy_name >= 0x10:
            parsed["Instance_Name"] = legacy_name
        elif int(parsed.get("Instance_Name", 0)) < 0x10:
            parsed.pop("Instance_Name", None)
        name_inner = self._coerce_int((instance_raw or {}).get("Name"))
        if name_inner is not None and name_inner > 0:
            parsed["Instance_NameInner"] = name_inner

    def _coerce_int(self, value: object) -> Optional[int]:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value) if value.is_integer() else None
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                return int(raw, 0)
            except ValueError:
                try:
                    return int(raw, 10)
                except ValueError:
                    return None
        return None

    def _has_required_values(self, values: Dict[str, int]) -> bool:
        if not all(int(values.get(key, 0)) > 0 for key in self.REQUIRED_OFFSETS):
            return False
        return int(values.get("Instance_Name", 0)) >= 0x10

    def has_required(self) -> bool:
        return self._has_required_values(self.values)

    def get(self, key: str, default: int = 0) -> int:
        return int(self.values.get(key, default))

    @classmethod
    def normalize_client_version(cls, value: object) -> str:
        match = CLIENT_VERSION_RE.search(str(value or ""))
        return match.group(0).lower() if match else ""

    @classmethod
    def client_version_from_path(cls, path: str | Path | None) -> str:
        return cls.normalize_client_version(path)
