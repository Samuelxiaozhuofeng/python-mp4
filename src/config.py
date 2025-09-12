"""
Configuration management module
Handles loading, saving and validation of application configuration
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """Configuration manager"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config_path = Path(config_file)
        self._config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Configuration file loading failed: {e}")
                self._config = self.get_default_config()
        else:
            self._config = self.get_default_config()
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Configuration file saving failed: {e}")
            return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "ai_service": {
                "api_key": "",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-3.5-turbo",
                "timeout": 30
            },
            "exercise": {
                "language": "English",
                "level": "B1-B2",
                "focus_areas": ["nouns", "verbs"],
                "blank_density": 25
            },
            "ui": {
                "window_width": 1200,
                "window_height": 800,
                "theme": "light"
            },
            "video": {
                "volume": 50,
                "subtitle_offset": 0.0
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value, supports dot-separated nested keys"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value, supports dot-separated nested keys"""
        keys = key.split('.')
        config = self._config
        
        # Navigate to target dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set value
        config[keys[-1]] = value
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI service configuration"""
        return self.get('ai_service', {})
    
    def set_ai_config(self, api_key: str, api_url: str, model: str) -> None:
        """Set AI service configuration"""
        self.set('ai_service.api_key', api_key)
        self.set('ai_service.api_url', api_url)
        self.set('ai_service.model', model)
    
    def get_exercise_config(self) -> Dict[str, Any]:
        """Get exercise configuration"""
        return self.get('exercise', {})
    
    def set_exercise_config(self, language: str, level: str, focus_areas: list, blank_density: int) -> None:
        """Set exercise configuration"""
        self.set('exercise.language', language)
        self.set('exercise.level', level)
        self.set('exercise.focus_areas', focus_areas)
        self.set('exercise.blank_density', blank_density)

# Global configuration instance
config = ConfigManager()
