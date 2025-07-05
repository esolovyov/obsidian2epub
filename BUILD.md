# Сборка плагина Obsidian to EPUB

## 🛠️ Требования для разработки

- Node.js 16+
- npm или yarn
- TypeScript
- Python 3.7+
- pandoc

## 📦 Подготовка окружения

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/your-repo/obsidian-to-epub-plugin.git
cd obsidian-to-epub-plugin
```

2. **Установите зависимости:**
```bash
npm install
```

3. **Установите Python зависимости:**
```bash
cd server
pip install -r requirements.txt
cd ..
```

## 🔨 Команды сборки

### Разработка
```bash
npm run dev
```
Запускает сборку в режиме разработки с watch mode.

### Продакшен
```bash
npm run build
```
Создает оптимизированную сборку для релиза.

## 📁 Структура проекта

```
obsidian-to-epub-plugin/
├── main.ts              # Основной код плагина
├── manifest.json        # Манифест плагина
├── package.json         # Node.js зависимости
├── tsconfig.json        # Конфигурация TypeScript
├── esbuild.config.mjs   # Конфигурация сборки
├── server/              # Python backend
│   ├── app.py          # Flask сервер
│   ├── database.py     # Работа с БД
│   ├── requirements.txt # Python зависимости
│   └── templates/      # HTML шаблоны
│       └── index.html
└── README-plugin.md    # Документация плагина
```

## 🚀 Тестирование

### Локальная установка для тестирования

1. **Соберите плагин:**
```bash
npm run build
```

2. **Создайте папку плагина в vault:**
```bash
mkdir -p /path/to/your/vault/.obsidian/plugins/obsidian-to-epub-plugin
```

3. **Скопируйте файлы:**
```bash
cp main.js manifest.json /path/to/your/vault/.obsidian/plugins/obsidian-to-epub-plugin/
cp -r server /path/to/your/vault/.obsidian/plugins/obsidian-to-epub-plugin/
```

4. **Перезапустите Obsidian** и включите плагин в настройках.

### Быстрая установка для разработки

Создайте символические ссылки для быстрого тестирования:

```bash
# Linux/macOS
ln -s $(pwd) /path/to/your/vault/.obsidian/plugins/obsidian-to-epub-plugin

# Windows
mklink /D "C:\path\to\your\vault\.obsidian\plugins\obsidian-to-epub-plugin" "%cd%"
```

## 🔧 Настройка окружения разработки

### VS Code
Рекомендуемые расширения:
- TypeScript и JavaScript
- Python
- Obsidian Plugin Development

### Конфигурация .vscode/settings.json:
```json
{
    "typescript.preferences.includePackageJsonAutoImports": "off",
    "typescript.suggest.autoImports": false,
    "python.defaultInterpreterPath": "./server/venv/bin/python"
}
```

## 🐛 Отладка

### Логи TypeScript плагина
Откройте Developer Console в Obsidian: `Ctrl+Shift+I` (Cmd+Option+I на Mac)

### Логи Python сервера
Проверьте вывод в консоли где запущен Obsidian или в логах плагина.

### Проверка работы сервера
```bash
curl http://localhost:5002/api/current-project
```

## 📋 Чеклист перед релизом

- [ ] Все тесты проходят
- [ ] Код собирается без ошибок
- [ ] Плагин работает в тестовом vault
- [ ] Обновлена документация
- [ ] Проверена совместимость с последней версией Obsidian
- [ ] Обновлен файл `manifest.json` с новой версией
- [ ] Созданы release notes

## 🚀 Публикация

1. **Обновите версию:**
```bash
npm run version
```

2. **Создайте tag:**
```bash
git tag v1.0.0
git push origin v1.0.0
```

3. **Создайте релиз на GitHub** с файлами:
   - `main.js`
   - `manifest.json`
   - `styles.css` (если есть)

## ⚡ Горячие клавиши для разработки

- `npm run dev` - сборка в режиме разработки
- `npm run build` - продакшен сборка
- `Ctrl+Shift+I` - Developer Console в Obsidian
- `Ctrl+R` - перезагрузка плагина в Obsidian

## 📚 Полезные ресурсы

- [Obsidian Plugin API](https://github.com/obsidianmd/obsidian-api)
- [Plugin Developer Docs](https://docs.obsidian.md/Plugins/Getting+started/Build+a+plugin)
- [Community Plugin Guidelines](https://docs.obsidian.md/Plugins/Releasing/Plugin+guidelines)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Удачной разработки! 🚀** 