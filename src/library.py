"""
本地收藏/库管理模块
负责保存与读取：视频路径、字幕路径、时间偏移、AI生成的练习结果等
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path


LIB_DIR = Path("data")
LIB_FILE = LIB_DIR / "library.json"


def _ensure_lib_file():
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    if not LIB_FILE.exists():
        with open(LIB_FILE, "w", encoding="utf-8") as f:
            json.dump({"entries": []}, f, ensure_ascii=False, indent=2)


@dataclass
class LibraryEntry:
    id: str
    video_path: str
    subtitle_path: str
    time_offset_ms: int = 0
    exercises: Optional[List[Dict]] = None
    exercise_config: Optional[Dict] = None
    created_at: float = 0.0
    updated_at: float = 0.0


class LibraryManager:
    """简单的JSON文件库管理器"""

    def __init__(self):
        _ensure_lib_file()
        self._data = self._read()

    def _read(self) -> Dict:
        try:
            with open(LIB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"entries": []}

    def _write(self):
        with open(LIB_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _make_id(self, video_path: str, subtitle_path: str) -> str:
        # 基于路径生成稳定ID（避免hash种子差异）
        key = f"{os.path.abspath(video_path)}|{os.path.abspath(subtitle_path)}".lower()
        # 简化为可读ID
        import hashlib
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def get_entries(self) -> List[LibraryEntry]:
        entries = []
        for e in self._data.get("entries", []):
            entries.append(LibraryEntry(**e))
        return entries

    def get_entry(self, entry_id: str) -> Optional[LibraryEntry]:
        for e in self._data.get("entries", []):
            if e.get("id") == entry_id:
                return LibraryEntry(**e)
        return None

    def add_or_update_entry(
        self,
        video_path: str,
        subtitle_path: str,
        time_offset_ms: int = 0,
        exercises: Optional[List[Dict]] = None,
        exercise_config: Optional[Dict] = None,
    ) -> LibraryEntry:
        eid = self._make_id(video_path, subtitle_path)
        now = time.time()

        # 查找是否存在
        found = None
        for e in self._data.get("entries", []):
            if e.get("id") == eid:
                found = e
                break

        entry_dict = {
            "id": eid,
            "video_path": os.path.abspath(video_path),
            "subtitle_path": os.path.abspath(subtitle_path),
            "time_offset_ms": int(time_offset_ms or 0),
            "exercises": exercises or (found.get("exercises") if found else None),
            "exercise_config": exercise_config or (found.get("exercise_config") if found else None),
            "created_at": found.get("created_at") if found else now,
            "updated_at": now,
        }

        if found:
            found.update(entry_dict)
        else:
            self._data.setdefault("entries", []).append(entry_dict)

        self._write()
        return LibraryEntry(**entry_dict)

    def update_exercises(self, entry_id: str, exercises: List[Dict], exercise_config: Optional[Dict] = None):
        for e in self._data.get("entries", []):
            if e.get("id") == entry_id:
                e["exercises"] = exercises
                if exercise_config is not None:
                    e["exercise_config"] = exercise_config
                e["updated_at"] = time.time()
                self._write()
                return

    def remove_entry(self, entry_id: str) -> bool:
        arr = self._data.get("entries", [])
        n = len(arr)
        self._data["entries"] = [e for e in arr if e.get("id") != entry_id]
        if len(self._data["entries"]) != n:
            self._write()
            return True
        return False

