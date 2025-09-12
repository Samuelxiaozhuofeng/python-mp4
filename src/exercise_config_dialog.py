"""
练习配置对话框
允许用户配置学习水平、挖空重点和练习难度
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
    """练习配置对话框"""
    
    # 信号定义
    exercises_generated = Signal(list)  # 练习生成完成信号
    
    def __init__(self, parent=None, subtitles=None):
        super().__init__(parent)
        self.subtitles = subtitles or []
        self.ai_thread = None
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("练习配置")
        self.setMinimumSize(500, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 语言配置
        language_group = QGroupBox("语言设置")
        language_layout = QFormLayout(language_group)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            "English (英语)",
            "Spanish (西班牙语)",
            "French (法语)",
            "German (德语)",
            "Italian (意大利语)",
            "Portuguese (葡萄牙语)",
            "Russian (俄语)",
            "Japanese (日语)",
            "Korean (韩语)",
            "Chinese (中文)",
            "Other (其他)"
        ])
        self.language_combo.setCurrentText("English (英语)")
        language_layout.addRow("学习语言:", self.language_combo)
        
        # 语言说明
        language_desc = QLabel(
            "选择您要学习的目标语言。AI将根据所选语言\n"
            "调整词汇难度和语法重点。"
        )
        language_desc.setStyleSheet("color: #666; font-size: 12px;")
        language_layout.addRow("", language_desc)
        
        layout.addWidget(language_group)
        
        # 学习水平配置
        level_group = QGroupBox("学习水平")
        level_layout = QFormLayout(level_group)
        
        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "A1-A2 (初级)",
            "B1-B2 (中级)", 
            "C1-C2 (高级)"
        ])
        self.level_combo.setCurrentText("B1-B2 (中级)")
        level_layout.addRow("语言水平:", self.level_combo)
        
        # 水平说明
        level_desc = QLabel(
            "• A1-A2: 基础词汇，简单语法\n"
            "• B1-B2: 常用词汇，中等语法\n" 
            "• C1-C2: 高级词汇，复杂语法"
        )
        level_desc.setStyleSheet("color: #666; font-size: 12px;")
        level_layout.addRow("", level_desc)
        
        layout.addWidget(level_group)
        
        # 挖空重点配置
        focus_group = QGroupBox("挖空重点")
        focus_layout = QVBoxLayout(focus_group)
        
        # 按词性挖空
        pos_label = QLabel("按词性挖空:")
        pos_label.setFont(QFont("", 10, QFont.Bold))
        focus_layout.addWidget(pos_label)
        
        pos_layout = QHBoxLayout()
        self.noun_check = QCheckBox("名词")
        self.verb_check = QCheckBox("动词") 
        self.adj_check = QCheckBox("形容词")
        self.prep_check = QCheckBox("介词")
        
        # 默认选中名词和动词
        self.noun_check.setChecked(True)
        self.verb_check.setChecked(True)
        
        pos_layout.addWidget(self.noun_check)
        pos_layout.addWidget(self.verb_check)
        pos_layout.addWidget(self.adj_check)
        pos_layout.addWidget(self.prep_check)
        pos_layout.addStretch()
        focus_layout.addLayout(pos_layout)
        
        # 按难度挖空
        diff_label = QLabel("按词汇难度:")
        diff_label.setFont(QFont("", 10, QFont.Bold))
        focus_layout.addWidget(diff_label)
        
        diff_layout = QHBoxLayout()
        self.common_check = QCheckBox("高频词")
        self.advanced_check = QCheckBox("低频词/核心词汇")
        
        # 默认选中核心词汇
        self.advanced_check.setChecked(True)
        
        diff_layout.addWidget(self.common_check)
        diff_layout.addWidget(self.advanced_check)
        diff_layout.addStretch()
        focus_layout.addLayout(diff_layout)
        
        # 按语法点挖空
        grammar_label = QLabel("按语法点:")
        grammar_label.setFont(QFont("", 10, QFont.Bold))
        focus_layout.addWidget(grammar_label)
        
        grammar_layout = QHBoxLayout()
        self.tense_check = QCheckBox("动词时态")
        self.modal_check = QCheckBox("情态动词")
        self.phrase_check = QCheckBox("固定搭配")
        
        grammar_layout.addWidget(self.tense_check)
        grammar_layout.addWidget(self.modal_check)
        grammar_layout.addWidget(self.phrase_check)
        grammar_layout.addStretch()
        focus_layout.addLayout(grammar_layout)
        
        layout.addWidget(focus_group)
        
        # 挖空密度配置
        density_group = QGroupBox("挖空密度")
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
        
        density_layout.addRow("挖空比例:", density_slider_layout)
        
        # 密度说明
        density_desc = QLabel(
            "• 10-20%: 简单练习，适合初学者\n"
            "• 20-30%: 中等练习，平衡难度\n"
            "• 30-50%: 高难度练习，深度学习"
        )
        density_desc.setStyleSheet("color: #666; font-size: 12px;")
        density_layout.addRow("", density_desc)
        
        layout.addWidget(density_group)
        
        # 预览信息
        preview_group = QGroupBox("生成预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.subtitle_count_label = QLabel(f"字幕数量: {len(self.subtitles)} 句")
        preview_layout.addWidget(self.subtitle_count_label)
        
        self.estimated_time_label = QLabel("预计生成时间: 计算中...")
        preview_layout.addWidget(self.estimated_time_label)
        
        # 更新预计时间
        self.update_estimated_time()
        
        layout.addWidget(preview_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.generate_button = QPushButton("生成练习")
        self.generate_button.clicked.connect(self.generate_exercises)
        self.generate_button.setDefault(True)
        button_layout.addWidget(self.generate_button)
        
        layout.addLayout(button_layout)
    
    def update_density_label(self, value):
        """更新密度标签"""
        self.density_label.setText(f"{value}%")
        self.update_estimated_time()
    
    def update_estimated_time(self):
        """更新预计生成时间"""
        if not self.subtitles:
            self.estimated_time_label.setText("预计生成时间: 0秒")
            return
        
        # 根据字幕数量估算时间 (每句约2-3秒)
        estimated_seconds = len(self.subtitles) * 2.5
        
        if estimated_seconds < 60:
            time_str = f"{int(estimated_seconds)} 秒"
        else:
            minutes = int(estimated_seconds // 60)
            seconds = int(estimated_seconds % 60)
            time_str = f"{minutes} 分 {seconds} 秒"
        
        self.estimated_time_label.setText(f"预计生成时间: {time_str}")
    
    def get_selected_focus_areas(self) -> List[str]:
        """获取选中的挖空重点"""
        areas = []
        
        # 词性类型
        if self.noun_check.isChecked():
            areas.append("名词")
        if self.verb_check.isChecked():
            areas.append("动词")
        if self.adj_check.isChecked():
            areas.append("形容词")
        if self.prep_check.isChecked():
            areas.append("介词")
        
        # 难度类型
        if self.common_check.isChecked():
            areas.append("高频词")
        if self.advanced_check.isChecked():
            areas.append("低频词")
        
        # 语法类型
        if self.tense_check.isChecked():
            areas.append("动词时态")
        if self.modal_check.isChecked():
            areas.append("情态动词")
        if self.phrase_check.isChecked():
            areas.append("固定搭配")
        
        return areas if areas else ["名词", "动词"]  # 默认值
    
    def get_config(self) -> Dict:
        """获取当前配置"""
        language_text = self.language_combo.currentText()
        language = language_text.split()[0]  # 提取语言名称，如English, Spanish等
        
        level_text = self.level_combo.currentText()
        level = level_text.split()[0]  # 提取A1-A2, B1-B2, C1-C2
        
        return {
            'language': language,
            'level': level,
            'focus_areas': self.get_selected_focus_areas(),
            'blank_density': self.density_slider.value()
        }
    
    def load_config(self):
        """加载保存的配置"""
        exercise_config = config.get_exercise_config()
        
        # 设置学习语言
        language = exercise_config.get('language', 'English')
        for i in range(self.language_combo.count()):
            if language in self.language_combo.itemText(i):
                self.language_combo.setCurrentIndex(i)
                break
        
        # 设置学习水平
        level = exercise_config.get('level', 'B1-B2')
        for i in range(self.level_combo.count()):
            if level in self.level_combo.itemText(i):
                self.level_combo.setCurrentIndex(i)
                break
        
        # 设置挖空重点
        focus_areas = exercise_config.get('focus_areas', ['名词', '动词'])
        
        self.noun_check.setChecked('名词' in focus_areas)
        self.verb_check.setChecked('动词' in focus_areas)
        self.adj_check.setChecked('形容词' in focus_areas)
        self.prep_check.setChecked('介词' in focus_areas)
        self.common_check.setChecked('高频词' in focus_areas)
        self.advanced_check.setChecked('低频词' in focus_areas)
        self.tense_check.setChecked('动词时态' in focus_areas)
        self.modal_check.setChecked('情态动词' in focus_areas)
        self.phrase_check.setChecked('固定搭配' in focus_areas)
        
        # 设置挖空密度
        density = exercise_config.get('blank_density', 25)
        self.density_slider.setValue(density)
    
    def save_config(self):
        """保存配置"""
        exercise_config = self.get_config()
        config.set_exercise_config(
            exercise_config['language'],
            exercise_config['level'],
            exercise_config['focus_areas'],
            exercise_config['blank_density']
        )
        config.save_config()
    
    def generate_exercises(self):
        """生成练习"""
        if not self.subtitles:
            QMessageBox.warning(self, "警告", "没有字幕数据，请先导入字幕文件")
            return
        
        # 验证AI配置
        ai_config = config.get_ai_config()
        if not ai_config.get('api_key') or not ai_config.get('api_url'):
            QMessageBox.warning(self, "警告", 
                               "请先配置AI服务\n\n"
                               "点击菜单 '设置' → 'AI服务配置' 进行配置")
            return
        
        # 验证选择项
        if not self.get_selected_focus_areas():
            QMessageBox.warning(self, "警告", "请至少选择一种挖空重点")
            return
        
        # 保存配置
        self.save_config()
        
        # 开始生成
        self.start_generation()
    
    def start_generation(self):
        """开始生成练习"""
        self.generate_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动AI生成线程
        exercise_config = self.get_config()
        self.ai_thread = AIExerciseThread(self.subtitles, exercise_config)
        
        # 连接信号
        self.ai_thread.generation_started.connect(self.on_generation_started)
        self.ai_thread.generation_finished.connect(self.on_generation_finished)
        self.ai_thread.progress_updated.connect(self.progress_bar.setValue)
        
        self.ai_thread.start()
    
    def on_generation_started(self):
        """生成开始"""
        self.generate_button.setText("生成中...")
    
    def on_generation_finished(self, success: bool, message: str, exercises: list):
        """生成完成"""
        self.generate_button.setEnabled(True)
        self.generate_button.setText("生成练习")
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.exercises_generated.emit(exercises)
            self.accept()
        else:
            QMessageBox.critical(self, "失败", message)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 如果生成线程正在运行，先停止它
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.terminate()
            self.ai_thread.wait()
        event.accept()
