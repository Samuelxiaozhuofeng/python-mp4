"""
配置管理模块
处理应用配置的加载、保存和验证
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config_path = Path(config_file)
        self._config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"配置文件加载失败: {e}")
                self._config = self.get_default_config()
        else:
            self._config = self.get_default_config()
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"配置文件保存失败: {e}")
            return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
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
                "focus_areas": ["名词", "动词"],
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
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        config = self._config
        
        # 导航到目标字典
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
    
    def get_ai_config(self) -> Dict[str, Any]:
        """获取AI服务配置"""
        return self.get('ai_service', {})
    
    def set_ai_config(self, api_key: str, api_url: str, model: str) -> None:
        """设置AI服务配置"""
        self.set('ai_service.api_key', api_key)
        self.set('ai_service.api_url', api_url)
        self.set('ai_service.model', model)
    
    def get_exercise_config(self) -> Dict[str, Any]:
        """获取练习配置"""
        return self.get('exercise', {})
    
    def set_exercise_config(self, language: str, level: str, focus_areas: list, blank_density: int) -> None:
        """设置练习配置"""
        self.set('exercise.language', language)
        self.set('exercise.level', level)
        self.set('exercise.focus_areas', focus_areas)
        self.set('exercise.blank_density', blank_density)

# 全局配置实例
config = ConfigManager()
