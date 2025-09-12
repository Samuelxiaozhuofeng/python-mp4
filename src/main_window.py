"""
主窗口模块
实现应用程序的主界面和布局
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QSplitter, QFrame, QLabel, QMenuBar, QToolBar, 
                               QStatusBar, QMessageBox, QFileDialog, QDockWidget,
                               QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QKeySequence, QAction

import os
from config import config
from favorites import ensure_favorites_dock, refresh_favorites_list, save_current_to_favorites

# 导入视频播放器组件 - 这个类现在在video_player.py中定义

# 旧的组件类已被新的 SubtitleExerciseWidget 替代

class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.subtitle_parser = None  # 字幕解析器
        self.current_exercise_index = 0  # 当前练习索引
        self.current_exercise_subtitle = None  # 当前练习字幕
        self.exercise_mode = False  # 练习模式标志
        self.generated_exercises = []  # AI生成的练习数据
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_toolbar()
        self.setup_status_bar()
        self.load_settings()
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("ListenFill AI - 个性化视频听力填空练习")
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局 - 上下分布
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 上方区域：视频播放器
        video_container = QFrame()
        video_container.setFrameStyle(QFrame.StyledPanel)
        video_container.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border: 2px solid #333333;
                border-radius: 8px;
            }
        """)
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        # 视频区标题
        video_title = QLabel("🎬 视频区")
        video_title.setAlignment(Qt.AlignCenter)
        video_title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 20px;
            }
        """)
        video_layout.addWidget(video_title)
        
        # 视频播放器
        from video_player import VideoPlayerWidget
        self.video_widget = VideoPlayerWidget()
        self.video_widget.video_loaded.connect(self.on_video_loaded)
        self.video_widget.position_changed.connect(self.on_position_changed)
        self.video_widget.playback_state_changed.connect(self.on_playback_state_changed)
        video_layout.addWidget(self.video_widget)
        
        # 设置视频区域占主要空间
        video_container.setMinimumHeight(400)
        main_layout.addWidget(video_container, 3)  # 权重为3
        
        # 下方区域：字幕交互区
        from exercise_widget import SubtitleExerciseWidget
        self.exercise_widget = SubtitleExerciseWidget()
        self.exercise_widget.exercise_completed.connect(self.on_exercise_completed)
        self.exercise_widget.next_exercise_requested.connect(self.on_next_exercise_requested)
        self.exercise_widget.hint_requested.connect(self.on_hint_requested)
        self.exercise_widget.show_answer_requested.connect(self.on_show_answer_requested)
        self.exercise_widget.replay_requested.connect(self.on_replay_requested)
        
        # 设置字幕交互区域 - 优化空间分配
        self.exercise_widget.setMinimumHeight(320)  # 增加最小高度以更好显示完整句子
        main_layout.addWidget(self.exercise_widget, 1.2)  # 增加权重，给练习区更多空间
    
    def _ensure_min_blanks(self, exercises):
        """确保每个AI练习至少包含一个挖空；若缺失则自动生成。"""
        import re, random
        for item in exercises or []:
            blanks = item.get('blanks') or []
            text = item.get('original_text') or ''
            if blanks:
                continue
            words = text.split()
            if not words:
                continue
            cleaned = [re.sub(r'^[\W_]+|[\W_]+$', '', w) for w in words]
            stopwords = {
                'the','a','an','is','are','am','was','were','be','been','being','and','or','but','to','of','in','on','at','for','from','by','with','as','that','this','these','those','it','its','he','she','they','we','you','i','me','him','her','them','us','your','our','their','my'
            }
            candidates = [i for i, w in enumerate(cleaned) if len(w) >= 3 and w.lower() not in stopwords]
            if not candidates:
                candidates = [i for i, w in enumerate(cleaned) if len(w) >= 1]
            pos = random.choice(candidates)
            ans = cleaned[pos]
            if not ans:
                continue
            item['blanks'] = [{
                'position': pos,
                'answer': ans,
                'hint': f"{len(ans)} letters",
                'difficulty': 'medium'
            }]

    def _ensure_exercise_has_blank(self, exercise_data):
        """确保单条练习至少包含一个挖空（显示前的双保险）。"""
        import re, random
        if not exercise_data:
            return exercise_data
        blanks = exercise_data.get('blanks') or []
        if blanks:
            return exercise_data
        text = exercise_data.get('original_text') or ''
        words = text.split()
        if not words:
            return exercise_data
        cleaned = [re.sub(r'^[\W_]+|[\W_]+$', '', w) for w in words]
        candidates = [i for i, w in enumerate(cleaned) if len(w) >= 3]
        if not candidates:
            candidates = [i for i, w in enumerate(cleaned) if len(w) >= 1]
        pos = random.choice(candidates)
        ans = cleaned[pos]
        if ans:
            exercise_data['blanks'] = [{
                'position': pos,
                'answer': ans,
                'hint': f"{len(ans)} letters",
                'difficulty': 'medium'
            }]
        return exercise_data

    def setup_menu_bar(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        # 导入视频和字幕
        import_action = QAction("导入视频文件(&I)", self)
        import_action.setShortcut(QKeySequence.Open)
        import_action.setStatusTip("选择MP4视频文件")
        import_action.triggered.connect(self.import_files)
        file_menu.addAction(import_action)
        
        # 单独导入字幕
        import_subtitle_action = QAction("导入字幕文件(&S)", self)
        import_subtitle_action.setShortcut(QKeySequence("Ctrl+S"))
        import_subtitle_action.setStatusTip("导入SRT字幕文件")
        import_subtitle_action.triggered.connect(self.import_subtitle)
        file_menu.addAction(import_subtitle_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip("退出应用程序")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")
        
        # AI服务配置
        ai_config_action = QAction("AI服务配置(&A)", self)
        ai_config_action.setStatusTip("配置AI服务API密钥和模型")
        ai_config_action.triggered.connect(self.show_ai_config)
        settings_menu.addAction(ai_config_action)
        
        # 练习配置
        exercise_config_action = QAction("练习配置(&E)", self)
        exercise_config_action.setStatusTip("配置练习难度和挖空选项")
        exercise_config_action.triggered.connect(self.show_exercise_config)
        settings_menu.addAction(exercise_config_action)
        
        settings_menu.addSeparator()
        
        # 开始练习
        start_exercise_action = QAction("开始练习(&P)", self)
        start_exercise_action.setShortcut(QKeySequence("F5"))
        start_exercise_action.setStatusTip("开始听力填空练习")
        start_exercise_action.triggered.connect(self.start_exercise_mode)
        settings_menu.addAction(start_exercise_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        # 关于
        about_action = QAction("关于(&A)", self)
        about_action.setStatusTip("关于ListenFill AI")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # 收藏菜单
        fav_menu = menubar.addMenu("收藏(&C)")

        open_fav_action = QAction("打开收藏面板(&O)", self)
        open_fav_action.setStatusTip("显示右侧收藏列表")
        open_fav_action.triggered.connect(lambda: ensure_favorites_dock(self))
        fav_menu.addAction(open_fav_action)

        save_fav_action = QAction("保存当前(&S)", self)
        save_fav_action.setStatusTip("保存当前视频/字幕/练习到收藏")
        save_fav_action.triggered.connect(lambda: save_current_to_favorites(self))
        fav_menu.addAction(save_fav_action)

        refresh_fav_action = QAction("刷新列表(&R)", self)
        refresh_fav_action.setStatusTip("刷新收藏列表")
        refresh_fav_action.triggered.connect(lambda: refresh_favorites_list(self))
        fav_menu.addAction(refresh_fav_action)
    
    def setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        # 导入文件按钮
        import_action = QAction("导入文件", self)
        import_action.setStatusTip("导入视频和字幕文件")
        import_action.triggered.connect(self.import_files)
        toolbar.addAction(import_action)
        
        toolbar.addSeparator()
        
        # AI配置按钮
        ai_config_action = QAction("AI配置", self)
        ai_config_action.setStatusTip("配置AI服务")
        ai_config_action.triggered.connect(self.show_ai_config)
        toolbar.addAction(ai_config_action)
        
        # 练习配置按钮
        exercise_config_action = QAction("练习配置", self)
        exercise_config_action.setStatusTip("配置练习选项")
        exercise_config_action.triggered.connect(self.show_exercise_config)
        toolbar.addAction(exercise_config_action)
    
    def setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 请导入视频和字幕文件开始练习")
    
    def load_settings(self):
        """加载设置"""
        # 从配置中加载窗口大小
        width = config.get('ui.window_width', 1200)
        height = config.get('ui.window_height', 800)
        self.resize(width, height)
        
        # 居中显示窗口
        self.center_window()
    
    def center_window(self):
        """将窗口居中显示"""
        screen = self.screen().availableGeometry()
        window = self.frameGeometry()
        window.moveCenter(screen.center())
        self.move(window.topLeft())
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 保存窗口大小到配置
        config.set('ui.window_width', self.width())
        config.set('ui.window_height', self.height())
        config.save_config()
        
        event.accept()
    
    # 菜单和工具栏事件处理方法
    def import_files(self):
        """导入文件"""
        # 选择视频文件
        video_file, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;所有文件 (*)"
        )
        
        if not video_file:
            return
        
        # 加载视频
        if self.video_widget.load_video(video_file):
            self.status_bar.showMessage(f"视频已加载: {os.path.basename(video_file)}")
            
            # 询问是否导入字幕
            reply = QMessageBox.question(
                self, 
                "导入字幕", 
                "视频加载成功！\n\n是否要导入字幕文件？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.import_subtitle()
        else:
            self.status_bar.showMessage("视频加载失败")
    
    def import_subtitle(self):
        """导入字幕文件"""
        from subtitle_import_dialog import SubtitleImportDialog
        
        # 获取视频时长
        video_duration = self.video_widget.get_duration()
        
        dialog = SubtitleImportDialog(self, video_duration)
        dialog.subtitle_loaded.connect(self.on_subtitle_loaded)
        
        # 如果视频正在播放，传递当前时间给对话框
        if self.video_widget.is_playing():
            current_time = self.video_widget.get_current_position()
            dialog.set_current_time(current_time)
        
        dialog.exec()
    
    def on_subtitle_loaded(self, subtitle_parser):
        """字幕加载完成回调"""
        print(f"[DEBUG] on_subtitle_loaded 被调用，字幕数量: {len(subtitle_parser.subtitles)}")
        
        # 保存字幕解析器引用
        self.subtitle_parser = subtitle_parser

        # 如果库中已保存过该视频+字幕的AI练习，则自动加载，避免重复生成
        try:
            from library import LibraryManager
            if getattr(self, 'library', None) is None:
                self.library = LibraryManager()
            video_path = getattr(self.video_widget, 'current_video_file', None)
            sub_path = getattr(self.subtitle_parser, 'current_file', None)
            if video_path and sub_path:
                import os
                vabs = os.path.abspath(video_path)
                sabs = os.path.abspath(sub_path)
                for e in self.library.get_entries():
                    if os.path.abspath(e.video_path) == vabs and os.path.abspath(e.subtitle_path) == sabs:
                        if e.exercises:
                            self.generated_exercises = e.exercises
                            self.status_bar.showMessage("已从收藏加载AI练习，无需重新生成")
                        break
        except Exception:
            # 忽略加载失败，保持正常流程
            pass
        
        # 在练习组件中显示字幕加载成功的提示
        print("[DEBUG] 准备调用 show_subtitle_loaded_state")
        self.show_subtitle_loaded_state()
        
        # 强制刷新界面
        self.exercise_widget.update()
        self.exercise_widget.repaint()
        self.update()
        
        self.status_bar.showMessage(f"字幕已加载: {len(subtitle_parser.subtitles)} 条")
        
        # 注意：我们把 QMessageBox 移到最后，因为它是阻塞的
        print("[DEBUG] 准备显示成功对话框")
        QMessageBox.information(self, "成功", 
                               f"字幕导入成功！\n\n"
                               f"共导入 {len(subtitle_parser.subtitles)} 条字幕\n"
                               f"时间偏移: {subtitle_parser.get_time_offset()/1000:.1f} 秒\n\n"
                               f"现在可以开始练习了！")
        print("[DEBUG] 成功对话框已显示")
    
    def show_subtitle_loaded_state(self):
        """显示字幕加载成功状态"""
        print("[DEBUG] show_subtitle_loaded_state 被调用")
        
        if not self.subtitle_parser:
            print("[DEBUG] subtitle_parser 为空，返回")
            return
        
        if not hasattr(self, 'exercise_widget') or not self.exercise_widget:
            print("[DEBUG] exercise_widget 不存在，返回")
            return
            
        print(f"[DEBUG] 字幕数量: {len(self.subtitle_parser.subtitles)}")
        
        # 创建临时的显示数据
        display_data = {
            'original_text': f"✅ 字幕已成功加载！\n\n共 {len(self.subtitle_parser.subtitles)} 条字幕\n\n请点击菜单 '设置' → '练习配置' 生成AI练习，\n或按 F5 开始练习模式",
            'blanks': [],  # 没有挖空
            'current': 0,
            'total': len(self.subtitle_parser.subtitles)
        }
        
        print(f"[DEBUG] 准备显示数据: {display_data}")
        
        try:
            # 显示到练习组件
            self.exercise_widget.show_subtitle_loaded(display_data)
            print("[DEBUG] 成功调用 exercise_widget.show_subtitle_loaded")
        except Exception as e:
            print(f"[DEBUG] 调用 show_subtitle_loaded 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def show_ai_config(self):
        """显示AI配置对话框"""
        from ai_config_dialog import AIConfigDialog
        dialog = AIConfigDialog(self)
        dialog.exec()
    
    def show_exercise_config(self):
        """显示练习配置对话框"""
        if not self.subtitle_parser or not self.subtitle_parser.subtitles:
            QMessageBox.warning(self, "警告", "请先导入字幕文件")
            return
        
        from exercise_config_dialog import ExerciseConfigDialog
        dialog = ExerciseConfigDialog(self, self.subtitle_parser.subtitles)
        dialog.exercises_generated.connect(self.on_exercises_generated)
        dialog.exec()
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于ListenFill AI", 
                         "ListenFill AI v1.0\n\n"
                         "个性化视频听力填空练习应用\n"
                         "基于AI技术的智能挖空生成\n\n"
                         "开发中...")
    
    # 视频播放器事件处理
    def on_video_loaded(self, video_path):
        """视频加载完成回调"""
        video_name = os.path.basename(video_path)
        self.setWindowTitle(f"ListenFill AI - {video_name}")
        self.status_bar.showMessage(f"已加载: {video_name}")
    
    def on_position_changed(self, position):
        """播放位置改变回调"""
        # 在练习模式下，检查是否需要暂停
        if hasattr(self, 'current_exercise_subtitle') and self.current_exercise_subtitle:
            subtitle_end_time = (self.current_exercise_subtitle.end_time + 
                               self.subtitle_parser.get_time_offset())
            
            # 如果播放到字幕结束时间，自动暂停
            if position >= subtitle_end_time:
                self.video_widget.media_player.pause()
                self.show_current_exercise()
    
    def on_playback_state_changed(self, is_playing):
        """播放状态改变回调"""
        # 可以在这里添加播放状态相关的逻辑
        pass
    
    def on_exercise_completed(self):
        """练习完成回调"""
        self.status_bar.showMessage("练习完成！")
    
    def on_next_exercise_requested(self):
        """请求下一个练习回调"""
        self.play_next_subtitle()
    
    def on_hint_requested(self):
        """请求提示回调"""
        self.status_bar.showMessage("提示功能将在AI集成后实现")
    
    def on_show_answer_requested(self):
        """请求显示答案回调"""
        self.status_bar.showMessage("已显示答案")
    
    def on_replay_requested(self):
        """重播当前例句"""
        if self.current_exercise_subtitle and self.subtitle_parser:
            start_time = self.current_exercise_subtitle.start_time + self.subtitle_parser.get_time_offset()
            self.video_widget.set_position(start_time)
            self.video_widget.media_player.play()
            self.status_bar.showMessage("重播当前例句")
        else:
            self.status_bar.showMessage("暂无可重播的例句")

    # 练习逻辑方法
    def start_exercise_mode(self):
        """开始练习模式"""
        if not self.subtitle_parser or not self.subtitle_parser.subtitles:
            QMessageBox.warning(self, "警告", "请先导入字幕文件")
            return
        
        # 检查是否已生成练习
        if not self.generated_exercises:
            reply = QMessageBox.question(
                self,
                "生成练习",
                "尚未生成AI练习。是否现在生成？\n\n"
                "点击'是'将打开练习配置对话框",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.show_exercise_config()
            return
        
        # 开始练习模式
        self.current_exercise_index = 0
        self.exercise_mode = True
        self.play_current_subtitle()
    
    def play_current_subtitle(self):
        """播放当前字幕"""
        if not self.subtitle_parser or self.current_exercise_index >= len(self.subtitle_parser.subtitles):
            return
        
        subtitle = self.subtitle_parser.subtitles[self.current_exercise_index]
        self.current_exercise_subtitle = subtitle
        
        # 定位到字幕开始时间
        start_time = subtitle.start_time + self.subtitle_parser.get_time_offset()
        self.video_widget.set_position(start_time)
        self.video_widget.media_player.play()
    
    def show_current_exercise(self):
        """显示当前练习"""
        if not self.current_exercise_subtitle:
            print("[DEBUG] show_current_exercise: 没有当前练习字幕")
            return
        
        # 使用AI生成的练习数据或备用方案
        if self.generated_exercises and self.current_exercise_index < len(self.generated_exercises):
            exercise_data = self.generated_exercises[self.current_exercise_index]
            print(f"[DEBUG] 使用AI生成的练习数据: {exercise_data}")
        else:
            # 备用方案：创建模拟练习数据
            exercise_data = self.create_mock_exercise(self.current_exercise_subtitle)
            print(f"[DEBUG] 使用备用练习数据: {exercise_data}")
        
        print(f"[DEBUG] 当前练习索引: {self.current_exercise_index}")
        print(f"[DEBUG] 生成的练习总数: {len(self.generated_exercises) if self.generated_exercises else 0}")
        
        self.exercise_widget.show_exercise(exercise_data)
    
    def create_mock_exercise(self, subtitle):
        """创建模拟练习数据 (临时方法)"""
        import random
        
        words = subtitle.text.split()
        if len(words) < 2:
            return {
                'original_text': subtitle.text,
                'blanks': [],
                'current': self.current_exercise_index + 1,
                'total': len(self.subtitle_parser.subtitles)
            }
        
        # 随机选择1-2个词进行挖空
        num_blanks = min(2, len(words) // 3 + 1)
        blank_positions = random.sample(range(len(words)), min(num_blanks, len(words)))
        
        blanks = []
        for pos in sorted(blank_positions):
            blanks.append({
                'position': pos,
                'answer': words[pos],
                'hint': f"{len(words[pos])} letters"
            })
        
        return {
            'original_text': subtitle.text,
            'blanks': blanks,
            'current': self.current_exercise_index + 1,
            'total': len(self.subtitle_parser.subtitles)
        }
    
    def play_next_subtitle(self):
        """播放下一句字幕"""
        self.current_exercise_index += 1
        
        # 检查练习数据的长度
        max_exercises = len(self.generated_exercises) if self.generated_exercises else len(self.subtitle_parser.subtitles)
        
        if self.current_exercise_index >= max_exercises:
            # 练习结束
            QMessageBox.information(self, "完成", "🎉 恭喜！所有练习已完成！\n\n"
                                   f"共完成 {max_exercises} 个练习")
            self.exercise_widget.show_waiting_state()
            self.current_exercise_index = 0
            self.exercise_mode = False
            return
        
        self.play_current_subtitle()
    
    def on_exercises_generated(self, exercises):
        """AI练习生成完成回调"""
        # 确保每个练习至少有一个挖空（修正AI漏挖）
        self._ensure_min_blanks(exercises)
        self.generated_exercises = exercises
        self.status_bar.showMessage(f"AI练习生成完成: {len(exercises)} 个练习")
        
        # 询问是否立即开始练习
        reply = QMessageBox.question(
            self,
            "练习已生成",
            f"AI练习生成完成！\n\n"
            f"共生成 {len(exercises)} 个个性化练习\n"
            f"是否立即开始练习？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.current_exercise_index = 0
            self.exercise_mode = True
            self.play_current_subtitle()
