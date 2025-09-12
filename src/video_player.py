"""
视频播放器模块
基于QMediaPlayer实现视频播放功能
"""
import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QSlider, QLabel, QFrame, QSizePolicy, QMessageBox,
                               QStyle, QFileDialog)
from PySide6.QtCore import Qt, QUrl, QTimer, Signal, QTime
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtGui import QKeySequence, QShortcut

class VideoControlWidget(QWidget):
    """视频控制面板"""
    
    # 定义信号
    play_pause_clicked = Signal()
    stop_clicked = Signal()
    position_changed = Signal(int)
    volume_changed = Signal(int)
    fullscreen_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 播放/暂停按钮
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setFixedSize(40, 30)
        self.play_button.setToolTip("播放/暂停 (空格键)")
        self.play_button.clicked.connect(self.play_pause_clicked.emit)
        layout.addWidget(self.play_button)
        
        # 停止按钮
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.setFixedSize(40, 30)
        self.stop_button.setToolTip("停止")
        self.stop_button.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.stop_button)
        
        # 时间标签
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMinimumWidth(80)
        layout.addWidget(self.time_label)
        
        # 进度条
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.position_changed.emit)
        self.position_slider.setToolTip("拖拽调整播放进度")
        layout.addWidget(self.position_slider)
        
        # 音量标签
        volume_label = QLabel("🔊")
        layout.addWidget(volume_label)
        
        # 音量滑块
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(80)
        self.volume_slider.setToolTip("调整音量")
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        layout.addWidget(self.volume_slider)
        
        # 全屏按钮
        self.fullscreen_button = QPushButton()
        self.fullscreen_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.fullscreen_button.setFixedSize(40, 30)
        self.fullscreen_button.setToolTip("全屏播放 (F11)")
        self.fullscreen_button.clicked.connect(self.fullscreen_requested.emit)
        layout.addWidget(self.fullscreen_button)
    
    def set_play_icon(self, is_playing):
        """设置播放/暂停图标"""
        if is_playing:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.play_button.setToolTip("暂停 (空格键)")
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.play_button.setToolTip("播放 (空格键)")
    
    def update_position(self, position, duration):
        """更新播放位置"""
        self.position_slider.setValue(position)
        
        # 更新时间显示
        current_time = QTime(0, 0, 0).addMSecs(position)
        total_time = QTime(0, 0, 0).addMSecs(duration)
        
        format_str = "mm:ss" if duration < 3600000 else "hh:mm:ss"
        time_text = f"{current_time.toString(format_str)} / {total_time.toString(format_str)}"
        self.time_label.setText(time_text)
    
    def update_duration(self, duration):
        """更新总时长"""
        self.position_slider.setRange(0, duration)

