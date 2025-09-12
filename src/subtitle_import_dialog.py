"""
Subtitle import dialog
Handles subtitle file import, preview and time synchronization adjustment
"""
import os
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QPushButton, QLabel, QGroupBox, QSpinBox, 
                               QTextEdit, QMessageBox, QProgressBar, QSlider,
                               QFileDialog, QListWidget, QListWidgetItem,
                               QSplitter, QFrame, QCheckBox)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from subtitle_parser import SubtitleParser, SubtitleItem

class SubtitlePreviewWidget(QFrame):
    """Subtitle preview component"""
    
    def __init__(self):
        super().__init__()
        self.subtitles = []
        self.current_time = 0
        self.time_offset = 0
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Subtitle Preview")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Subtitle list
        self.subtitle_list = QListWidget()
        self.subtitle_list.setMaximumHeight(200)
        layout.addWidget(self.subtitle_list)
        
        # Current subtitle display
        current_group = QGroupBox("Current Subtitle")
        current_layout = QVBoxLayout(current_group)
        
        self.current_subtitle_label = QLabel("No subtitle")
        self.current_subtitle_label.setWordWrap(True)
        self.current_subtitle_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        current_layout.addWidget(self.current_subtitle_label)
        
        layout.addWidget(current_group)
    
    def load_subtitles(self, subtitles):
        """Load subtitle data"""
        self.subtitles = subtitles
        self.update_subtitle_list()
    
    def update_subtitle_list(self):
        """Update subtitle list"""
        self.subtitle_list.clear()
        
        for subtitle in self.subtitles[:50]:  # 只显示前50条
            start_time = self._ms_to_time_string(subtitle.start_time + self.time_offset)
            end_time = self._ms_to_time_string(subtitle.end_time + self.time_offset)
            
            item_text = f"{start_time} - {end_time}: {subtitle.text[:50]}..."
            item = QListWidgetItem(item_text)
            self.subtitle_list.addItem(item)
        
        if len(self.subtitles) > 50:
            item = QListWidgetItem(f"... {len(self.subtitles) - 50} more subtitles")
            item.setForeground(Qt.gray)
            self.subtitle_list.addItem(item)
    
    def set_time_offset(self, offset_ms):
        """Set time offset"""
        self.time_offset = offset_ms
        self.update_subtitle_list()
        self.update_current_subtitle()
    
    def set_current_time(self, time_ms):
        """Set current time and update display"""
        self.current_time = time_ms
        self.update_current_subtitle()
    
    def update_current_subtitle(self):
        """Update current subtitle display"""
        adjusted_time = self.current_time - self.time_offset
        current_subtitle = None
        
        for subtitle in self.subtitles:
            if subtitle.start_time <= adjusted_time <= subtitle.end_time:
                current_subtitle = subtitle
                break
        
        if current_subtitle:
            start_time = self._ms_to_time_string(current_subtitle.start_time + self.time_offset)
            end_time = self._ms_to_time_string(current_subtitle.end_time + self.time_offset)
            
            text = f"[{start_time} - {end_time}]\n{current_subtitle.text}"
            self.current_subtitle_label.setText(text)
            self.current_subtitle_label.setStyleSheet("""
                QLabel {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 14px;
                }
            """)
        else:
            self.current_subtitle_label.setText("No subtitle at current time")
            self.current_subtitle_label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 14px;
                    color: #6c757d;
                }
            """)
    
    def _ms_to_time_string(self, ms):
        """Convert milliseconds to time string"""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"

class SubtitleImportDialog(QDialog):
    """Subtitle import dialog"""
    
    # Define signals
    subtitle_loaded = Signal(object)  # Subtitle parser object
    
    def __init__(self, parent=None, video_duration_ms=0):
        super().__init__(parent)
        self.video_duration_ms = video_duration_ms
        self.subtitle_parser = SubtitleParser()
        self.current_time = 0
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("Import Subtitle File")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side: file import and time adjustment
        left_widget = self.create_import_panel()
        splitter.addWidget(left_widget)
        
        # Right side: subtitle preview
        self.preview_widget = SubtitlePreviewWidget()
        splitter.addWidget(self.preview_widget)
        
        # Set splitter ratio
        splitter.setSizes([400, 400])
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.import_button = QPushButton("Import Subtitle")
        self.import_button.clicked.connect(self.import_subtitle)
        self.import_button.setDefault(True)
        self.import_button.setEnabled(False)
        button_layout.addWidget(self.import_button)
        
        layout.addLayout(button_layout)
    
    def create_import_panel(self):
        """创建导入面板"""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        
        # 文件选择组
        file_group = QGroupBox("选择字幕文件")
        file_layout = QVBoxLayout(file_group)
        
        # 文件路径显示
        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setStyleSheet("color: #666; font-style: italic;")
        file_layout.addWidget(self.file_path_label)
        
        # 选择文件按钮
        select_file_btn = QPushButton("选择SRT文件")
        select_file_btn.clicked.connect(self.select_subtitle_file)
        file_layout.addWidget(select_file_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        file_layout.addWidget(self.progress_bar)
        
        layout.addWidget(file_group)
        
        # 字幕信息组
        self.info_group = QGroupBox("字幕信息")
        info_layout = QFormLayout(self.info_group)
        
        self.subtitle_count_label = QLabel("-")
        info_layout.addRow("字幕条数:", self.subtitle_count_label)
        
        self.duration_label = QLabel("-")
        info_layout.addRow("总时长:", self.duration_label)
        
        self.time_range_label = QLabel("-")
        info_layout.addRow("时间范围:", self.time_range_label)
        
        self.info_group.setVisible(False)
        layout.addWidget(self.info_group)
        
        # 时间同步调整组
        self.sync_group = QGroupBox("时间同步调整")
        sync_layout = QFormLayout(self.sync_group)
        
        # 时间偏移调整
        offset_layout = QHBoxLayout()
        
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-30000, 30000)  # -30秒到+30秒
        self.offset_slider.setValue(0)
        self.offset_slider.valueChanged.connect(self.on_offset_changed)
        offset_layout.addWidget(self.offset_slider)
        
        self.offset_label = QLabel("0.0秒")
        self.offset_label.setMinimumWidth(60)
        offset_layout.addWidget(self.offset_label)
        
        sync_layout.addRow("时间偏移:", offset_layout)
        
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_offset)
        sync_layout.addRow("", reset_btn)
        
        self.sync_group.setVisible(False)
        layout.addWidget(self.sync_group)
        
        # 验证结果组
        self.validation_group = QGroupBox("验证结果")
        validation_layout = QVBoxLayout(self.validation_group)
        
        self.validation_text = QTextEdit()
        self.validation_text.setMaximumHeight(150)
        self.validation_text.setReadOnly(True)
        validation_layout.addWidget(self.validation_text)
        
        self.validation_group.setVisible(False)
        layout.addWidget(self.validation_group)
        
        layout.addStretch()
        return widget
    
    def connect_signals(self):
        """连接信号"""
        self.subtitle_parser.parsing_started.connect(self.on_parsing_started)
        self.subtitle_parser.parsing_finished.connect(self.on_parsing_finished)
        self.subtitle_parser.progress_updated.connect(self.progress_bar.setValue)
    
    def select_subtitle_file(self):
        """选择字幕文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择字幕文件",
            "",
            "字幕文件 (*.srt);;所有文件 (*)"
        )
        
        if file_path:
            self.load_subtitle_file(file_path)
    
    def load_subtitle_file(self, file_path):
        """加载字幕文件"""
        self.file_path_label.setText(os.path.basename(file_path))
        self.subtitle_parser.load_srt_file(file_path)
    
    def on_parsing_started(self):
        """解析开始"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
    
    def on_parsing_finished(self, success, message):
        """解析完成"""
        self.progress_bar.setVisible(False)
        
        if success:
            self.show_subtitle_info()
            self.preview_widget.load_subtitles(self.subtitle_parser.subtitles)
            self.validate_subtitles()
            self.import_button.setEnabled(True)
        else:
            QMessageBox.warning(self, "解析失败", message)
            self.import_button.setEnabled(False)
    
    def show_subtitle_info(self):
        """显示字幕信息"""
        stats = self.subtitle_parser.get_subtitle_stats()
        
        self.subtitle_count_label.setText(str(stats['total_count']))
        
        duration_sec = stats['time_span_ms'] // 1000
        duration_str = f"{duration_sec // 60:02d}:{duration_sec % 60:02d}"
        self.duration_label.setText(duration_str)
        
        start_str = self._ms_to_time_string(stats['first_start_time'])
        end_str = self._ms_to_time_string(stats['last_end_time'])
        self.time_range_label.setText(f"{start_str} - {end_str}")
        
        self.info_group.setVisible(True)
        self.sync_group.setVisible(True)
    
    def validate_subtitles(self):
        """验证字幕"""
        if self.video_duration_ms > 0:
            validation = self.subtitle_parser.validate_timing(self.video_duration_ms)
            
            result_text = []
            
            if validation['valid']:
                result_text.append("✓ 字幕验证通过")
            else:
                result_text.append("⚠ 发现以下问题:")
                for issue in validation['issues']:
                    result_text.append(f"  • {issue}")
                
                if validation['suggestions']:
                    result_text.append("\n建议:")
                    for suggestion in validation['suggestions']:
                        result_text.append(f"  • {suggestion}")
            
            # 显示统计信息
            stats = validation.get('stats', {})
            if stats:
                result_text.append(f"\n统计信息:")
                result_text.append(f"  • 总字幕数: {stats.get('total_subtitles', 0)}")
                if stats.get('overlapping', 0) > 0:
                    result_text.append(f"  • 重叠字幕: {stats['overlapping']}")
                if stats.get('gaps', 0) > 0:
                    result_text.append(f"  • 间隔过大: {stats['gaps']}")
            
            self.validation_text.setText('\n'.join(result_text))
            self.validation_group.setVisible(True)
    
    def on_offset_changed(self, value):
        """偏移量改变"""
        offset_sec = value / 1000.0
        self.offset_label.setText(f"{offset_sec:+.1f}秒")
        
        self.subtitle_parser.set_time_offset(value)
        self.preview_widget.set_time_offset(value)
        
        # 重新验证
        if self.video_duration_ms > 0:
            self.validate_subtitles()
    
    def reset_offset(self):
        """重置偏移量"""
        self.offset_slider.setValue(0)
    
    def set_current_time(self, time_ms):
        """设置当前播放时间"""
        self.current_time = time_ms
        self.preview_widget.set_current_time(time_ms)
    
    def import_subtitle(self):
        """导入字幕"""
        if self.subtitle_parser.subtitles:
            self.subtitle_loaded.emit(self.subtitle_parser)
            self.accept()
        else:
            QMessageBox.warning(self, "警告", "没有可导入的字幕数据")
    
    def _ms_to_time_string(self, ms):
        """Convert milliseconds to time string"""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"
