from flask import Flask, render_template, request, jsonify, send_file
import os
import tempfile
import shutil
import subprocess
from datetime import datetime
from database import Database
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Инициализация базы данных
db = Database()

# Глобальные переменные для кэширования
current_project = None
folder_tree_cache = None


@app.route('/')
def index():
    """Главная страница - единственная страница приложения"""
    return render_template('index.html')


@app.route('/api/set-project', methods=['POST'])
def set_project():
    """Установка активного проекта"""
    try:
        data = request.json
        project_path = data.get('path')
        project_name = data.get('name')
        
        if not project_path or not project_name:
            return jsonify({
                'success': False,
                'error': 'Не указан путь или имя проекта'
            })
        
        # Преобразуем относительный путь в абсолютный
        if not os.path.isabs(project_path):
            # Если путь относительный, пытаемся найти его в стандартных местах
            possible_paths = [
                os.path.join(os.path.expanduser('~'), project_path),
                os.path.join(
                    '/Users', os.getenv('USER', ''),
                    'Library/Mobile Documents/iCloud~md~obsidian/Documents',
                    project_path
                ),
                project_path
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    project_path = path
                    break
        
        if not os.path.exists(project_path):
            return jsonify({
                'success': False,
                'error': f'Папка не найдена: {project_path}'
            })
        
        # Создаем или обновляем проект
        project = db.create_or_update_project(project_name, project_path)
        db.set_active_project(project['id'])
        
        global current_project, folder_tree_cache
        current_project = project
        folder_tree_cache = None  # Сбрасываем кэш
        
        return jsonify({'success': True, 'project': project})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/current-project')
def get_current_project():
    """Получение текущего активного проекта"""
    try:
        global current_project
        if not current_project:
            current_project = db.get_active_project()
        
        return jsonify({'success': True, 'project': current_project})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/folder-tree')
def get_folder_tree():
    """Получение дерева папок с состояниями"""
    try:
        global current_project
        
        if not current_project:
            return jsonify({'success': False, 'error': 'Проект не выбран'})
        
        # Получаем состояния папок из базы данных
        folder_states = {}
        if current_project:
            states = db.get_folder_states(current_project['id'])
            folder_states = {
                state['folder_path']: state 
                for state in states
            }
        
        # Строим дерево папок
        tree = build_folder_tree(current_project['path'], folder_states)
        
        return jsonify({'success': True, 'tree': tree, 'folder_states': folder_states})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/set-folder-state', methods=['POST'])
def set_folder_state():
    """Установка состояния папки"""
    try:
        data = request.json
        folder_path = data.get('folder_path')
        is_selected = data.get('is_selected')
        is_expanded = data.get('is_expanded')
        
        global current_project
        if not current_project:
            return jsonify({'success': False, 'error': 'Проект не выбран'})
        
        # Сохраняем состояние папки
        db.set_folder_state(current_project['id'], folder_path, is_selected, is_expanded)
        
        # Если папка выбрана, добавляем её файлы в список
        if is_selected:
            files_data = get_files_from_folder(current_project['path'], folder_path)
            if files_data:
                db.add_files_to_project(current_project['id'], files_data)
        else:
            # Если папка не выбрана, удаляем её файлы из списка
            db.remove_files_from_folder(current_project['id'], folder_path)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/get-project-files')
def get_project_files():
    """Получение файлов проекта из базы данных"""
    try:
        global current_project
        if not current_project:
            return jsonify({'success': False, 'error': 'Проект не выбран'})
        
        # Получаем файлы из базы данных
        files = db.get_project_files(current_project['id'])
        
        return jsonify({'success': True, 'files': files})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/update-file-selection', methods=['POST'])
def update_file_selection():
    """Обновление выбора файлов"""
    try:
        data = request.json
        file_updates = data.get('files', [])
        
        global current_project
        if not current_project:
            return jsonify({'success': False, 'error': 'Проект не выбран'})
        
        # Обновляем состояние файлов
        for file_update in file_updates:
            file_id = file_update.get('id')
            is_selected = file_update.get('selected')
            if file_id is not None and is_selected is not None:
                db.toggle_file_inclusion(file_id, is_selected)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/update-file-order', methods=['POST'])
def update_file_order():
    """Обновление порядка файлов"""
    try:
        data = request.json
        file_orders = data.get('file_orders', [])
        
        global current_project
        if not current_project:
            return jsonify({'success': False, 'error': 'Проект не выбран'})
        
        # Обновляем порядок файлов в базе данных
        db.update_file_order(current_project['id'], file_orders)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/files-from-folders', methods=['POST'])
def get_files_from_folders():
    """Получение файлов из выбранных папок (legacy)"""
    try:
        data = request.json
        folder_paths = data.get('folders', [])
        
        global current_project
        if not current_project:
            return jsonify({'success': False, 'error': 'Проект не выбран'})
        
        base_path = current_project['path']
        all_files = []
        
        for folder_path in folder_paths:
            files_data = get_files_from_folder(base_path, folder_path)
            all_files.extend(files_data)
        
        # Сортируем по имени
        all_files.sort(key=lambda x: x['name'].lower())
        
        return jsonify({'success': True, 'files': all_files})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/export-epub', methods=['POST'])
def export_epub():
    """Экспорт выбранных файлов в EPUB"""
    try:
        data = request.json
        files = data.get('files', [])
        title = data.get('title', 'Мои заметки')
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'Не выбраны файлы для экспорта'
            })
        
        # Создаем временную папку
        with tempfile.TemporaryDirectory() as temp_dir:
            processed_files = []
            images_dir = os.path.join(temp_dir, 'images')
            os.makedirs(images_dir, exist_ok=True)
            
            # Собираем все изображения
            global current_project
            base_path = current_project['path'] if current_project else ''
            
            # Обрабатываем каждый файл
            for file_info in files:
                if not file_info.get('is_included'):
                    continue
                    
                file_path = file_info['path']
                if not os.path.exists(file_path):
                    continue
                
                # Читаем и обрабатываем содержимое файла
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Обрабатываем Obsidian-специфичные элементы и изображения
                content = process_obsidian_content(content, file_path, images_dir, base_path)
                
                # Не добавляем заголовок главы если в контенте уже есть заголовок
                if not content.lstrip().startswith('#'):
                    chapter_title = file_info['name'].replace('.md', '')
                    final_content = f"# {chapter_title}\n\n{content}"
                else:
                    final_content = content
                
                # Создаем временный файл
                temp_file = os.path.join(
                    temp_dir, 
                    f"{len(processed_files):03d}_{file_info['name']}"
                )
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                
                processed_files.append(temp_file)
            
            if not processed_files:
                return jsonify({
                    'success': False,
                    'error': 'Нет файлов для обработки'
                })
            
            # Создаем EPUB
            epub_filename = f"{title}.epub"
            epub_path = os.path.join(temp_dir, epub_filename)
            
            # Команда pandoc - убираем переносы страниц и копирайт
            cmd = [
                'pandoc',
                '--from', 'markdown',
                '--to', 'epub',
                '--output', epub_path,
                '--metadata', f'title={title}',
                '--metadata', f'date={datetime.now().strftime("%Y-%m-%d")}',
                '--resource-path', temp_dir
            ] + processed_files
            
            # Выполняем команду
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Ошибка pandoc: {result.stderr}'
                })
            
            # Копируем файл в папку загрузок
            downloads_dir = os.path.expanduser('~/Downloads')
            final_epub_path = os.path.join(downloads_dir, epub_filename)
            
            # Если файл уже существует, добавляем номер
            counter = 1
            while os.path.exists(final_epub_path):
                name_part = title
                final_epub_path = os.path.join(
                    downloads_dir, f"{name_part}_{counter}.epub"
                )
                counter += 1
            
            shutil.copy2(epub_path, final_epub_path)
            
            return jsonify({
                'success': True,
                'filename': os.path.basename(final_epub_path),
                'download_url': f'/download/{os.path.basename(final_epub_path)}',
                'path': final_epub_path
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание созданного EPUB файла"""
    try:
        downloads_dir = os.path.expanduser('~/Downloads')
        file_path = os.path.join(downloads_dir, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'Файл не найден'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500





def get_files_from_folder(base_path, folder_path):
    """Получение файлов из указанной папки"""
    files_data = []
    
    full_path = (os.path.join(base_path, folder_path)
                if not os.path.isabs(folder_path) else folder_path)
    
    if os.path.exists(full_path):
        # Получаем все MD файлы из папки и подпапок
        for root, dirs, files in os.walk(full_path):
            # Исключаем скрытые папки и папки Attachment
            dirs[:] = [d for d in dirs 
                      if not d.startswith('.') and
                      not d.endswith('_Attachment') and
                      not d.endswith('_Attachments') and
                      not d.endswith('Attachment')]
            
            for file in files:
                if (file.endswith('.md') and 
                    not file.endswith('_Attachment.md') and
                    not file.endswith('_Attachments.md') and
                    not file.endswith('Attachment.md')):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, base_path)
                    
                    file_info = {
                        'name': file,
                        'path': file_path,
                        'relative_path': relative_path,
                        'size': os.path.getsize(file_path),
                        'selected': True  # По умолчанию выбран
                    }
                    files_data.append(file_info)
    
    return files_data


def build_folder_tree(base_path, folder_states=None):
    """Построение дерева папок с состояниями"""
    if folder_states is None:
        folder_states = {}
    
    def scan_folder(path, relative_path=""):
        folder_info = {
            'name': (os.path.basename(path) if relative_path
                    else os.path.basename(base_path)),
            'path': relative_path,
            'children': [],
            'files_count': 0,
            'total_files_count': 0,
            'is_selected': False,
            'is_expanded': False
        }
        
        # Применяем сохраненные состояния
        if relative_path in folder_states:
            state = folder_states[relative_path]
            folder_info['is_selected'] = bool(state.get('is_selected', 0))
            folder_info['is_expanded'] = bool(state.get('is_expanded', 0))
        
        if not os.path.exists(path):
            return folder_info
        
        try:
            items = os.listdir(path)
            dirs = []
            files = []
            
            for item in items:
                item_path = os.path.join(path, item)
                # Фильтруем папки: скрытые (начинающиеся с точки) и Attachment
                if (os.path.isdir(item_path) and 
                    not item.startswith('.') and
                    not item.endswith('_Attachment') and
                    not item.endswith('_Attachments') and
                    not item.endswith('Attachment')):
                    dirs.append(item)
                elif (item.endswith('.md') and 
                      not item.endswith('_Attachment.md') and
                      not item.endswith('_Attachments.md') and
                      not item.endswith('Attachment.md')):
                    files.append(item)
            
            # Файлы в текущей папке
            folder_info['files_count'] = len(files)
            folder_info['total_files_count'] = len(files)
            
            # Обрабатываем подпапки
            for dir_name in sorted(dirs):
                dir_path = os.path.join(path, dir_name)
                child_relative_path = (os.path.join(relative_path, dir_name) 
                                      if relative_path else dir_name)
                child_info = scan_folder(dir_path, child_relative_path)
                folder_info['children'].append(child_info)
                folder_info['total_files_count'] += child_info['total_files_count']
            
        except PermissionError:
            pass
        
        return folder_info
    
    return scan_folder(base_path)


def process_obsidian_content(content, file_path=None, images_dir=None, base_path=None):
    """Обработка Obsidian-специфичного контента"""
    
    # СУПЕР АГРЕССИВНАЯ ОЧИСТКА YAML - полностью удаляем всё между первыми ---
    
    # Метод 1: Удаляем любой блок начинающийся с --- в начале файла
    if content.strip().startswith('---'):
        lines = content.split('\n')
        yaml_start = 0
        yaml_end = -1
        
        # Ищем первый --- в начале
        if lines[0].strip() == '---':
            yaml_start = 0
            
            # Ищем закрывающий ---
            for i in range(1, len(lines)):
                if lines[i].strip() == '---':
                    yaml_end = i
                    break
            
            if yaml_end > 0:
                # Удаляем всё от начала до закрывающего --- включительно
                content = '\n'.join(lines[yaml_end + 1:])
            else:
                # Нет закрывающего --- - удаляем всё до первого заголовка или 50 строк
                for i in range(1, min(len(lines), 100)):
                    line = lines[i].strip()
                    if (line.startswith('#') or 
                        (line and not line.startswith(('title:', 'date:', 'tags:', 'author:', 'description:', 'created:', 'updated:', 'aliases:', 'cssclass:', 'publish:', 'draft:', 'category:', 'categories:', 'summary:', 'weight:', 'url:', 'slug:', 'layout:', 'type:', 'series:', 'keywords:', 'cover:', 'thumbnail:', 'image:', 'featured:', 'toc:', 'math:', 'markup:', 'highlight:', 'linenos:', 'anchor:', 'menu:', 'sitemap:', 'noindex:', 'robots:', 'canonical:', 'redirect:', 'resources:', 'cascade:', 'params:', 'outputs:', 'translationKey:', 'lang:', 'contentDir:', 'disable:', 'Источник:', 'Тип:', 'Теги:', 'Дата создания:', 'Дата обновления:', '  -', '- ')) and 
                         not re.match(r'^\s*[a-zA-Zа-яёА-ЯЁ0-9_-]+\s*:\s*', line))):
                        content = '\n'.join(lines[i:])
                        break
                else:
                    # Если не нашли подходящее место, берем с 50-й строки
                    content = '\n'.join(lines[50:] if len(lines) > 50 else lines[1:])
    
    # Метод 2: Еще раз проверяем на остатки YAML
    yaml_pattern = r'^---\s*\n.*?\n---\s*\n'
    content = re.sub(yaml_pattern, '', content, flags=re.DOTALL | re.MULTILINE)
    
    # Метод 3: Удаляем любые остатки YAML-подобных строк в начале
    lines = content.split('\n')
    start_index = 0
    
    for i, line in enumerate(lines[:20]):  # Проверяем только первые 20 строк
        stripped = line.strip()
        if (stripped == '' or
            stripped.startswith('#') or
            stripped.startswith('![[') or
            stripped.startswith('[[') or
            stripped.startswith('> ') or
            stripped.startswith('- ') or
            stripped.startswith('* ') or
            stripped.startswith('1. ') or
            stripped.startswith('```') or
            stripped.startswith('|') or
            (stripped and 
             not stripped.startswith('---') and
             not re.match(r'^[a-zA-Zа-яёА-ЯЁ0-9_\s-]*:\s*', stripped) and
             not stripped.startswith(('  -', '- ')))):
            start_index = i
            break
    
    content = '\n'.join(lines[start_index:])
    
    # Обрабатываем вставки страниц ![[filename]] (embeds/transclusion)
    if file_path and base_path:
        content = process_embeds(content, file_path, base_path, images_dir)
    else:
        content = re.sub(r'!\[\[([^\]]+)\]\]', r'*[Изображение]*', content)
    
    # Обрабатываем ссылки [[Note Name]]
    content = re.sub(r'\[\[([^\]]+)\]\]', r'**\1**', content)
    
    # Обрабатываем теги #tag
    content = re.sub(r'#([a-zA-Z0-9_-]+)', r'**#\1**', content)
    
    # Убираем пустые строки в начале и конце
    content = content.strip()
    
    # ФИНАЛЬНАЯ ОЧИСТКА: удаляем все оставшиеся --- строки
    # которые могут быть интерпретированы pandoc как YAML
    lines = content.split('\n')
    filtered_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped_line = line.strip()
        
        # Пропускаем строки содержащие только ---
        if stripped_line == '---':
            i += 1
            continue
        
        # Удаляем блоки метаданных плагинов (title: style: minLevel: и т.д.)
        if re.match(r'^(title|style|minLevel|maxLevel|includeLinks|debugInConsole):', stripped_line):
            # Пропускаем все строки до пустой строки или заголовка
            while i < len(lines) and lines[i].strip() != '' and not lines[i].strip().startswith('#'):
                i += 1
            continue
        
        filtered_lines.append(line)
        i += 1
    
    content = '\n'.join(filtered_lines)
    
    return content


def process_embeds(content, file_path, base_path, images_dir, visited_files=None):
    """Обработка вставок страниц Obsidian (![[filename]])"""
    if visited_files is None:
        visited_files = set()
    
    # Добавляем текущий файл в посещенные для предотвращения циклических ссылок
    current_file = os.path.abspath(file_path)
    if current_file in visited_files:
        return content
    visited_files.add(current_file)
    
    def replace_embed(match):
        embed_name = match.group(1)
        
        # Проверяем, не является ли это изображением
        _, ext = os.path.splitext(embed_name)
        if ext.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']:
            # Обрабатываем как изображение
            return process_single_image(embed_name, file_path, images_dir, base_path)
        
        # Ищем markdown файл для вставки
        embed_file_path = find_markdown_file(embed_name, base_path)
        
        if embed_file_path and os.path.exists(embed_file_path):
            try:
                # Читаем содержимое файла
                with open(embed_file_path, 'r', encoding='utf-8') as f:
                    embed_content = f.read()
                
                # Рекурсивно обрабатываем содержимое (для вложенных вставок)
                embed_content = process_obsidian_content(
                    embed_content, embed_file_path, images_dir, base_path
                )
                
                # Добавляем разделитель без длинного имени
                return f"\n\n{embed_content}\n\n"
                
            except Exception as e:
                print(f"Ошибка при обработке вставки {embed_name}: {e}")
                return f'*[Ошибка при вставке: {embed_name}]*'
        else:
            return f'*[Файл для вставки не найден: {embed_name}]*'
    
    # Заменяем все вставки
    content = re.sub(r'!\[\[([^\]]+)\]\]', replace_embed, content)
    
    # Убираем текущий файл из посещенных
    visited_files.discard(current_file)
    
    return content


def find_markdown_file(filename, base_path):
    """Поиск markdown файла по имени"""
    # Если filename уже содержит расширение .md
    if filename.endswith('.md'):
        search_name = filename
    else:
        search_name = f"{filename}.md"
    
    # Поиск рекурсивно по всему проекту
    for root, dirs, files in os.walk(base_path):
        # Исключаем папки attachments
        dirs[:] = [d for d in dirs 
                  if not d.startswith('.') and
                  not d.endswith('_Attachment') and
                  not d.endswith('_Attachments') and
                  not d.endswith('Attachment')]
        
        if search_name in files:
            return os.path.join(root, search_name)
    
    return None


def process_single_image(image_name, file_path, images_dir, base_path):
    """Обработка одного изображения"""
    if not images_dir:
        return f'*[Изображение: {image_name}]*'
    
    # Ищем изображение в разных местах
    possible_paths = []
    
    # Папка с самим файлом
    file_dir = os.path.dirname(file_path)
    possible_paths.append(os.path.join(file_dir, image_name))
    
    # Папки attachments рядом с файлом
    possible_paths.append(os.path.join(file_dir, '_Attachments', image_name))
    possible_paths.append(os.path.join(file_dir, '_Attachment', image_name))
    possible_paths.append(os.path.join(file_dir, 'Attachments', image_name))
    possible_paths.append(os.path.join(file_dir, 'Attachment', image_name))
    
    # Папки attachments в корне проекта
    possible_paths.append(os.path.join(base_path, '_Attachments', image_name))
    possible_paths.append(os.path.join(base_path, '_Attachment', image_name))
    possible_paths.append(os.path.join(base_path, 'Attachments', image_name))
    possible_paths.append(os.path.join(base_path, 'Attachment', image_name))
    
    # Поиск рекурсивно по всему проекту
    for root, dirs, files in os.walk(base_path):
        if image_name in files:
            possible_paths.append(os.path.join(root, image_name))
    
    # Пытаемся найти изображение
    for img_path in possible_paths:
        if os.path.exists(img_path):
            try:
                # Определяем расширение
                _, ext = os.path.splitext(image_name)
                if ext.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']:
                    # Копируем изображение с коротким именем
                    file_ext = os.path.splitext(image_name)[1]
                    short_name = f"image_{len(os.listdir(images_dir)) + 1}{file_ext}"
                    dest_path = os.path.join(images_dir, short_name)
                    shutil.copy2(img_path, dest_path)
                    
                    # Возвращаем markdown ссылку без длинного имени
                    return f'![Изображение](images/{short_name})'
            except Exception as e:
                print(f"Ошибка при копировании изображения {image_name}: {e}")
                break
    
    # Если изображение не найдено
    return f'*[Изображение не найдено: {image_name}]*'


if __name__ == '__main__':
    app.run(debug=True, port=5002, host='0.0.0.0') 