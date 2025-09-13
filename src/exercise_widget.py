"""
Interactive exercise component
Implements subtitle display, fill-in-the-blank exercises and user interaction functionality
"""
import re
from typing import List, Dict, Optional, Tuple
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QFrame, QScrollArea,
                               QSizePolicy, QSpacerItem, QLayout)
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QSize, QPoint
from PySide6.QtGui import QFont, QKeySequence, QShortcut

class FlowLayout(QLayout):
    """A simple flow layout that wraps child widgets to the next line.
    Adapted from Qt's Flow Layout example.
    """

    def __init__(self, parent=None, margin=0, hspacing=8, vspacing=6):
        super().__init__(parent)
        self._item_list = []
        self._hspacing = hspacing
        self._vspacing = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                      margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        # Respect contents margins
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)

        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        max_right = effective_rect.right()

        for item in self._item_list:
            wid = item.widget()
            if wid is not None and not wid.isVisible():
                continue

            space_x = self._hspacing
            space_y = self._vspacing
            hint = item.sizeHint()
            next_x = x + hint.width() + space_x
            if next_x - space_x > max_right and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + hint.width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = next_x
            line_height = max(line_height, hint.height())
        # Total required height includes bottom margin
        return (y + line_height + bottom) - rect.y()

class BlankInputWidget(QLineEdit):
    """Blank input box component"""
    
    # Signal definition
    answer_submitted = Signal(str)  # Answer submission signal
    
    def __init__(self, expected_answer: str, placeholder: str = ""):
        super().__init__()
        self.expected_answer = expected_answer.strip().lower()
        self.is_correct = False
        self.setup_ui(placeholder)
    
    def setup_ui(self, placeholder: str):
        """Setup UI"""
        self.setPlaceholderText(placeholder or "Enter answer...")
        # Dynamic width based on expected answer length for better rhythm
        approx = max(40, min(260, 12 * max(1, len(self.expected_answer)) + 20))
        self.setMinimumWidth(approx)
        self.setMaximumWidth(max(approx, 100))
        
        # Optimize style to better integrate into sentences
        self.setStyleSheet("""
            QLineEdit {
                border: 1px solid #2196f3;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 16px;
                font-family: Inter, Roboto, 'Segoe UI', 'Noto Sans', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif;
                font-weight: normal;
                background-color: #f8f9fa;
                color: #1976d2;
                margin: 1px 2px;
            }
            QLineEdit:focus {
                border-color: #1976d2;
                background-color: #e3f2fd;
                border-width: 2px;
            }
        """)
        
        # Connect signals
        self.textChanged.connect(self.on_text_changed)
        self.returnPressed.connect(self.submit_answer)
    
    def on_text_changed(self, text):
        """Handle text changes"""
        # Real-time answer validation
        if text.strip().lower() == self.expected_answer:
            self.set_correct_style()
            self.is_correct = True
        else:
            self.set_normal_style()
            self.is_correct = False
    
    def submit_answer(self):
        """Submit answer"""
        answer = self.text().strip()
        self.answer_submitted.emit(answer)
        
        if answer.lower() == self.expected_answer:
            self.set_correct_style()
            self.is_correct = True
        else:
            self.set_incorrect_style()
            self.is_correct = False

    def submit_without_signal(self):
        """Submit answer without emitting answer_submitted signal (for programmatic validation)"""
        answer = self.text().strip()
        if answer.lower() == self.expected_answer:
            self.set_correct_style()
            self.is_correct = True
        else:
            self.set_incorrect_style()
            self.is_correct = False
    
    def set_correct_style(self):
        """Set correct answer style"""
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #4caf50;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 18px;
                font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
                font-weight: 600;
                background-color: #e8f5e8;
                color: #2e7d32;
                margin: 2px 4px;
            }
        """)
    
    def set_incorrect_style(self):
        """Set incorrect answer style"""
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #f44336;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 18px;
                font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
                font-weight: 500;
                background-color: #ffebee;
                color: #c62828;
                margin: 2px 4px;
            }
        """)
    
    def set_normal_style(self):
        """Set normal style"""
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e3f2fd;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 18px;
                font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
                font-weight: 500;
                background-color: #fafbfc;
                color: #2c3e50;
                margin: 2px 4px;
                line-height: 1.4;
            }
            QLineEdit:focus {
                border-color: #2196f3;
                background-color: #ffffff;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #90caf9;
                background-color: #ffffff;
            }
        """)
    
    def show_answer(self):
        """Show correct answer"""
        self.setText(self.expected_answer.title())
        self.set_correct_style()
        self.is_correct = True
        self.setReadOnly(True)

class SubtitleExerciseWidget(QFrame):
    """Subtitle exercise component"""
    
    # Signal definition
    exercise_completed = Signal()  # Exercise completion signal
    next_exercise_requested = Signal()  # Request next exercise signal
    hint_requested = Signal()  # Request hint signal
    show_answer_requested = Signal()  # Request show answer signal
    replay_requested = Signal()  # Request replay current sentence
    
    def __init__(self):
        super().__init__()
        self.current_exercise = None
        self.blank_inputs = []  # Store all input boxes
        self._checking_answers = False  # Prevent recursive/duplicate checking
        self.setup_ui()
        self.setup_shortcuts()
    
    def setup_ui(self):
        """Setup UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        # Use compact main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Significantly reduce margins
        layout.setSpacing(5)  # Reduce component spacing
        
        # Compact title area
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(5, 0, 5, 0)  # Reduce title area margins
        
        self.title_label = QLabel("Subtitle Exercise Area")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                background: transparent;
                border: none;
                padding: 2px 0px;
            }
        """)
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        # Progress display
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #6c757d;
                background: transparent;
                border: none;
                padding: 2px 0px;
            }
        """)
        title_layout.addWidget(self.progress_label)
        
        layout.addLayout(title_layout)
        
        # Subtitle display area (scroll area) - maximize space utilization
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(160)  # Increase default readable space
        
        # Optimize scroll area style, reduce border usage
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollArea > QWidget > QWidget {
                background-color: white;
            }
        """)
        
        self.subtitle_widget = QWidget()
        self.subtitle_widget.setStyleSheet("background-color: white;")
        self.subtitle_layout = QVBoxLayout(self.subtitle_widget)
        self.subtitle_layout.setAlignment(Qt.AlignTop)
        self.subtitle_layout.setContentsMargins(12, 12, 12, 12)
        self.subtitle_layout.setSpacing(10)
        
        scroll_area.setWidget(self.subtitle_widget)
        layout.addWidget(scroll_area, 1)  # Set stretch factor to let content area occupy more space
        
        # Compact control button area
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 3, 0, 0)  # Reduce button area margins
        control_layout.setSpacing(8)  # Reduce button spacing
        
        # Hint button - compact style
        self.hint_button = QPushButton("💡 Hint")
        self.hint_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:pressed {
                background-color: #d39e00;
            }
        """)
        self.hint_button.clicked.connect(self.hint_requested.emit)
        control_layout.addWidget(self.hint_button)
        
        # Show answer button - compact style
        self.show_answer_button = QPushButton("👁️ Show Answer")
        self.show_answer_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        self.show_answer_button.clicked.connect(self.show_all_answers)
        control_layout.addWidget(self.show_answer_button)

        # Replay current sentence button - compact style
        self.replay_button = QPushButton("🔁 Replay")
        self.replay_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
        """)
        self.replay_button.setToolTip("Replay current sentence (R)")
        self.replay_button.clicked.connect(self.replay_requested.emit)
        control_layout.addWidget(self.replay_button)

        control_layout.addStretch()
        
        # Confirm button - compact style
        self.confirm_button = QPushButton("✓ Confirm")
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: bold;
                min-height: 26px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
        """)
        self.confirm_button.clicked.connect(self.check_answers)
        self.confirm_button.setEnabled(False)
        control_layout.addWidget(self.confirm_button)
        
        # Next sentence button - compact style
        self.next_button = QPushButton("▶️ Next")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: bold;
                min-height: 26px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        self.next_button.clicked.connect(self.next_exercise_requested.emit)
        self.next_button.setVisible(False)
        control_layout.addWidget(self.next_button)
        
        layout.addLayout(control_layout)
        
        # Default display
        self.show_waiting_state()
    
    def setup_shortcuts(self):
        """Setup shortcuts"""
        # Enter key confirm
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.check_answers)
        # Support numeric keypad Enter
        keypad_enter_shortcut = QShortcut(QKeySequence(Qt.Key_Enter), self)
        keypad_enter_shortcut.activated.connect(self.check_answers)
        
        # Ctrl+H hint
        hint_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        hint_shortcut.activated.connect(self.hint_requested.emit)
        
        # Ctrl+A show answer
        answer_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        answer_shortcut.activated.connect(self.show_all_answers)
        # R key replay current sentence
        replay_shortcut = QShortcut(QKeySequence(Qt.Key_R), self)
        replay_shortcut.activated.connect(self.replay_requested.emit)
    
    def show_waiting_state(self):
        """Show waiting state"""
        print("[DEBUG] show_waiting_state called")
        self.clear_layout(self.subtitle_layout)
        
        waiting_label = QLabel("🎬 Ready\n\nPlease import video and subtitle files to start exercise")
        waiting_label.setAlignment(Qt.AlignCenter)
        waiting_label.setMinimumHeight(80)  # Reduce height
        waiting_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #6c757d;
                background-color: white;
                border: 1px dashed #dee2e6;
                border-radius: 6px;
                padding: 15px;
                margin: 5px;
            }
        """)
        
        self.subtitle_layout.addWidget(waiting_label)
        
        # Ensure layout is properly applied
        self.subtitle_widget.setMinimumHeight(90)
        self.subtitle_layout.update()
        print("[DEBUG] Waiting state label added and layout updated")
        
        self.confirm_button.setEnabled(False)
        self.next_button.setVisible(False)
    
    def show_subtitle_loaded(self, display_data: Dict):
        """Show subtitle loading success state"""
        print(f"[DEBUG] SubtitleExerciseWidget.show_subtitle_loaded called")
        print(f"[DEBUG] Received data: {display_data}")
        
        try:
            self.clear_layout(self.subtitle_layout)
            print("[DEBUG] Layout cleared")
            
            # Update progress information
            if 'total' in display_data:
                progress_text = f"Total {display_data['total']} subtitles"
                self.progress_label.setText(progress_text)
                print(f"[DEBUG] Updated progress label: {progress_text}")
            
            # Create info label - compact style
            info_text = display_data.get('original_text', 'Subtitles loaded')
            print(f"[DEBUG] Created info label, text: {info_text}")
            
            info_label = QLabel(info_text)
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setWordWrap(True)
            info_label.setMinimumHeight(70)  # Reduce height
            info_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #28a745;
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 6px;
                    padding: 12px;
                    margin: 5px;
                    line-height: 1.4;
                }
            """)
            
            self.subtitle_layout.addWidget(info_label)
            print("[DEBUG] Info label added to layout")
            
            # Ensure layout is properly applied
            self.subtitle_widget.setMinimumHeight(80)
            self.subtitle_layout.update()
            print("[DEBUG] Layout and size updated")
            
            # Disable exercise-related buttons
            self.confirm_button.setEnabled(False)
            self.next_button.setVisible(False)
            print("[DEBUG] Button state updated")
            
            # Force refresh interface
            self.update()
            self.repaint()
            print("[DEBUG] Interface refresh completed")
            
        except Exception as e:
            print(f"[ERROR] show_subtitle_loaded execution error: {e}")
            import traceback
            traceback.print_exc()
    
    def show_exercise(self, exercise_data: Dict):
        """Show exercise content"""
        self.current_exercise = exercise_data
        self.clear_layout(self.subtitle_layout)
        self.blank_inputs = []
        
        # Update progress
        if 'current' in exercise_data and 'total' in exercise_data:
            self.progress_label.setText(f"Exercise {exercise_data['current']}/{exercise_data['total']}")
        
        # Create subtitle display
        subtitle_text = exercise_data.get('original_text', '')
        blanks_info = exercise_data.get('blanks', [])
        
        # Build subtitle display with input boxes
        self.create_interactive_subtitle(subtitle_text, blanks_info)
        
        # Enable confirm button
        self.confirm_button.setEnabled(True)
        self.next_button.setVisible(False)
        
        # Focus on first input box
        if self.blank_inputs:
            self.blank_inputs[0].setFocus()
    
    def create_interactive_subtitle(self, text: str, blanks: List[Dict]):
        """Create interactive display for complete sentence"""
        # If no text, show error message
        if not text.strip():
            error_label = QLabel("❌ Exercise data error: No subtitle text found")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #dc3545;
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 6px;
                    padding: 15px;
                }
            """)
            self.subtitle_layout.addWidget(error_label)
            return
        
        # Create display container for complete sentence
        self._create_complete_sentence_display(text, blanks)
    
    def _create_complete_sentence_display(self, text: str, blanks: List[Dict]):
        """Create display for complete sentence, maintaining sentence integrity"""
        # Create main sentence container
        sentence_container = QWidget()
        sentence_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 2px solid #e3f2fd;
                border-radius: 12px;
                padding: 20px 24px;
                margin: 8px 0px;
            }
            QWidget:hover {
                border-color: #2196f3;
            }
        """)
        
        # Use flow layout to display complete sentence
        flow_layout = FlowLayout(margin=0, hspacing=8, vspacing=12)
        sentence_container.setLayout(flow_layout)
        
        # Split text into words
        words = text.split()
        
        # Create mapping for blank positions
        blank_positions = {blank['position']: blank for blank in blanks}
        
        # Create display elements word by word
        for word_index, word in enumerate(words):
            if word_index in blank_positions:
                # Create blank input box
                blank_info = blank_positions[word_index]
                input_widget = BlankInputWidget(
                    expected_answer=blank_info['answer'],
                    placeholder=f"({len(blank_info['answer'])})"
                )
                input_widget.answer_submitted.connect(self.on_answer_submitted)
                self.blank_inputs.append(input_widget)
                flow_layout.addWidget(input_widget)
            else:
                # Create normal text label
                word_label = QLabel(word)
                word_label.setStyleSheet("""
                    QLabel {
                        font-size: 18px;
                        font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
                        color: #2c3e50;
                        background: transparent;
                        border: none;
                        padding: 4px 2px;
                        line-height: 1.6;
                    }
                """)
                flow_layout.addWidget(word_label)
        
        # Add sentence hint information (if any)
        if blanks:
            hint_text = f"💡 Please fill in {len(blanks)} blanks"
            hint_label = QLabel(hint_text)
            hint_label.setAlignment(Qt.AlignCenter)
            hint_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #6c757d;
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 6px;
                    padding: 8px 12px;
                    margin-top: 12px;
                }
            """)
            
            # Create vertical layout containing sentence and hints
            main_container = QWidget()
            main_layout = QVBoxLayout(main_container)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(8)
            main_layout.addWidget(sentence_container)
            main_layout.addWidget(hint_label)
            
            self.subtitle_layout.addWidget(main_container)
        else:
            self.subtitle_layout.addWidget(sentence_container)
    
    def _get_sentence_preview(self, text: str, max_length: int = 100) -> str:
        """Get sentence preview for displaying abbreviated version of complete sentence"""
        if len(text) <= max_length:
            return text
        
        # Truncate at word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # If truncation point won't lose too much content
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def on_answer_submitted(self, answer: str):
        """Handle answer submission"""
        # Check if all answers are filled
        if self.are_all_answers_filled():
            self.check_answers()
    
    def are_all_answers_filled(self) -> bool:
        """Check if all answers are filled"""
        for input_widget in self.blank_inputs:
            if not input_widget.text().strip():
                return False
        return True
    
    def are_all_answers_correct(self) -> bool:
        """Check if all answers are correct"""
        for input_widget in self.blank_inputs:
            if not input_widget.is_correct:
                return False
        return True
    
    def check_answers(self):
        """Check answers"""
        if not self.blank_inputs:
            return
        # Prevent duplicate triggering or recursive calls
        if getattr(self, '_checking_answers', False):
            return
        self._checking_answers = True
        
        # Submit all answers for validation
        for input_widget in self.blank_inputs:
            input_widget.submit_without_signal()
        
        # Check results
        if self.are_all_answers_correct():
            self.show_success_state()
            # Quickly proceed to next sentence after correct answer (brief delay to show feedback)
            QTimer.singleShot(400, self.next_exercise_requested.emit)
        else:
            self.show_retry_state()
        # Reset check flag
        self._checking_answers = False
    
    def show_success_state(self):
        """Show success state"""
        self.confirm_button.setEnabled(False)
        self.next_button.setVisible(True)
        
        # Can add success animation or sound effect
        self.title_label.setText("✅ Correct answer!")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #28a745;
                background: transparent;
                border: none;
            }
        """)
        
        # Auto-restore title after 3 seconds
        QTimer.singleShot(3000, self.reset_title)
    
    def show_retry_state(self):
        """Show retry state"""
        self.title_label.setText("❌ Please check answers and retry")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #dc3545;
                background: transparent;
                border: none;
            }
        """)
        
        # Auto-restore title after 3 seconds
        QTimer.singleShot(3000, self.reset_title)
    
    def reset_title(self):
        """Reset title"""
        self.title_label.setText("Subtitle Exercise Area")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                background: transparent;
                border: none;
            }
        """)
    
    def show_all_answers(self):
        """Show all answers"""
        for input_widget in self.blank_inputs:
            input_widget.show_answer()
        
        self.confirm_button.setEnabled(False)
        self.next_button.setVisible(True)
        self.show_answer_requested.emit()
    
    def clear_layout(self, layout):
        """Clear layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())
