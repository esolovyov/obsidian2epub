#!/bin/bash

echo "🚀 Установка Obsidian to EPUB Converter"
echo "======================================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Пожалуйста, установите Python 3.7+"
    exit 1
fi

echo "✅ Python3 найден: $(python3 --version)"

# Проверка pandoc
if ! command -v pandoc &> /dev/null; then
    echo "❌ pandoc не найден."
    echo "📦 Для установки pandoc:"
    echo "   macOS: brew install pandoc"
    echo "   Ubuntu/Debian: sudo apt-get install pandoc"
    echo "   Windows: https://pandoc.org/installing.html"
    exit 1
fi

echo "✅ pandoc найден: $(pandoc --version | head -1)"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "🔧 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip install -r requirements.txt

echo ""
echo "✅ Установка завершена!"
echo "🚀 Для запуска приложения используйте:"
echo "   ./run.py"
echo "   или"
echo "   source venv/bin/activate && python app.py"
echo ""
echo "📱 Приложение будет доступно по адресу: http://localhost:5000" 