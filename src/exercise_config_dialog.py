"""
Exercise configuration dialog
Allows users to configure learning level, blank focus areas and exercise difficulty
"""
from typing import List, Dict
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QPushButton, QLabel, QGroupBox, QSlider, 
                               QComboBox, QCheckBox, QTextEdit, QProgressBar,
                               QMessageBox, QSpinBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from config import config
from ai_exercise_generator import AIExerciseThread

class ExerciseConfigDialog(QDialog):
    """Exercise configuration dialog"""
    
    # Signal definition
    exercises_generated = Signal(list)  # Exercise generation completion signal
    
    def __init__(self, parent=None, subtitles=None):
        super().__init__(parent)
        self.subtitles = subtitles or []
        self.ai_thread = None
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup user interface"""
        self.setWindowTitle("Exercise Configuration")
        self.setMinimumSize(500, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Language configuration
        language_group = QGroupBox("Language Settings")
        language_layout = QFormLayout(language_group)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            "English",
            "Spanish",
            "French",
            "German",
            "Italian",
            "Portuguese",
            "Russian",
            "Japanese",
            "Korean",
            "Chinese",
            "Other"
        ])
        self.language_combo.setCurrentText("English")
        language_layout.addRow("Learning Language:", self.language_combo)
        
        # Language description
        language_desc = QLabel(
            "Select the target language you want to learn. AI will adjust\n"
            "vocabulary difficulty and grammar focus based on the selected language."
        )
        language_desc.setStyleSheet("color: #666; font-size: 12px;")
        language_layout.addRow("", language_desc)
        
        layout.addWidget(language_group)
        
        # Learning level configuration
        level_group = QGroupBox("Learning Level")
        level_layout = QFormLayout(level_group)
        
        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "A1-A2 (Beginner)",
            "B1-B2 (Intermediate)", 
            "C1-C2 (Advanced)"
        ])
        self.level_combo.setCurrentText("B1-B2 (Intermediate)")
        level_layout.addRow("Language Level:", self.level_combo)
        
        # Level description
        level_desc = QLabel(
            "• A1-A2: Basic vocabulary, simple grammar\n"
            "• B1-B2: Common vocabulary, intermediate grammar\n" 
            "• C1-C2: Advanced vocabulary, complex grammar"
        )
        level_desc.setStyleSheet("color: #666; font-size: 12px;")
        level_layout.addRow("", level_desc)
        
        layout.addWidget(level_group)
        
        # Blank focus configuration
        focus_group = QGroupBox("Blank Focus Areas")
        focus_layout = QVBoxLayout(focus_group)
        
        # Blank by part of speech
        pos_label = QLabel("Blank by Part of Speech:")
        pos_label.setFont(QFont("", 10, QFont.Bold))
        focus_layout.addWidget(pos_label)
        
        pos_layout = QHBoxLayout()
        self.noun_check = QCheckBox("Nouns")
        self.verb_check = QCheckBox("Verbs") 
        self.adj_check = QCheckBox("Adjectives")
        self.prep_check = QCheckBox("Prepositions")
        
        # Default select nouns and verbs
        self.noun_check.setChecked(True)
        self.verb_check.setChecked(True)
        
        pos_layout.addWidget(self.noun_check)
        pos_layout.addWidget(self.verb_check)
        pos_layout.addWidget(self.adj_check)
        pos_layout.addWidget(self.prep_check)
        pos_layout.addStretch()
        focus_layout.addLayout(pos_layout)
        
        # Blank by difficulty
        diff_label = QLabel("Blank by Vocabulary Difficulty:")
        diff_label.setFont(QFont("", 10, QFont.Bold))
        focus_layout.addWidget(diff_label)
        
        diff_layout = QHBoxLayout()
        self.common_check = QCheckBox("High-frequency Words")
        self.advanced_check = QCheckBox("Low-frequency/Core Vocabulary")
        
        # Default select core vocabulary
        self.advanced_check.setChecked(True)
        
        diff_layout.addWidget(self.common_check)
        diff_layout.addWidget(self.advanced_check)
        diff_layout.addStretch()
        focus_layout.addLayout(diff_layout)
        
        # Blank by grammar points
        grammar_label = QLabel("Blank by Grammar Points:")
        grammar_label.setFont(QFont("", 10, QFont.Bold))
        focus_layout.addWidget(grammar_label)
        
        grammar_layout = QHBoxLayout()
        self.tense_check = QCheckBox("Verb Tenses")
        self.modal_check = QCheckBox("Modal Verbs")
        self.phrase_check = QCheckBox("Fixed Collocations")
        
        grammar_layout.addWidget(self.tense_check)
        grammar_layout.addWidget(self.modal_check)
        grammar_layout.addWidget(self.phrase_check)
        grammar_layout.addStretch()
        focus_layout.addLayout(grammar_layout)
        
        layout.addWidget(focus_group)
        
        # Blank density configuration
        density_group = QGroupBox("Blank Density")
        density_layout = QFormLayout(density_group)
        
        density_slider_layout = QHBoxLayout()
        
        self.density_slider = QSlider(Qt.Horizontal)
        self.density_slider.setRange(10, 50)
        self.density_slider.setValue(25)
        self.density_slider.setTickPosition(QSlider.TicksBelow)
        self.density_slider.setTickInterval(10)
        self.density_slider.valueChanged.connect(self.update_density_label)
        density_slider_layout.addWidget(self.density_slider)
        
        self.density_label = QLabel("25%")
        self.density_label.setMinimumWidth(40)
        density_slider_layout.addWidget(self.density_label)
        
        density_layout.addRow("Blank Ratio:", density_slider_layout)
        
        # Density description
        density_desc = QLabel(
            "• 10-20%: Simple exercises, suitable for beginners\n"
            "• 20-30%: Intermediate exercises, balanced difficulty\n"
            "• 30-50%: High difficulty exercises, deep learning"
        )
        density_desc.setStyleSheet("color: #666; font-size: 12px;")
        density_layout.addRow("", density_desc)
        
        layout.addWidget(density_group)
        
        # Preview information
        preview_group = QGroupBox("Generation Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.subtitle_count_label = QLabel(f"Subtitle Count: {len(self.subtitles)} sentences")
        preview_layout.addWidget(self.subtitle_count_label)
        
        self.estimated_time_label = QLabel("Estimated Generation Time: Calculating...")
        preview_layout.addWidget(self.estimated_time_label)
        
        # Update estimated time
        self.update_estimated_time()
        
        layout.addWidget(preview_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Button area
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.generate_button = QPushButton("Generate Exercise")
        self.generate_button.clicked.connect(self.generate_exercises)
        self.generate_button.setDefault(True)
        button_layout.addWidget(self.generate_button)
        
        layout.addLayout(button_layout)
    
    def update_density_label(self, value):
        """Update density label"""
        self.density_label.setText(f"{value}%")
        self.update_estimated_time()
    
    def update_estimated_time(self):
        """Update estimated generation time"""
        if not self.subtitles:
            self.estimated_time_label.setText("Estimated Generation Time: 0 seconds")
            return
        
        # Estimate time based on subtitle count (about 2-3 seconds per sentence)
        estimated_seconds = len(self.subtitles) * 2.5
        
        if estimated_seconds < 60:
            time_str = f"{int(estimated_seconds)} seconds"
        else:
            minutes = int(estimated_seconds // 60)
            seconds = int(estimated_seconds % 60)
            time_str = f"{minutes} minutes {seconds} seconds"
        
        self.estimated_time_label.setText(f"Estimated Generation Time: {time_str}")
    
    def get_selected_focus_areas(self) -> List[str]:
        """Get selected blank focus areas"""
        areas = []
        
        # Part of speech types
        if self.noun_check.isChecked():
            areas.append("nouns")
        if self.verb_check.isChecked():
            areas.append("verbs")
        if self.adj_check.isChecked():
            areas.append("adjectives")
        if self.prep_check.isChecked():
            areas.append("prepositions")
        
        # Difficulty types
        if self.common_check.isChecked():
            areas.append("high-frequency words")
        if self.advanced_check.isChecked():
            areas.append("low-frequency words")
        
        # Grammar types
        if self.tense_check.isChecked():
            areas.append("verb tenses")
        if self.modal_check.isChecked():
            areas.append("modal verbs")
        if self.phrase_check.isChecked():
            areas.append("fixed collocations")
        
        return areas if areas else ["nouns", "verbs"]  # Default value
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        language_text = self.language_combo.currentText()
        language = language_text.split()[0]  # Extract language name, such as English, Spanish, etc.
        
        level_text = self.level_combo.currentText()
        level = level_text.split()[0]  # Extract A1-A2, B1-B2, C1-C2
        
        return {
            'language': language,
            'level': level,
            'focus_areas': self.get_selected_focus_areas(),
            'blank_density': self.density_slider.value()
        }
    
    def load_config(self):
        """Load saved configuration"""
        exercise_config = config.get_exercise_config()
        
        # Set learning language
        language = exercise_config.get('language', 'English')
        for i in range(self.language_combo.count()):
            if language in self.language_combo.itemText(i):
                self.language_combo.setCurrentIndex(i)
                break
        
        # Set learning level
        level = exercise_config.get('level', 'B1-B2')
        for i in range(self.level_combo.count()):
            if level in self.level_combo.itemText(i):
                self.level_combo.setCurrentIndex(i)
                break
        
        # Set blank focus areas
        focus_areas = exercise_config.get('focus_areas', ['nouns', 'verbs'])
        
        self.noun_check.setChecked('nouns' in focus_areas)
        self.verb_check.setChecked('verbs' in focus_areas)
        self.adj_check.setChecked('adjectives' in focus_areas)
        self.prep_check.setChecked('prepositions' in focus_areas)
        self.common_check.setChecked('high-frequency words' in focus_areas)
        self.advanced_check.setChecked('low-frequency words' in focus_areas)
        self.tense_check.setChecked('verb tenses' in focus_areas)
        self.modal_check.setChecked('modal verbs' in focus_areas)
        self.phrase_check.setChecked('fixed collocations' in focus_areas)
        
        # Set blank density
        density = exercise_config.get('blank_density', 25)
        self.density_slider.setValue(density)
    
    def save_config(self):
        """Save configuration"""
        exercise_config = self.get_config()
        config.set_exercise_config(
            exercise_config['language'],
            exercise_config['level'],
            exercise_config['focus_areas'],
            exercise_config['blank_density']
        )
        config.save_config()
    
    def generate_exercises(self):
        """Generate exercises"""
        if not self.subtitles:
            QMessageBox.warning(self, "Warning", "No subtitle data, please import subtitle file first")
            return
        
        # Validate AI configuration
        ai_config = config.get_ai_config()
        if not ai_config.get('api_key') or not ai_config.get('api_url'):
            QMessageBox.warning(self, "Warning", 
                               "Please configure AI service first\n\n"
                               "Click menu 'Settings' → 'AI Service Configuration' to configure")
            return
        
        # Validate selections
        if not self.get_selected_focus_areas():
            QMessageBox.warning(self, "Warning", "Please select at least one blank focus area")
            return
        
        # Save configuration
        self.save_config()
        
        # Start generation
        self.start_generation()
    
    def start_generation(self):
        """Start exercise generation"""
        self.generate_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Create and start AI generation thread
        exercise_config = self.get_config()
        self.ai_thread = AIExerciseThread(self.subtitles, exercise_config)
        
        # Connect signals
        self.ai_thread.generation_started.connect(self.on_generation_started)
        self.ai_thread.generation_finished.connect(self.on_generation_finished)
        self.ai_thread.progress_updated.connect(self.progress_bar.setValue)
        
        self.ai_thread.start()
    
    def on_generation_started(self):
        """Generation started"""
        self.generate_button.setText("Generating...")
    
    def on_generation_finished(self, success: bool, message: str, exercises: list):
        """Generation completed"""
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate Exercise")
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.exercises_generated.emit(exercises)
            self.accept()
        else:
            QMessageBox.critical(self, "Failed", message)
    
    def closeEvent(self, event):
        """Close event"""
        # If generation thread is running, stop it first
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.terminate()
            self.ai_thread.wait()
        event.accept()
