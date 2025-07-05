#!/usr/bin/env python3
"""
Скрипт для запуска Obsidian to EPUB Converter
"""
import sys
import webbrowser
from threading import Timer
from app import app


def open_browser():
    """Открывает браузер через 1.5 секунды после запуска"""
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    print("🚀 Запуск Obsidian to EPUB Converter...")
    print("📱 Приложение будет доступно по адресу: http://localhost:5000")
    print("🛑 Для остановки нажмите Ctrl+C")
    
    # Открываем браузер через 1.5 секунды
    Timer(1.5, open_browser).start()
    
    try:
        app.run(debug=True, port=5000, host='0.0.0.0')
    except KeyboardInterrupt:
        print("\n👋 Приложение остановлено")
        sys.exit(0) 