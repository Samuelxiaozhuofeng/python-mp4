from __future__ import annotations

from typing import Optional, List, Dict
from PySide6.QtWidgets import QDockWidget, QListWidget, QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt
import os

from library import LibraryManager


def ensure_favorites_dock(mw):
    """确保收藏面板已创建并显示"""
    if getattr(mw, '_fav_list', None) is None:
        setup_favorites_dock(mw)
    refresh_favorites_list(mw)


def setup_favorites_dock(mw):
    """创建收藏列表侧边栏"""
    # 初始化库管理器
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()

    dock = QDockWidget("收藏", mw)
    dock.setObjectName("FavoritesDock")
    dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
    fav_list = QListWidget(dock)
    fav_list.itemDoubleClicked.connect(lambda item: on_favorite_activated(mw, item))
    dock.setWidget(fav_list)
    mw.addDockWidget(Qt.RightDockWidgetArea, dock)
    mw._fav_list = fav_list
    refresh_favorites_list(mw)


def refresh_favorites_list(mw):
    fav_list = getattr(mw, '_fav_list', None)
    if fav_list is None:
        return
    # 确保库管理器存在
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()
    entries = mw.library.get_entries()
    fav_list.clear()
    for e in entries:
        video_name = os.path.basename(e.video_path)
        subtitle_name = os.path.basename(e.subtitle_path)
        tag = "(含练习)" if e.exercises else ""
        item = QListWidgetItem(f"{video_name} | {subtitle_name} {tag}")
        item.setData(Qt.UserRole, e.id)
        fav_list.addItem(item)


def save_current_to_favorites(mw):
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()
    video_file = getattr(mw.video_widget, 'current_video_file', None)
    if not video_file:
        QMessageBox.information(mw, "提示", "请先导入并加载视频")
        return
    if not mw.subtitle_parser or not getattr(mw.subtitle_parser, 'current_file', None):
        QMessageBox.information(mw, "提示", "请先导入字幕")
        return
    mw.library.add_or_update_entry(
        video_path=video_file,
        subtitle_path=mw.subtitle_parser.current_file,
        time_offset_ms=mw.subtitle_parser.get_time_offset(),
        exercises=mw.generated_exercises if mw.generated_exercises else None
    )
    mw.status_bar.showMessage("已保存到收藏")
    refresh_favorites_list(mw)


def on_favorite_activated(mw, item: QListWidgetItem):
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()
    entry_id = item.data(Qt.UserRole)
    entry = mw.library.get_entry(entry_id)
    if not entry:
        return
    if not os.path.exists(entry.video_path):
        QMessageBox.warning(mw, "警告", f"视频文件不存在:\n{entry.video_path}")
        return
    if not os.path.exists(entry.subtitle_path):
        QMessageBox.warning(mw, "警告", f"字幕文件不存在:\n{entry.subtitle_path}")
        return

    # 加载视频
    if mw.video_widget.load_video(entry.video_path):
        mw.status_bar.showMessage(f"视频已加载: {os.path.basename(entry.video_path)}")
    else:
        QMessageBox.warning(mw, "错误", "视频加载失败")
        return

    # 加载字幕
    from subtitle_parser import SubtitleParser
    parser = SubtitleParser()
    if not parser.load_srt_file(entry.subtitle_path):
        QMessageBox.warning(mw, "错误", "字幕加载失败")
        return
    parser.set_time_offset(getattr(entry, 'time_offset_ms', 0) or 0)
    mw.on_subtitle_loaded(parser)

    # 加载练习
    if entry.exercises:
        mw.generated_exercises = entry.exercises
        mw.status_bar.showMessage("已加载收藏中的AI练习结果")
    else:
        mw.status_bar.showMessage("收藏无练习结果，可在练习配置中生成")

