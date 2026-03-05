import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class GuideProgress:
    """Persist guide progress and completion metadata."""

    def __init__(self, data_dir: Path):
        self.path = data_dir / "guide_progress.json"
        self.data: Dict[str, Any] = {
            "version": 1,
            "completed": {}
        }
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                self.data.update(payload)
        except Exception:
            # Keep defaults if loading fails
            pass

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def mark_completed(self, key: str, details: Optional[Dict[str, Any]] = None) -> None:
        if not key:
            return
        self.data.setdefault("completed", {})
        self.data["completed"][key] = {
            "timestamp": time.time(),
            "details": details or {}
        }
        self.save()

    def is_completed(self, key: str) -> bool:
        return bool(self.data.get("completed", {}).get(key))

    def get_details(self, key: str) -> Dict[str, Any]:
        return self.data.get("completed", {}).get(key, {}).get("details", {})
