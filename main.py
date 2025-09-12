#!/usr/bin/env python3
"""
ListenFill AI - 主程序入口
个性化视频听力填空练习应用
"""
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("ListenFill AI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ListenFill")
    
    # 设置应用程序属性
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    try:
        # 导入并创建主窗口
        from main_window import MainWindow
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        # 运行应用程序
        return app.exec()
        
    except ImportError as e:
        QMessageBox.critical(None, "导入错误", f"无法导入必要的模块: {e}")
        return 1
    except Exception as e:
        QMessageBox.critical(None, "启动错误", f"应用程序启动失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
