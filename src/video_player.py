"""
Video player module
Implements video playback functionality based on QMediaPlayer
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
    """Video control panel"""
    
    # Define signals
    play_pause_clicked = Signal()
    stop_clicked = Signal()
    position_changed = Signal(int)
    volume_changed = Signal(int)
    fullscreen_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Play/pause button
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setFixedSize(40, 30)
        self.play_button.setToolTip("Play/Pause (Space)")
        self.play_button.clicked.connect(self.play_pause_clicked.emit)
        layout.addWidget(self.play_button)
        
        # Stop button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.setFixedSize(40, 30)
        self.stop_button.setToolTip("Stop")
        self.stop_button.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.stop_button)
        
        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMinimumWidth(80)
        layout.addWidget(self.time_label)
        
        # Progress bar
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.position_changed.emit)
        self.position_slider.setToolTip("Drag to adjust playback progress")
        layout.addWidget(self.position_slider)
        
        # Volume label
        volume_label = QLabel("🔊")
        layout.addWidget(volume_label)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(80)
        self.volume_slider.setToolTip("Adjust volume")
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        layout.addWidget(self.volume_slider)
        
        # Fullscreen button
        self.fullscreen_button = QPushButton()
        self.fullscreen_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.fullscreen_button.setFixedSize(40, 30)
        self.fullscreen_button.setToolTip("Fullscreen playback (F11)")
        self.fullscreen_button.clicked.connect(self.fullscreen_requested.emit)
        layout.addWidget(self.fullscreen_button)
    
    def set_play_icon(self, is_playing):
        """Set play/pause icon"""
        if is_playing:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.play_button.setToolTip("Pause (Space)")
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.play_button.setToolTip("Play (Space)")
    
    def update_position(self, position, duration):
        """Update playback position"""
        self.position_slider.setValue(position)
        
        # Update time display
        current_time = QTime(0, 0, 0).addMSecs(position)
        total_time = QTime(0, 0, 0).addMSecs(duration)
        
        format_str = "mm:ss" if duration < 3600000 else "hh:mm:ss"
        time_text = f"{current_time.toString(format_str)} / {total_time.toString(format_str)}"
        self.time_label.setText(time_text)
    
    def update_duration(self, duration):
        """Update total duration"""
        self.position_slider.setRange(0, duration)

class VideoPlayerWidget(QFrame):
    """Video player component"""
    
    # Define signals
    video_loaded = Signal(str)  # Video loading completed
    position_changed = Signal(int)  # Playback position changed
    duration_changed = Signal(int)  # Duration changed
    playback_state_changed = Signal(bool)  # Playback state changed
    
    def __init__(self):
        super().__init__()
        self.current_video_file = None
        self.target_position = None  # Target playback position
        self.setup_ui()
        self.setup_media_player()
        self.setup_shortcuts()
    
    def setup_ui(self):
        """Setup UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # Video display area
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)
        
        # Control panel
        self.control_widget = VideoControlWidget()
        self.control_widget.play_pause_clicked.connect(self.toggle_playback)
        self.control_widget.stop_clicked.connect(self.stop_playback)
        self.control_widget.position_changed.connect(self.set_position)
        self.control_widget.volume_changed.connect(self.set_volume)
        self.control_widget.fullscreen_requested.connect(self.toggle_fullscreen)
        layout.addWidget(self.control_widget)
        
        # Default display prompt information
        self.show_placeholder()
    
    def setup_media_player(self):
        """Setup media player"""
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        # Connect signals
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_error_occurred)
        
        # Set initial volume
        self.audio_output.setVolume(0.5)
    
    def setup_shortcuts(self):
        """Setup shortcuts"""
        # Space key play/pause
        play_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        play_shortcut.activated.connect(self.toggle_playback)
        
        # F11 fullscreen
        fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        
        # Left/right arrow fast forward/rewind
        forward_shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        forward_shortcut.activated.connect(lambda: self.skip_time(5000))
        
        backward_shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        backward_shortcut.activated.connect(lambda: self.skip_time(-5000))
    
    def show_placeholder(self):
        """Show placeholder information"""
        placeholder_layout = QVBoxLayout()
        placeholder_label = QLabel("🎬 Video player ready\n\nClick 'File' → 'Import Video and Subtitles' to start")
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
        
        # Temporarily hide video component, show placeholder
        self.video_widget.hide()
        if not hasattr(self, 'placeholder_widget'):
            self.placeholder_widget = QWidget()
            self.placeholder_widget.setLayout(placeholder_layout)
            self.layout().insertWidget(0, self.placeholder_widget)
    
    def hide_placeholder(self):
        """Hide placeholder"""
        if hasattr(self, 'placeholder_widget'):
            self.placeholder_widget.hide()
        self.video_widget.show()
    
    def load_video(self, video_path):
        """Load video file"""
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "Error", f"Video file does not exist: {video_path}")
            return False
        
        try:
            self.current_video_file = video_path
            video_url = QUrl.fromLocalFile(os.path.abspath(video_path))
            self.media_player.setSource(video_url)
            self.hide_placeholder()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load video: {str(e)}")
            return False
    
    def toggle_playback(self):
        """Toggle play/pause state"""
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def stop_playback(self):
        """Stop playback"""
        self.media_player.stop()
    
    def set_position(self, position):
        """Set playback position"""
        self.media_player.setPosition(position)
    
    def set_volume(self, volume):
        """Set volume (0-100)"""
        self.audio_output.setVolume(volume / 100.0)
    
    def skip_time(self, milliseconds):
        """Skip time (milliseconds)"""
        current_pos = self.media_player.position()
        new_pos = max(0, min(current_pos + milliseconds, self.media_player.duration()))
        self.set_position(new_pos)
    
    def play_segment(self, start_ms, end_ms):
        """Play specified time segment"""
        self.target_position = end_ms
        self.set_position(start_ms)
        self.media_player.play()
        
        # Set timer to stop at specified time
        if hasattr(self, 'segment_timer'):
            self.segment_timer.stop()
        
        self.segment_timer = QTimer()
        self.segment_timer.setSingleShot(True)
        self.segment_timer.timeout.connect(lambda: self.media_player.pause())
        self.segment_timer.start(end_ms - start_ms)
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.video_widget.isFullScreen():
            self.video_widget.setFullScreen(False)
        else:
            self.video_widget.setFullScreen(True)
    
    # Media player event handling
    def on_position_changed(self, position):
        """Playback position changed"""
        self.control_widget.update_position(position, self.media_player.duration())
        self.position_changed.emit(position)
        
        # Check if need to stop at target position
        if self.target_position and position >= self.target_position:
            self.media_player.pause()
            self.target_position = None
    
    def on_duration_changed(self, duration):
        """Duration changed"""
        self.control_widget.update_duration(duration)
        self.duration_changed.emit(duration)
    
    def on_playback_state_changed(self, state):
        """Playback state changed"""
        is_playing = (state == QMediaPlayer.PlayingState)
        self.control_widget.set_play_icon(is_playing)
        self.playback_state_changed.emit(is_playing)
    
    def on_media_status_changed(self, status):
        """Media status changed"""
        if status == QMediaPlayer.LoadedMedia:
            # Video loading completed
            if self.current_video_file:
                self.video_loaded.emit(self.current_video_file)
        elif status == QMediaPlayer.InvalidMedia:
            QMessageBox.warning(self, "Warning", "Invalid media file")
    
    def on_error_occurred(self, error):
        """Playback error handling"""
        error_messages = {
            QMediaPlayer.NoError: "No error",
            QMediaPlayer.ResourceError: "Resource error",
            QMediaPlayer.FormatError: "Format not supported",
            QMediaPlayer.NetworkError: "Network error",
            QMediaPlayer.AccessDeniedError: "Access denied"
        }
        
        error_msg = error_messages.get(error, f"Unknown error ({error})")
        QMessageBox.critical(self, "Playback Error", f"Video playback error: {error_msg}")
    
    def get_current_position(self):
        """Get current playback position (milliseconds)"""
        return self.media_player.position()
    
    def get_duration(self):
        """Get video total duration (milliseconds)"""
        return self.media_player.duration()
    
    def is_playing(self):
        """Check if currently playing"""
        return self.media_player.playbackState() == QMediaPlayer.PlayingState
