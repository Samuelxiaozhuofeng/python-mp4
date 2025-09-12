#!/usr/bin/env python3
"""
ListenFill AI - Main Entry Point
Personalized video listening fill-in-the-blank exercise application
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

def main():
    """Main function"""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("ListenFill AI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ListenFill")
    
    # Set application attributes
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    try:
        # Import and create main window
        from main_window import MainWindow
        
        # Create main window
        window = MainWindow()
        window.show()
        
        # Run application
        return app.exec()
        
    except ImportError as e:
        QMessageBox.critical(None, "Import Error", f"Unable to import required modules: {e}")
        return 1
    except Exception as e:
        QMessageBox.critical(None, "Startup Error", f"Application startup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
