"""
AI service configuration dialog
Allows users to configure custom AI API settings
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
    """AI API connection test thread"""
    
    # Signal definition
    test_completed = Signal(bool, str)  # Test completion signal (success/failure, message)
    
    def __init__(self, api_key, api_url, model):
        super().__init__()
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
    
    def run(self):
        """Execute API test"""
        try:
            # Build test request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": "Test connection"}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            # Send test request
            response = requests.post(
                self.api_url, 
                json=data, 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    self.test_completed.emit(True, "Connection successful! API response normal.")
                else:
                    self.test_completed.emit(False, "API response format abnormal")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                self.test_completed.emit(False, error_msg)
                
        except requests.exceptions.Timeout:
            self.test_completed.emit(False, "Connection timeout, please check network or API URL")
        except requests.exceptions.ConnectionError:
            self.test_completed.emit(False, "Unable to connect to API server")
        except Exception as e:
            self.test_completed.emit(False, f"Test failed: {str(e)}")

class AIConfigDialog(QDialog):
    """AI service configuration dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.test_thread = None
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup user interface"""
        self.setWindowTitle("AI Service Configuration")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # API configuration group
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout(api_group)
        
        # API Key input
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Enter your API key")
        api_layout.addRow("API Key:", self.api_key_edit)
        
        # Show/hide API Key button
        show_key_layout = QHBoxLayout()
        self.show_key_checkbox = QCheckBox("Show API Key")
        self.show_key_checkbox.toggled.connect(self.toggle_api_key_visibility)
        show_key_layout.addWidget(self.show_key_checkbox)
        show_key_layout.addStretch()
        api_layout.addRow("", show_key_layout)
        
        # API URL input
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("https://api.openai.com/v1/chat/completions")
        api_layout.addRow("API URL:", self.api_url_edit)
        
        # Model selection
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
        api_layout.addRow("AI Model:", self.model_combo)
        
        # Timeout settings
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" seconds")
        api_layout.addRow("Request Timeout:", self.timeout_spin)
        
        layout.addWidget(api_group)
        
        # Connection test group
        test_group = QGroupBox("Connection Test")
        test_layout = QVBoxLayout(test_group)
        
        # Test button and progress bar
        test_button_layout = QHBoxLayout()
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        test_button_layout.addWidget(self.test_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        test_button_layout.addWidget(self.progress_bar)
        
        test_layout.addLayout(test_button_layout)
        
        # Test result display
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(80)
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("Click 'Test Connection' to verify API configuration...")
        test_layout.addWidget(self.result_text)
        
        layout.addWidget(test_group)
        
        # Preset configuration group
        preset_group = QGroupBox("Preset Configuration")
        preset_layout = QHBoxLayout(preset_group)
        
        openai_btn = QPushButton("OpenAI Official")
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
        
        # Button area
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_config)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def toggle_api_key_visibility(self, visible):
        """Toggle API Key visibility"""
        if visible:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
    
    def load_preset(self, preset_type):
        """Load preset configuration"""
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
            
            # Show information message
            if preset_type == "azure":
                QMessageBox.information(self, "Information", 
                    "Azure OpenAI configuration requires modifying the resource name and deployment name in the URL")
            elif preset_type == "claude":
                QMessageBox.information(self, "Information", 
                    "Claude API uses a different request format, please ensure your API key is correct")
    
    def test_connection(self):
        """Test API connection"""
        # Validate input
        if not self.api_key_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Please enter API Key")
            return
        
        if not self.api_url_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Please enter API URL")
            return
        
        if not self.model_combo.currentText().strip():
            QMessageBox.warning(self, "Warning", "Please select AI model")
            return
        
        # Start test
        self.test_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress bar
        self.result_text.clear()
        self.result_text.append("Testing connection...")
        
        # Create and start test thread
        self.test_thread = AITestThread(
            self.api_key_edit.text().strip(),
            self.api_url_edit.text().strip(),
            self.model_combo.currentText().strip()
        )
        self.test_thread.test_completed.connect(self.on_test_completed)
        self.test_thread.start()
    
    def on_test_completed(self, success, message):
        """Test completion callback"""
        self.test_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.result_text.setStyleSheet("QTextEdit { color: green; }")
            self.result_text.setText(f"✓ {message}")
        else:
            self.result_text.setStyleSheet("QTextEdit { color: red; }")
            self.result_text.setText(f"✗ {message}")
        
        # Clean up thread
        if self.test_thread:
            self.test_thread.deleteLater()
            self.test_thread = None
    
    def load_config(self):
        """Load current configuration"""
        ai_config = config.get_ai_config()
        
        self.api_key_edit.setText(ai_config.get('api_key', ''))
        self.api_url_edit.setText(ai_config.get('api_url', 'https://api.openai.com/v1/chat/completions'))
        self.model_combo.setCurrentText(ai_config.get('model', 'gpt-3.5-turbo'))
        self.timeout_spin.setValue(ai_config.get('timeout', 30))
    
    def save_config(self):
        """Save configuration"""
        # Validate input
        if not self.api_key_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Please enter API Key")
            return
        
        if not self.api_url_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Please enter API URL")
            return
        
        if not self.model_combo.currentText().strip():
            QMessageBox.warning(self, "Warning", "Please select AI model")
            return
        
        # Save configuration
        config.set_ai_config(
            self.api_key_edit.text().strip(),
            self.api_url_edit.text().strip(),
            self.model_combo.currentText().strip()
        )
        config.set('ai_service.timeout', self.timeout_spin.value())
        
        if config.save_config():
            QMessageBox.information(self, "Success", "AI service configuration saved")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Configuration save failed")
    
    def closeEvent(self, event):
        """Close event"""
        # If test thread is running, stop it first
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.terminate()
            self.test_thread.wait()
        event.accept()
