#!/usr/bin/env python3
"""
Скрипт для запуска Obsidian to EPUB Converter
"""
import sys
import os
import webbrowser
from threading import Timer
from app import app
import requests
import time


def setup_default_project():
    """Автоматически устанавливает проект с папкой Obsidian"""
    vault_path = ("/Users/esolovyov/Library/Mobile Documents/iCloud~md~obsidian/"
                  "Documents/Evgeniy Solovyov Obsidian/")
    
    # Проверяем что папка существует
    if os.path.exists(vault_path):
        print(f"📁 Автоматически выбираю папку Obsidian: {vault_path}")
        
        # Ждем пока сервер запустится
        time.sleep(2)
        
        try:
            # Устанавливаем проект через API
            response = requests.post('http://localhost:5002/api/set-project', 
                                     json={
                                         'path': vault_path,
                                         'name': 'Evgeniy Solovyov Obsidian'
                                     })
            
            if response.status_code == 200:
                print("✅ Папка Obsidian успешно выбрана!")
            else:
                print(f"⚠️  Ошибка при выборе папки: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Не удалось автоматически выбрать папку: {e}")
    else:
        print(f"⚠️  Папка Obsidian не найдена: {vault_path}")


def open_browser():
    """Открывает браузер через 1.5 секунды после запуска"""
    webbrowser.open('http://localhost:5002')


if __name__ == '__main__':
    print("🚀 Запуск Obsidian to EPUB Converter...")
    print("📱 Приложение будет доступно по адресу: http://localhost:5002")
    print("🛑 Для остановки нажмите Ctrl+C")
    
    # Открываем браузер через 1.5 секунды
    Timer(1.5, open_browser).start()
    
    # Устанавливаем проект через 3 секунды
    Timer(3.0, setup_default_project).start()
    
    try:
        app.run(debug=True, port=5002, host='0.0.0.0')
    except KeyboardInterrupt:
        print("\n👋 Приложение остановлено")
        sys.exit(0) 