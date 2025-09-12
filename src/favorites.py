from __future__ import annotations

from typing import Optional, List, Dict
from PySide6.QtWidgets import QDockWidget, QListWidget, QListWidgetItem, QMessageBox, QMenu
from PySide6.QtCore import Qt
import os

from library import LibraryManager
from config import config


def ensure_favorites_dock(mw):
    """确保收藏面板已创建并显示"""
    if getattr(mw, '_fav_list', None) is None:
        setup_favorites_dock(mw)
    refresh_favorites_list(mw)


def setup_favorites_dock(mw):
    """创建收藏列表侧边栏"""
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()

    dock = QDockWidget("收藏", mw)
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

    # 记录当前播放进度与对应练习索引
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

    mw.library.add_or_update_entry(
        video_path=video_file,
        subtitle_path=mw.subtitle_parser.current_file,
        time_offset_ms=mw.subtitle_parser.get_time_offset(),
        exercises=mw.generated_exercises if mw.generated_exercises else None,
        exercise_config=config.get_exercise_config(),
        resume_position_ms=resume_pos or 0,
        resume_exercise_index=resume_index or 0,
    )
    mw.status_bar.showMessage("已保存到收藏")
    refresh_favorites_list(mw)


def on_favorites_context_menu(mw, list_widget: QListWidget, pos):
    """收藏列表右键菜单：打开/删除"""
    item = list_widget.itemAt(pos)
    if item is None:
        return
    entry_id = item.data(Qt.UserRole)

    menu = QMenu(list_widget)
    open_action = menu.addAction("打开")
    delete_action = menu.addAction("删除")
    action = menu.exec(list_widget.mapToGlobal(pos))

    if action == open_action:
        open_favorite_and_resume(mw, item)
    elif action == delete_action:
        on_delete_favorite(mw, entry_id)


def on_delete_favorite(mw, entry_id: str):
    """删除收藏项"""
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()
    reply = QMessageBox.question(
        mw,
        "删除确认",
        "确定要删除该收藏吗？此操作不会删除您的视频/字幕文件。",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        return

    ok = mw.library.remove_entry(entry_id)
    if ok:
        mw.status_bar.showMessage("已删除收藏")
        refresh_favorites_list(mw)
    else:
        QMessageBox.warning(mw, "提示", "删除失败：未找到该收藏")


def open_favorite_and_resume(mw, item: QListWidgetItem):
    """打开收藏，并恢复到保存的进度后进入句子练习模式"""
    if getattr(mw, 'library', None) is None:
        mw.library = LibraryManager()
    entry_id = item.data(Qt.UserRole)
    entry = mw.library.get_entry(entry_id)
    if not entry:
        return
    if not os.path.exists(entry.video_path):
        QMessageBox.warning(mw, "警告", f"视频文件不存在\n{entry.video_path}")
        return
    if not os.path.exists(entry.subtitle_path):
        QMessageBox.warning(mw, "警告", f"字幕文件不存在\n{entry.subtitle_path}")
        return

    # 加载视频
    if not mw.video_widget.load_video(entry.video_path):
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

    # 加载练习（如已保存）
    if entry.exercises:
        mw.generated_exercises = entry.exercises
        mw.status_bar.showMessage("已加载收藏中的AI练习结果")
    else:
        mw.status_bar.showMessage("收藏无练习结果，可在练习配置中生成")

    # 恢复进度并进入练习模式（播放一句自动暂停填空）
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

        # 设定索引并开始当前句子的播放
        if mw.subtitle_parser and 0 <= idx < len(mw.subtitle_parser.subtitles):
            mw.current_exercise_index = idx
        else:
            mw.current_exercise_index = 0
        mw.exercise_mode = True
        mw.play_current_subtitle()
        mw.status_bar.showMessage("已恢复到上次练习进度，并进入练习模式")
    except Exception:
        pass

