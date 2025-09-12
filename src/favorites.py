from __future__ import annotations

from typing import Optional, List, Dict
from PySide6.QtWidgets import QDockWidget, QListWidget, QListWidgetItem, QMessageBox, QMenu
from PySide6.QtCore import Qt
import os

from library import LibraryManager
from config import config


def ensure_favorites_dock(mw):
    """Ensure favorites panel is created and displayed"""
    if getattr(mw, '_fav_list', None) is None:
        setup_favorites_dock(mw)
    refresh_favorites_list(mw)


def setup_favorites_dock(mw):
    """Create favorites list sidebar"""
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()

    dock = QDockWidget("Favorites", mw)
    dock.setObjectName("FavoritesDock")
    dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

    fav_list = QListWidget(dock)
    fav_list.itemDoubleClicked.connect(lambda item: open_favorite_and_resume(mw, item))
    fav_list.setContextMenuPolicy(Qt.CustomContextMenu)
    fav_list.customContextMenuRequested.connect(lambda pos: on_favorites_context_menu(mw, fav_list, pos))

    dock.setWidget(fav_list)
    mw.addDockWidget(Qt.RightDockWidgetArea, dock)
    mw._fav_list = fav_list
    refresh_favorites_list(mw)


def refresh_favorites_list(mw):
    fav_list = getattr(mw, '_fav_list', None)
    if fav_list is None:
        return
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()

    entries = mw.library.get_entries()
    fav_list.clear()
    for e in entries:
        video_name = os.path.basename(e.video_path)
        subtitle_name = os.path.basename(e.subtitle_path)
        tag = "(with exercises)" if e.exercises else ""
        item = QListWidgetItem(f"{video_name} | {subtitle_name} {tag}")
        item.setData(Qt.UserRole, e.id)
        fav_list.addItem(item)


def save_current_to_favorites(mw):
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()

    video_file = getattr(mw.video_widget, 'current_video_file', None)
    if not video_file:
        QMessageBox.information(mw, "Tip", "Please import and load video first")
        return
    if not mw.subtitle_parser or not getattr(mw.subtitle_parser, 'current_file', None):
        QMessageBox.information(mw, "Tip", "Please import subtitles first")
        return

    # Record current playback progress and corresponding exercise index
    try:
        resume_pos = mw.video_widget.get_current_position() if hasattr(mw, 'video_widget') else 0
    except Exception:
        resume_pos = 0

    resume_index = 0
    try:
        if mw.subtitle_parser and resume_pos is not None:
            sub = mw.subtitle_parser.get_subtitle_at_time(resume_pos)
            if sub:
                for i, s in enumerate(mw.subtitle_parser.subtitles):
                    if s.index == sub.index:
                        resume_index = i
                        break
        if resume_index == 0 and getattr(mw, 'current_exercise_index', None) is not None:
            resume_index = int(mw.current_exercise_index)
    except Exception:
        pass

    entry = mw.library.add_or_update_entry(
        video_path=video_file,
        subtitle_path=mw.subtitle_parser.current_file,
        time_offset_ms=mw.subtitle_parser.get_time_offset(),
        exercises=mw.generated_exercises if mw.generated_exercises else None,
        exercise_config=config.get_exercise_config(),
        resume_position_ms=resume_pos or 0,
        resume_exercise_index=resume_index or 0,
    )
    # 记录当前收藏条目的ID，供自动保存进度使用
    try:
        mw.current_library_entry_id = entry.id
    except Exception:
        pass
    mw.status_bar.showMessage("Saved to favorites")
    refresh_favorites_list(mw)


def on_favorites_context_menu(mw, list_widget: QListWidget, pos):
    """Favorites list right-click menu: open/delete"""
    item = list_widget.itemAt(pos)
    if item is None:
        return
    entry_id = item.data(Qt.UserRole)

    menu = QMenu(list_widget)
    open_action = menu.addAction("Open")
    delete_action = menu.addAction("Delete")
    action = menu.exec(list_widget.mapToGlobal(pos))

    if action == open_action:
        open_favorite_and_resume(mw, item)
    elif action == delete_action:
        on_delete_favorite(mw, entry_id)


def on_delete_favorite(mw, entry_id: str):
    """Delete favorite item"""
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()
    reply = QMessageBox.question(
        mw,
        "Delete Confirmation",
        "Are you sure you want to delete this favorite? This operation will not delete your video/subtitle files.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        return

    ok = mw.library.remove_entry(entry_id)
    if ok:
        mw.status_bar.showMessage("Favorite deleted")
        refresh_favorites_list(mw)
    else:
        QMessageBox.warning(mw, "Tip", "Delete failed: favorite not found")


def open_favorite_and_resume(mw, item: QListWidgetItem):
    """Open favorite and restore to saved progress, then enter sentence exercise mode"""
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()
    entry_id = item.data(Qt.UserRole)
    entry = mw.library.get_entry(entry_id)
    if not entry:
        return
    if not os.path.exists(entry.video_path):
        QMessageBox.warning(mw, "Warning", f"Video file does not exist\n{entry.video_path}")
        return
    if not os.path.exists(entry.subtitle_path):
        QMessageBox.warning(mw, "Warning", f"Subtitle file does not exist\n{entry.subtitle_path}")
        return

    # Load video
    if not mw.video_widget.load_video(entry.video_path):
        QMessageBox.warning(mw, "Error", "Video loading failed")
        return

    # Load subtitles
    from subtitle_parser import SubtitleParser
    parser = SubtitleParser()
    if not parser.load_srt_file(entry.subtitle_path):
        QMessageBox.warning(mw, "Error", "Subtitle loading failed")
        return
    parser.set_time_offset(getattr(entry, 'time_offset_ms', 0) or 0)
    mw.on_subtitle_loaded(parser)

    # Load exercises (if saved)
    if entry.exercises:
        mw.generated_exercises = entry.exercises
        mw.status_bar.showMessage("Loaded AI exercise results from favorites")
    else:
        mw.status_bar.showMessage("No exercise results in favorites, can generate in exercise configuration")

    # Restore progress and enter exercise mode (play one sentence and automatically pause for fill-in-the-blank)
    try:
        idx = getattr(entry, 'resume_exercise_index', 0) or 0
        if not idx:
            resume_pos = getattr(entry, 'resume_position_ms', 0) or 0
            if resume_pos and mw.subtitle_parser:
                sub = mw.subtitle_parser.get_subtitle_at_time(resume_pos)
                if sub:
                    for i, s in enumerate(mw.subtitle_parser.subtitles):
                        if s.index == sub.index:
                            idx = i
                            break

        # Set index and start playing current sentence
        if mw.subtitle_parser and 0 <= idx < len(mw.subtitle_parser.subtitles):
            mw.current_exercise_index = idx
        else:
            mw.current_exercise_index = 0
        mw.exercise_mode = True
        mw.play_current_subtitle()
        mw.status_bar.showMessage("Restored to last exercise progress and entered exercise mode")
    except Exception:
        pass

    # Mark current open favorite entry ID, enable auto-save mechanism
    try:
        mw.current_library_entry_id = entry.id
    except Exception:
        pass

