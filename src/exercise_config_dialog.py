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
import spacy_cloze
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

        # Generation settings (spaCy/AI mode)
        gen_group = QGroupBox("Generation Settings")
        gen_layout = QFormLayout(gen_group)

        # Mode combo with internal codes as userData
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Hybrid (spaCy + AI)", userData="hybrid")
        self.mode_combo.addItem("spaCy only (local)", userData="spacy")
        self.mode_combo.addItem("AI only", userData="ai")
        self.mode_combo.currentIndexChanged.connect(self.update_estimated_time)
        gen_layout.addRow("Generation Mode:", self.mode_combo)

        # spaCy enable toggle
        self.use_spacy_check = QCheckBox("Enable spaCy acceleration (recommended for Spanish)")
        self.use_spacy_check.setChecked(True)
        self.use_spacy_check.stateChanged.connect(self.update_estimated_time)
        gen_layout.addRow("spaCy:", self.use_spacy_check)

        tip = QLabel("spaCy 提供更稳定的分词/词性，hybrid 模式先选词再由 AI 生成提示。")
        tip.setStyleSheet("color: #666; font-size: 12px;")
        gen_layout.addRow("", tip)

        layout.addWidget(gen_group)

        # spaCy(local) specific options
        self.spacy_group = QGroupBox("spaCy (local) Options")
        sp_layout = QFormLayout(self.spacy_group)

        # POS checkboxes
        pos_box = QHBoxLayout()
        self.sp_pos_noun = QCheckBox("NOUN")
        self.sp_pos_verb = QCheckBox("VERB")
        self.sp_pos_adj = QCheckBox("ADJ")
        self.sp_pos_adv = QCheckBox("ADV")
        for w in (self.sp_pos_noun, self.sp_pos_verb, self.sp_pos_adj, self.sp_pos_adv):
            w.setChecked(True)
            pos_box.addWidget(w)
        pos_box.addStretch()
        sp_layout.addRow("POS to blank:", pos_box)

        # Max blanks per sentence
        self.sp_max_blanks = QSpinBox()
        self.sp_max_blanks.setRange(1, 5)
        self.sp_max_blanks.setValue(2)
        sp_layout.addRow("Max blanks per sentence:", self.sp_max_blanks)

        # Exclude stopwords
        self.sp_exclude_stop = QCheckBox("Exclude stopwords")
        self.sp_exclude_stop.setChecked(True)
        sp_layout.addRow("Stopwords:", self.sp_exclude_stop)

        # Prefer named entities
        self.sp_prefer_entities = QCheckBox("Prefer named entities / PROPN")
        self.sp_prefer_entities.setChecked(True)
        sp_layout.addRow("Entities:", self.sp_prefer_entities)

        # Include lemma in hint
        self.sp_hint_lemma = QCheckBox("Include lemma in hint")
        self.sp_hint_lemma.setChecked(True)
        sp_layout.addRow("Hints:", self.sp_hint_lemma)

        layout.addWidget(self.spacy_group)

        # Toggle spaCy group visibility based on mode
        self.mode_combo.currentIndexChanged.connect(self._update_spacy_visibility)
        self._update_spacy_visibility()
        
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
        # Estimate time per sentence by mode
        mode = self.mode_combo.currentData() if hasattr(self, 'mode_combo') else 'hybrid'
        use_spacy = self.use_spacy_check.isChecked() if hasattr(self, 'use_spacy_check') else True
        if mode == 'spacy' and use_spacy:
            per = 0.08  # very fast local
        elif mode == 'hybrid' and use_spacy:
            per = 0.9   # faster than pure AI
        else:
            per = 2.5   # default AI estimate
        estimated_seconds = len(self.subtitles) * per
        
        if estimated_seconds < 60:
            time_str = f"{int(estimated_seconds)} seconds"
        else:
            minutes = int(estimated_seconds // 60)
            seconds = int(estimated_seconds % 60)
            time_str = f"{minutes} minutes {seconds} seconds"
        
        self.estimated_time_label.setText(f"Estimated Generation Time: {time_str}")

    def _update_spacy_visibility(self):
        """Show spaCy options only in spaCy(local) mode."""
        mode = self.mode_combo.currentData()
        self.spacy_group.setVisible(mode == 'spacy')
    
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
        
        # spaCy options
        sp_pos = []
        if self.sp_pos_noun.isChecked():
            sp_pos.append("NOUN")
        if self.sp_pos_verb.isChecked():
            sp_pos.append("VERB")
        if self.sp_pos_adj.isChecked():
            sp_pos.append("ADJ")
        if self.sp_pos_adv.isChecked():
            sp_pos.append("ADV")

        return {
            'language': language,
            'level': level,
            'focus_areas': self.get_selected_focus_areas(),
            'blank_density': self.density_slider.value(),
            'use_spacy': self.use_spacy_check.isChecked(),
            'generation_mode': self.mode_combo.currentData() or 'hybrid',
            'spacy_options': {
                'pos': sp_pos or ["NOUN", "VERB", "ADJ", "ADV"],
                'max_blanks': int(self.sp_max_blanks.value()),
                'exclude_stop': bool(self.sp_exclude_stop.isChecked()),
                'hint_lemma': bool(self.sp_hint_lemma.isChecked()),
                'prefer_entities': bool(self.sp_prefer_entities.isChecked()),
            }
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

        # Generation settings
        use_spacy = exercise_config.get('use_spacy', True)
        self.use_spacy_check.setChecked(bool(use_spacy))

        mode = exercise_config.get('generation_mode', 'hybrid')
        # select item whose userData equals mode
        chosen = 0
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == mode:
                chosen = i
                break
        self.mode_combo.setCurrentIndex(chosen)
        self.update_estimated_time()

        # spaCy options load
        sp = exercise_config.get('spacy_options', {}) or {}
        pos = set(sp.get('pos', ["NOUN","VERB","ADJ","ADV"]))
        self.sp_pos_noun.setChecked("NOUN" in pos)
        self.sp_pos_verb.setChecked("VERB" in pos)
        self.sp_pos_adj.setChecked("ADJ" in pos)
        self.sp_pos_adv.setChecked("ADV" in pos)
        self.sp_max_blanks.setValue(int(sp.get('max_blanks', 2)))
        self.sp_exclude_stop.setChecked(bool(sp.get('exclude_stop', True)))
        self.sp_hint_lemma.setChecked(bool(sp.get('hint_lemma', True)))
        self.sp_prefer_entities.setChecked(bool(sp.get('prefer_entities', True)))
        self._update_spacy_visibility()
    
    def save_config(self):
        """Save configuration"""
        exercise_config = self.get_config()
        config.set_exercise_config(
            exercise_config['language'],
            exercise_config['level'],
            exercise_config['focus_areas'],
            exercise_config['blank_density']
        )
        # Save spaCy integration settings
        config.set('exercise.use_spacy', bool(exercise_config.get('use_spacy', True)))
        config.set('exercise.generation_mode', exercise_config.get('generation_mode', 'hybrid'))
        config.set('exercise.spacy_options', exercise_config.get('spacy_options', {}))
        config.save_config()
    
    def generate_exercises(self):
        """Generate exercises"""
        if not self.subtitles:
            QMessageBox.warning(self, "Warning", "No subtitle data, please import subtitle file first")
            return
        
        # Determine mode and validate accordingly
        ex_cfg = self.get_config()
        mode = ex_cfg.get('generation_mode', 'hybrid')
        if mode == 'spacy' and ex_cfg.get('use_spacy', True):
            # Ensure spaCy model is available for the language
            if not spacy_cloze.ensure_nlp(ex_cfg.get('language', 'Spanish')):
                QMessageBox.warning(self, "spaCy Not Available",
                                    "spaCy model unavailable. Please install Spanish model:\n\n"
                                    "python -m spacy download es_core_news_md")
                return
        else:
            # Validate AI configuration for modes that require AI
            ai_config = config.get_ai_config()
            if not ai_config.get('api_key') or not ai_config.get('api_url'):
                # Offer to switch to spaCy-only if available
                if spacy_cloze.ensure_nlp(ex_cfg.get('language', 'Spanish')):
                    choice = QMessageBox.question(
                        self,
                        "AI Config Missing",
                        "AI configuration not set. Switch to spaCy-only mode?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if choice == QMessageBox.Yes:
                        # Temporarily switch mode for this run and save
                        self.mode_combo.setCurrentIndex(1)  # spaCy item
                        self.use_spacy_check.setChecked(True)
                        self.save_config()
                    else:
                        return
                else:
                    QMessageBox.warning(self, "Warning",
                                        "Please configure AI service first or install spaCy Spanish model\n\n"
                                        "AI: Settings → AI Service Configuration\n"
                                        "spaCy: python -m spacy download es_core_news_md")
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