class VideoPlayerWidget(QFrame):
    """视频播放器组件"""
    
    # 定义信号
    video_loaded = Signal(str)  # 视频加载完成
    position_changed = Signal(int)  # 播放位置改变
    duration_changed = Signal(int)  # 时长改变
    playback_state_changed = Signal(bool)  # 播放状态改变
    
    def __init__(self):
        super().__init__()
        self.current_video_file = None
        self.target_position = None  # 目标播放位置
        self.setup_ui()
        self.setup_media_player()
        self.setup_shortcuts()
    
    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # 视频显示区域
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)
        
        # 控制面板
        self.control_widget = VideoControlWidget()
        self.control_widget.play_pause_clicked.connect(self.toggle_playback)
        self.control_widget.stop_clicked.connect(self.stop_playback)
        self.control_widget.position_changed.connect(self.set_position)
        self.control_widget.volume_changed.connect(self.set_volume)
        self.control_widget.fullscreen_requested.connect(self.toggle_fullscreen)
        layout.addWidget(self.control_widget)
        
        # 默认显示提示信息
        self.show_placeholder()
    
    def setup_media_player(self):
        """设置媒体播放器"""
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        # 连接信号
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_error_occurred)
        
        # 设置初始音量
        self.audio_output.setVolume(0.5)
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # 空格键播放/暂停
        play_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        play_shortcut.activated.connect(self.toggle_playback)
        
        # F11全屏
        fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        
        # 左右箭头快进快退
        forward_shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        forward_shortcut.activated.connect(lambda: self.skip_time(5000))
        
        backward_shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        backward_shortcut.activated.connect(lambda: self.skip_time(-5000))
    
    def show_placeholder(self):
        """显示占位符信息"""
        placeholder_layout = QVBoxLayout()
        placeholder_label = QLabel("🎬 视频播放器已就绪\n\n点击 '文件' → '导入视频和字幕' 开始")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 16px;
                background-color: #f0f0f0;
                border: 2px dashed #cccccc;
                border-radius: 10px;
                padding: 40px;
            }
        """)
        placeholder_layout.addWidget(placeholder_label)
        
        # 临时隐藏视频组件，显示占位符
        self.video_widget.hide()
        if not hasattr(self, 'placeholder_widget'):
            self.placeholder_widget = QWidget()
            self.placeholder_widget.setLayout(placeholder_layout)
            self.layout().insertWidget(0, self.placeholder_widget)
    
    def hide_placeholder(self):
        """隐藏占位符"""
        if hasattr(self, 'placeholder_widget'):
            self.placeholder_widget.hide()
        self.video_widget.show()
    
    def load_video(self, video_path):
        """加载视频文件"""
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "错误", f"视频文件不存在: {video_path}")
            return False
        
        try:
            self.current_video_file = video_path
            video_url = QUrl.fromLocalFile(os.path.abspath(video_path))
            self.media_player.setSource(video_url)
            self.hide_placeholder()
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载视频失败: {str(e)}")
            return False
    
    def toggle_playback(self):
        """切换播放/暂停状态"""
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def stop_playback(self):
        """停止播放"""
        self.media_player.stop()
    
    def set_position(self, position):
        """设置播放位置"""
        self.media_player.setPosition(position)
    
    def set_volume(self, volume):
        """设置音量 (0-100)"""
        self.audio_output.setVolume(volume / 100.0)
    
    def skip_time(self, milliseconds):
        """跳转时间 (毫秒)"""
        current_pos = self.media_player.position()
        new_pos = max(0, min(current_pos + milliseconds, self.media_player.duration()))
        self.set_position(new_pos)
    
    def play_segment(self, start_ms, end_ms):
        """播放指定时间段"""
        self.target_position = end_ms
        self.set_position(start_ms)
        self.media_player.play()
        
        # 设置定时器在指定时间停止
        if hasattr(self, 'segment_timer'):
            self.segment_timer.stop()
        
        self.segment_timer = QTimer()
        self.segment_timer.setSingleShot(True)
        self.segment_timer.timeout.connect(lambda: self.media_player.pause())
        self.segment_timer.start(end_ms - start_ms)
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        if self.video_widget.isFullScreen():
            self.video_widget.setFullScreen(False)
        else:
            self.video_widget.setFullScreen(True)
    
    # 媒体播放器事件处理
    def on_position_changed(self, position):
        """播放位置改变"""
        self.control_widget.update_position(position, self.media_player.duration())
        self.position_changed.emit(position)
        
        # 检查是否需要在目标位置停止
        if self.target_position and position >= self.target_position:
            self.media_player.pause()
            self.target_position = None
    
    def on_duration_changed(self, duration):
        """时长改变"""
        self.control_widget.update_duration(duration)
        self.duration_changed.emit(duration)
    
    def on_playback_state_changed(self, state):
        """播放状态改变"""
        is_playing = (state == QMediaPlayer.PlayingState)
        self.control_widget.set_play_icon(is_playing)
        self.playback_state_changed.emit(is_playing)
    
    def on_media_status_changed(self, status):
        """媒体状态改变"""
        if status == QMediaPlayer.LoadedMedia:
            # 视频加载完成
            if self.current_video_file:
                self.video_loaded.emit(self.current_video_file)
        elif status == QMediaPlayer.InvalidMedia:
            QMessageBox.warning(self, "警告", "无效的媒体文件")
    
    def on_error_occurred(self, error):
        """播放错误处理"""
        error_messages = {
            QMediaPlayer.NoError: "无错误",
            QMediaPlayer.ResourceError: "资源错误",
            QMediaPlayer.FormatError: "格式不支持",
            QMediaPlayer.NetworkError: "网络错误",
            QMediaPlayer.AccessDeniedError: "访问被拒绝"
        }
        
        error_msg = error_messages.get(error, f"未知错误 ({error})")
        QMessageBox.critical(self, "播放错误", f"视频播放出错: {error_msg}")
    
    def get_current_position(self):
        """获取当前播放位置 (毫秒)"""
        return self.media_player.position()
    
    def get_duration(self):
        """获取视频总时长 (毫秒)"""
        return self.media_player.duration()
    
    def is_playing(self):
        """检查是否正在播放"""
        return self.media_player.playbackState() == QMediaPlayer.PlayingState
