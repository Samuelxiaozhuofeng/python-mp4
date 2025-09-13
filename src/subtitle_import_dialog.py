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
        
        for subtitle in self.subtitles[:50]:  # Only show first 50 items
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
        """Setup user interface"""
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
        """Create import panel"""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        
        # File selection group
        file_group = QGroupBox("Select Subtitle File")
        file_layout = QVBoxLayout(file_group)
        
        # File path display
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("color: #666; font-style: italic;")
        file_layout.addWidget(self.file_path_label)
        
        # Select file button
        select_file_btn = QPushButton("Select SRT File")
        select_file_btn.clicked.connect(self.select_subtitle_file)
        file_layout.addWidget(select_file_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        file_layout.addWidget(self.progress_bar)
        
        layout.addWidget(file_group)
        
        # Subtitle info group
        self.info_group = QGroupBox("Subtitle Information")
        info_layout = QFormLayout(self.info_group)
        
        self.subtitle_count_label = QLabel("-")
        info_layout.addRow("Subtitle Count:", self.subtitle_count_label)
        
        self.duration_label = QLabel("-")
        info_layout.addRow("Total Duration:", self.duration_label)
        
        self.time_range_label = QLabel("-")
        info_layout.addRow("Time Range:", self.time_range_label)
        
        self.info_group.setVisible(False)
        layout.addWidget(self.info_group)
        
        # Time synchronization adjustment group
        self.sync_group = QGroupBox("Time Synchronization Adjustment")
        sync_layout = QFormLayout(self.sync_group)
        
        # Time offset adjustment
        offset_layout = QHBoxLayout()
        
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-30000, 30000)  # -30 seconds to +30 seconds
        self.offset_slider.setValue(0)
        self.offset_slider.valueChanged.connect(self.on_offset_changed)
        offset_layout.addWidget(self.offset_slider)
        
        self.offset_label = QLabel("0.0s")
        self.offset_label.setMinimumWidth(60)
        offset_layout.addWidget(self.offset_label)
        
        sync_layout.addRow("Time Offset:", offset_layout)
        
        # Reset button
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_offset)
        sync_layout.addRow("", reset_btn)
        
        self.sync_group.setVisible(False)
        layout.addWidget(self.sync_group)
        
        # Validation results group
        self.validation_group = QGroupBox("Validation Results")
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
        """Connect signals"""
        self.subtitle_parser.parsing_started.connect(self.on_parsing_started)
        self.subtitle_parser.parsing_finished.connect(self.on_parsing_finished)
        self.subtitle_parser.progress_updated.connect(self.progress_bar.setValue)
    
    def select_subtitle_file(self):
        """Select subtitle file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Subtitle File",
            "",
            "Subtitle Files (*.srt);;All Files (*)"
        )
        
        if file_path:
            self.load_subtitle_file(file_path)
    
    def load_subtitle_file(self, file_path):
        """Load subtitle file"""
        self.file_path_label.setText(os.path.basename(file_path))
        self.subtitle_parser.load_srt_file(file_path)
    
    def on_parsing_started(self):
        """Parsing started"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
    
    def on_parsing_finished(self, success, message):
        """Parsing finished"""
        self.progress_bar.setVisible(False)
        
        if success:
            self.show_subtitle_info()
            self.preview_widget.load_subtitles(self.subtitle_parser.subtitles)
            self.validate_subtitles()
            self.import_button.setEnabled(True)
        else:
            QMessageBox.warning(self, "Parsing Failed", message)
            self.import_button.setEnabled(False)
    
    def show_subtitle_info(self):
        """Show subtitle information"""
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
        """Validate subtitles"""
        if self.video_duration_ms > 0:
            validation = self.subtitle_parser.validate_timing(self.video_duration_ms)
            
            result_text = []
            
            if validation['valid']:
                result_text.append("✓ Subtitle validation passed")
            else:
                result_text.append("⚠ Found the following issues:")
                for issue in validation['issues']:
                    result_text.append(f"  • {issue}")
                
                if validation['suggestions']:
                    result_text.append("\nSuggestions:")
                    for suggestion in validation['suggestions']:
                        result_text.append(f"  • {suggestion}")
            
            # Show statistics
            stats = validation.get('stats', {})
            if stats:
                result_text.append(f"\nStatistics:")
                result_text.append(f"  • Total subtitles: {stats.get('total_subtitles', 0)}")
                if stats.get('overlapping', 0) > 0:
                    result_text.append(f"  • Overlapping subtitles: {stats['overlapping']}")
                if stats.get('gaps', 0) > 0:
                    result_text.append(f"  • Large gaps: {stats['gaps']}")
            
            self.validation_text.setText('\n'.join(result_text))
            self.validation_group.setVisible(True)
    
    def on_offset_changed(self, value):
        """Offset changed"""
        offset_sec = value / 1000.0
        self.offset_label.setText(f"{offset_sec:+.1f}s")
        
        self.subtitle_parser.set_time_offset(value)
        self.preview_widget.set_time_offset(value)
        
        # Re-validate
        if self.video_duration_ms > 0:
            self.validate_subtitles()
    
    def reset_offset(self):
        """Reset offset"""
        self.offset_slider.setValue(0)
    
    def set_current_time(self, time_ms):
        """Set current playback time"""
        self.current_time = time_ms
        self.preview_widget.set_current_time(time_ms)
    
    def import_subtitle(self):
        """Import subtitle"""
        if self.subtitle_parser.subtitles:
            self.subtitle_loaded.emit(self.subtitle_parser)
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "No subtitle data to import")
    
    def _ms_to_time_string(self, ms):
        """Convert milliseconds to time string"""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"
