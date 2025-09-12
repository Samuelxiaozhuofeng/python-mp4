"""
AI服务配置对话框
允许用户配置自定义AI API设置
"""
import requests
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QComboBox, QPushButton, QLabel, 
                               QGroupBox, QSpinBox, QTextEdit, QMessageBox,
                               QProgressBar, QCheckBox)
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont

from config import config

class AITestThread(QThread):
    """AI API连接测试线程"""
    
    # 信号定义
    test_completed = Signal(bool, str)  # 测试完成信号 (成功/失败, 消息)
    
    def __init__(self, api_key, api_url, model):
        super().__init__()
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
    
    def run(self):
        """执行API测试"""
        try:
            # 构建测试请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": "测试连接"}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            # 发送测试请求
            response = requests.post(
                self.api_url, 
                json=data, 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    self.test_completed.emit(True, "连接成功！API响应正常。")
                else:
                    self.test_completed.emit(False, "API响应格式异常")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                self.test_completed.emit(False, error_msg)
                
        except requests.exceptions.Timeout:
            self.test_completed.emit(False, "连接超时，请检查网络或API URL")
        except requests.exceptions.ConnectionError:
            self.test_completed.emit(False, "无法连接到API服务器")
        except Exception as e:
            self.test_completed.emit(False, f"测试失败: {str(e)}")

class AIConfigDialog(QDialog):
    """AI服务配置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.test_thread = None
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("AI服务配置")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # API配置组
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout(api_group)
        
        # API Key输入
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("输入您的API密钥")
        api_layout.addRow("API Key:", self.api_key_edit)
        
        # 显示/隐藏API Key按钮
        show_key_layout = QHBoxLayout()
        self.show_key_checkbox = QCheckBox("显示API Key")
        self.show_key_checkbox.toggled.connect(self.toggle_api_key_visibility)
        show_key_layout.addWidget(self.show_key_checkbox)
        show_key_layout.addStretch()
        api_layout.addRow("", show_key_layout)
        
        # API URL输入
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("https://api.openai.com/v1/chat/completions")
        api_layout.addRow("API URL:", self.api_url_edit)
        
        # 模型选择
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems([
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo-preview", 
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307"
        ])
        api_layout.addRow("AI模型:", self.model_combo)
        
        # 超时设置
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" 秒")
        api_layout.addRow("请求超时:", self.timeout_spin)
        
        layout.addWidget(api_group)
        
        # 连接测试组
        test_group = QGroupBox("连接测试")
        test_layout = QVBoxLayout(test_group)
        
        # 测试按钮和进度条
        test_button_layout = QHBoxLayout()
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        test_button_layout.addWidget(self.test_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        test_button_layout.addWidget(self.progress_bar)
        
        test_layout.addLayout(test_button_layout)
        
        # 测试结果显示
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(80)
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("点击'测试连接'验证API配置...")
        test_layout.addWidget(self.result_text)
        
        layout.addWidget(test_group)
        
        # 预设配置组
        preset_group = QGroupBox("预设配置")
        preset_layout = QHBoxLayout(preset_group)
        
        openai_btn = QPushButton("OpenAI官方")
        openai_btn.clicked.connect(lambda: self.load_preset("openai"))
        preset_layout.addWidget(openai_btn)
        
        azure_btn = QPushButton("Azure OpenAI")
        azure_btn.clicked.connect(lambda: self.load_preset("azure"))
        preset_layout.addWidget(azure_btn)
        
        claude_btn = QPushButton("Anthropic Claude")
        claude_btn.clicked.connect(lambda: self.load_preset("claude"))
        preset_layout.addWidget(claude_btn)
        
        preset_layout.addStretch()
        layout.addWidget(preset_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_config)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def toggle_api_key_visibility(self, visible):
        """切换API Key显示状态"""
        if visible:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
    
    def load_preset(self, preset_type):
        """加载预设配置"""
        presets = {
            "openai": {
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-3.5-turbo"
            },
            "azure": {
                "api_url": "https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2023-12-01-preview",
                "model": "gpt-3.5-turbo"
            },
            "claude": {
                "api_url": "https://api.anthropic.com/v1/messages",
                "model": "claude-3-sonnet-20240229"
            }
        }
        
        if preset_type in presets:
            preset = presets[preset_type]
            self.api_url_edit.setText(preset["api_url"])
            self.model_combo.setCurrentText(preset["model"])
            
            # 显示提示信息
            if preset_type == "azure":
                QMessageBox.information(self, "提示", 
                    "Azure OpenAI配置需要修改URL中的resource名称和deployment名称")
            elif preset_type == "claude":
                QMessageBox.information(self, "提示", 
                    "Claude API使用不同的请求格式，请确保您的API密钥正确")
    
    def test_connection(self):
        """测试API连接"""
        # 验证输入
        if not self.api_key_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入API Key")
            return
        
        if not self.api_url_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入API URL")
            return
        
        if not self.model_combo.currentText().strip():
            QMessageBox.warning(self, "警告", "请选择AI模型")
            return
        
        # 开始测试
        self.test_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.result_text.clear()
        self.result_text.append("正在测试连接...")
        
        # 创建并启动测试线程
        self.test_thread = AITestThread(
            self.api_key_edit.text().strip(),
            self.api_url_edit.text().strip(),
            self.model_combo.currentText().strip()
        )
        self.test_thread.test_completed.connect(self.on_test_completed)
        self.test_thread.start()
    
    def on_test_completed(self, success, message):
        """测试完成回调"""
        self.test_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.result_text.setStyleSheet("QTextEdit { color: green; }")
            self.result_text.setText(f"✓ {message}")
        else:
            self.result_text.setStyleSheet("QTextEdit { color: red; }")
            self.result_text.setText(f"✗ {message}")
        
        # 清理线程
        if self.test_thread:
            self.test_thread.deleteLater()
            self.test_thread = None
    
    def load_config(self):
        """加载当前配置"""
        ai_config = config.get_ai_config()
        
        self.api_key_edit.setText(ai_config.get('api_key', ''))
        self.api_url_edit.setText(ai_config.get('api_url', 'https://api.openai.com/v1/chat/completions'))
        self.model_combo.setCurrentText(ai_config.get('model', 'gpt-3.5-turbo'))
        self.timeout_spin.setValue(ai_config.get('timeout', 30))
    
    def save_config(self):
        """保存配置"""
        # 验证输入
        if not self.api_key_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入API Key")
            return
        
        if not self.api_url_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入API URL")
            return
        
        if not self.model_combo.currentText().strip():
            QMessageBox.warning(self, "警告", "请选择AI模型")
            return
        
        # 保存配置
        config.set_ai_config(
            self.api_key_edit.text().strip(),
            self.api_url_edit.text().strip(),
            self.model_combo.currentText().strip()
        )
        config.set('ai_service.timeout', self.timeout_spin.value())
        
        if config.save_config():
            QMessageBox.information(self, "成功", "AI服务配置已保存")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "配置保存失败")
    
    def closeEvent(self, event):
        """关闭事件"""
        # 如果测试线程正在运行，先停止它
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.terminate()
            self.test_thread.wait()
        event.accept()
