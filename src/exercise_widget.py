"""
交互式练习组件
实现字幕显示、挖空练习和用户交互功能
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
    """挖空输入框组件"""
    
    # 信号定义
    answer_submitted = Signal(str)  # 答案提交信号
    
    def __init__(self, expected_answer: str, placeholder: str = ""):
        super().__init__()
        self.expected_answer = expected_answer.strip().lower()
        self.is_correct = False
        self.setup_ui(placeholder)
    
    def setup_ui(self, placeholder: str):
        """设置UI"""
        self.setPlaceholderText(placeholder or "输入答案...")
        # Dynamic width based on expected answer length for better rhythm
        approx = max(40, min(260, 12 * max(1, len(self.expected_answer)) + 20))
        self.setMinimumWidth(approx)
        self.setMaximumWidth(max(approx, 100))
        
        # 优化样式，更好地融入句子
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
        
        # 连接信号
        self.textChanged.connect(self.on_text_changed)
        self.returnPressed.connect(self.submit_answer)
    
    def on_text_changed(self, text):
        """文本改变时的处理"""
        # 实时验证答案
        if text.strip().lower() == self.expected_answer:
            self.set_correct_style()
            self.is_correct = True
        else:
            self.set_normal_style()
            self.is_correct = False
    
    def submit_answer(self):
        """提交答案"""
        answer = self.text().strip()
        self.answer_submitted.emit(answer)
        
        if answer.lower() == self.expected_answer:
            self.set_correct_style()
            self.is_correct = True
        else:
            self.set_incorrect_style()
            self.is_correct = False

    def submit_without_signal(self):
        """提交答案但不发出 answer_submitted 信号（用于程序化验证）"""
        answer = self.text().strip()
        if answer.lower() == self.expected_answer:
            self.set_correct_style()
            self.is_correct = True
        else:
            self.set_incorrect_style()
            self.is_correct = False
    
    def set_correct_style(self):
        """设置正确答案样式"""
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
        """设置错误答案样式"""
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
        """设置正常样式"""
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
        """显示正确答案"""
        self.setText(self.expected_answer.title())
        self.set_correct_style()
        self.is_correct = True
        self.setReadOnly(True)

class SubtitleExerciseWidget(QFrame):
    """字幕练习组件"""
    
    # 信号定义
    exercise_completed = Signal()  # 练习完成信号
    next_exercise_requested = Signal()  # 请求下一个练习信号
    hint_requested = Signal()  # 请求提示信号
    show_answer_requested = Signal()  # 请求显示答案信号
    replay_requested = Signal()  # 请求重播当前例句
    
    def __init__(self):
        super().__init__()
        self.current_exercise = None
        self.blank_inputs = []  # 存储所有输入框
        self._checking_answers = False  # 防止递归/重复检查
        self.setup_ui()
        self.setup_shortcuts()
    
    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        # 使用紧凑的主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # 大幅减少边距
        layout.setSpacing(5)  # 减少组件间距
        
        # 紧凑的标题区域
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(5, 0, 5, 0)  # 减少标题区域边距
        
        self.title_label = QLabel("字幕练习区")
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
        
        # 进度显示
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
        
        # 字幕显示区域（滚动区域） - 最大化空间利用
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(160)  # 提升默认可读空间
        
        # 优化滚动区域样式，减少边框占用
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
        layout.addWidget(scroll_area, 1)  # 设置拉伸因子，让内容区域占用更多空间
        
        # 紧凑的控制按钮区域
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 3, 0, 0)  # 减少按钮区域边距
        control_layout.setSpacing(8)  # 减少按钮间距
        
        # 提示按钮 - 紧凑样式
        self.hint_button = QPushButton("💡 提示")
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
        
        # 显示答案按钮 - 紧凑样式
        self.show_answer_button = QPushButton("👁️ 显示答案")
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

        # 重播当前例句按钮 - 紧凑样式
        self.replay_button = QPushButton("🔁 重播")
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
        self.replay_button.setToolTip("重播当前例句 (R)")
        self.replay_button.clicked.connect(self.replay_requested.emit)
        control_layout.addWidget(self.replay_button)

        control_layout.addStretch()
        
        # 确认按钮 - 紧凑样式
        self.confirm_button = QPushButton("✓ 确认")
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
        
        # 下一句按钮 - 紧凑样式
        self.next_button = QPushButton("▶️ 下一句")
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
        
        # 默认显示
        self.show_waiting_state()
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # Enter键确认
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.check_answers)
        # 支持数字键盘 Enter
        keypad_enter_shortcut = QShortcut(QKeySequence(Qt.Key_Enter), self)
        keypad_enter_shortcut.activated.connect(self.check_answers)
        
        # Ctrl+H 提示
        hint_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        hint_shortcut.activated.connect(self.hint_requested.emit)
        
        # Ctrl+A 显示答案
        answer_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        answer_shortcut.activated.connect(self.show_all_answers)
        # R 键重播当前例句
        replay_shortcut = QShortcut(QKeySequence(Qt.Key_R), self)
        replay_shortcut.activated.connect(self.replay_requested.emit)
    
    def show_waiting_state(self):
        """显示等待状态"""
        print("[DEBUG] show_waiting_state 被调用")
        self.clear_layout(self.subtitle_layout)
        
        waiting_label = QLabel("🎬 准备就绪\n\n请导入视频和字幕文件开始练习")
        waiting_label.setAlignment(Qt.AlignCenter)
        waiting_label.setMinimumHeight(80)  # 减少高度
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
        
        # 确保布局被正确应用
        self.subtitle_widget.setMinimumHeight(90)
        self.subtitle_layout.update()
        print("[DEBUG] 等待状态标签已添加并更新布局")
        
        self.confirm_button.setEnabled(False)
        self.next_button.setVisible(False)
    
    def show_subtitle_loaded(self, display_data: Dict):
        """显示字幕加载成功状态"""
        print(f"[DEBUG] SubtitleExerciseWidget.show_subtitle_loaded 被调用")
        print(f"[DEBUG] 接收到的数据: {display_data}")
        
        try:
            self.clear_layout(self.subtitle_layout)
            print("[DEBUG] 已清空布局")
            
            # 更新进度信息
            if 'total' in display_data:
                progress_text = f"共 {display_data['total']} 条字幕"
                self.progress_label.setText(progress_text)
                print(f"[DEBUG] 更新进度标签: {progress_text}")
            
            # 创建提示标签 - 紧凑样式
            info_text = display_data.get('original_text', '字幕已加载')
            print(f"[DEBUG] 创建信息标签，文本: {info_text}")
            
            info_label = QLabel(info_text)
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setWordWrap(True)
            info_label.setMinimumHeight(70)  # 减少高度
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
            print("[DEBUG] 信息标签已添加到布局")
            
            # 确保布局被正确应用
            self.subtitle_widget.setMinimumHeight(80)
            self.subtitle_layout.update()
            print("[DEBUG] 布局和尺寸已更新")
            
            # 禁用练习相关按钮
            self.confirm_button.setEnabled(False)
            self.next_button.setVisible(False)
            print("[DEBUG] 按钮状态已更新")
            
            # 强制刷新界面
            self.update()
            self.repaint()
            print("[DEBUG] 界面刷新完成")
            
        except Exception as e:
            print(f"[ERROR] show_subtitle_loaded 执行出错: {e}")
            import traceback
            traceback.print_exc()
    
    def show_exercise(self, exercise_data: Dict):
        """显示练习内容"""
        self.current_exercise = exercise_data
        self.clear_layout(self.subtitle_layout)
        self.blank_inputs = []
        
        # 更新进度
        if 'current' in exercise_data and 'total' in exercise_data:
            self.progress_label.setText(f"第 {exercise_data['current']}/{exercise_data['total']} 句")
        
        # 创建字幕显示
        subtitle_text = exercise_data.get('original_text', '')
        blanks_info = exercise_data.get('blanks', [])
        
        # 构建带输入框的字幕显示
        self.create_interactive_subtitle(subtitle_text, blanks_info)
        
        # 启用确认按钮
        self.confirm_button.setEnabled(True)
        self.next_button.setVisible(False)
        
        # 聚焦第一个输入框
        if self.blank_inputs:
            self.blank_inputs[0].setFocus()
    
    def create_interactive_subtitle(self, text: str, blanks: List[Dict]):
        """创建完整句子的交互式显示"""
        # 如果没有文本，显示错误信息
        if not text.strip():
            error_label = QLabel("❌ 练习数据错误：没有找到字幕文本")
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
        
        # 创建完整句子的显示容器
        self._create_complete_sentence_display(text, blanks)
    
    def _create_complete_sentence_display(self, text: str, blanks: List[Dict]):
        """创建完整句子的显示，保持句子完整性"""
        # 创建主句子容器
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
        
        # 使用流式布局来显示完整句子
        flow_layout = FlowLayout(margin=0, hspacing=8, vspacing=12)
        sentence_container.setLayout(flow_layout)
        
        # 分割文本为单词
        words = text.split()
        
        # 创建挖空位置的映射
        blank_positions = {blank['position']: blank for blank in blanks}
        
        # 逐词创建显示元素
        for word_index, word in enumerate(words):
            if word_index in blank_positions:
                # 创建挖空输入框
                blank_info = blank_positions[word_index]
                input_widget = BlankInputWidget(
                    expected_answer=blank_info['answer'],
                    placeholder=f"({len(blank_info['answer'])})"
                )
                input_widget.answer_submitted.connect(self.on_answer_submitted)
                self.blank_inputs.append(input_widget)
                flow_layout.addWidget(input_widget)
            else:
                # 创建普通文字标签
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
        
        # 添加句子提示信息（如果有）
        if blanks:
            hint_text = f"💡 请填入 {len(blanks)} 个空白处"
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
            
            # 创建包含句子和提示的垂直布局
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
        """获取句子预览，用于显示完整句子的缩略版"""
        if len(text) <= max_length:
            return text
        
        # 在单词边界截断
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # 如果截断点不会丢失太多内容
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def on_answer_submitted(self, answer: str):
        """处理答案提交"""
        # 检查是否所有答案都已填写
        if self.are_all_answers_filled():
            self.check_answers()
    
    def are_all_answers_filled(self) -> bool:
        """检查所有答案是否已填写"""
        for input_widget in self.blank_inputs:
            if not input_widget.text().strip():
                return False
        return True
    
    def are_all_answers_correct(self) -> bool:
        """检查所有答案是否正确"""
        for input_widget in self.blank_inputs:
            if not input_widget.is_correct:
                return False
        return True
    
    def check_answers(self):
        """检查答案"""
        if not self.blank_inputs:
            return
        # 防止重复触发或递归调用
        if getattr(self, '_checking_answers', False):
            return
        self._checking_answers = True
        
        # 提交所有答案进行验证
        for input_widget in self.blank_inputs:
            input_widget.submit_without_signal()
        
        # 检查结果
        if self.are_all_answers_correct():
            self.show_success_state()
            # 正确后快速进入下一句（短暂延迟以展示反馈）
            QTimer.singleShot(400, self.next_exercise_requested.emit)
        else:
            self.show_retry_state()
        # 结束检查标志复位
        self._checking_answers = False
    
    def show_success_state(self):
        """显示成功状态"""
        self.confirm_button.setEnabled(False)
        self.next_button.setVisible(True)
        
        # 可以添加成功动画或音效
        self.title_label.setText("✅ 回答正确！")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #28a745;
                background: transparent;
                border: none;
            }
        """)
        
        # 3秒后自动恢复标题
        QTimer.singleShot(3000, self.reset_title)
    
    def show_retry_state(self):
        """显示重试状态"""
        self.title_label.setText("❌ 请检查答案并重试")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #dc3545;
                background: transparent;
                border: none;
            }
        """)
        
        # 3秒后自动恢复标题
        QTimer.singleShot(3000, self.reset_title)
    
    def reset_title(self):
        """重置标题"""
        self.title_label.setText("字幕练习区")
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
        """显示所有答案"""
        for input_widget in self.blank_inputs:
            input_widget.show_answer()
        
        self.confirm_button.setEnabled(False)
        self.next_button.setVisible(True)
        self.show_answer_requested.emit()
    
    def clear_layout(self, layout):
        """清空布局"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())
