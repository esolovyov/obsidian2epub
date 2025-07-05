import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class Database:
    def __init__(self, db_path: str = "obs2epub.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица настроек
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Таблица проектов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица файлов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    relative_path TEXT,
                    size INTEGER,
                    is_included INTEGER DEFAULT 1,
                    file_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    UNIQUE(project_id, path)
                )
            ''')
            
            # Таблица состояний папок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS folder_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    folder_path TEXT NOT NULL,
                    is_selected INTEGER DEFAULT 0,
                    is_expanded INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    UNIQUE(project_id, folder_path)
                )
            ''')
            
            conn.commit()
    
    def get_connection(self):
        """Получение соединения с базой данных"""
        return sqlite3.connect(self.db_path)
    
    def dict_factory(self, cursor, row):
        """Преобразование результата в словарь"""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    
    def create_or_update_project(self, name, path):
        """Создание или обновление проекта"""
        with self.get_connection() as conn:
            conn.row_factory = self.dict_factory
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже такой проект
            cursor.execute('SELECT * FROM projects WHERE path = ?', (path,))
            existing_project = cursor.fetchone()
            
            if existing_project:
                # Обновляем существующий проект
                cursor.execute('''
                    UPDATE projects 
                    SET name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE path = ?
                ''', (name, path))
                project_id = existing_project['id']
            else:
                # Создаем новый проект
                cursor.execute('''
                    INSERT INTO projects (name, path)
                    VALUES (?, ?)
                ''', (name, path))
                project_id = cursor.lastrowid
            
            # Получаем обновленную информацию о проекте
            cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
            project = cursor.fetchone()
            
            conn.commit()
            return project
    
    def get_active_project(self):
        """Получение активного проекта"""
        with self.get_connection() as conn:
            conn.row_factory = self.dict_factory
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM projects WHERE is_active = 1 LIMIT 1')
            return cursor.fetchone()
    
    def set_active_project(self, project_id):
        """Установка активного проекта"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Сначала убираем активность у всех проектов
            cursor.execute('UPDATE projects SET is_active = 0')
            
            # Затем устанавливаем активность у указанного проекта
            cursor.execute('UPDATE projects SET is_active = 1 WHERE id = ?', (project_id,))
            
            conn.commit()
    
    def get_all_projects(self):
        """Получение всех проектов"""
        with self.get_connection() as conn:
            conn.row_factory = self.dict_factory
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM projects ORDER BY updated_at DESC')
            return cursor.fetchall()
    
    def delete_project(self, project_id):
        """Удаление проекта"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Удаляем файлы проекта
            cursor.execute('DELETE FROM files WHERE project_id = ?', (project_id,))
            
            # Удаляем проект
            cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            
            conn.commit()
    
    def sync_project_files(self, project_id, files_data):
        """Синхронизация файлов проекта"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем существующие файлы
            cursor.execute('SELECT path FROM files WHERE project_id = ?', (project_id,))
            existing_paths = {row[0] for row in cursor.fetchall()}
            
            # Добавляем новые файлы
            for file_data in files_data:
                if file_data['path'] not in existing_paths:
                    cursor.execute('''
                        INSERT INTO files (project_id, name, path, relative_path, size)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        project_id,
                        file_data['name'],
                        file_data['path'],
                        file_data.get('relative_path', ''),
                        file_data.get('size', 0)
                    ))
            
            conn.commit()
    
    def get_project_files(self, project_id):
        """Получение файлов проекта"""
        with self.get_connection() as conn:
            conn.row_factory = self.dict_factory
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM files 
                WHERE project_id = ? 
                ORDER BY file_order ASC, name ASC
            ''', (project_id,))
            
            return cursor.fetchall()
    
    def get_included_files(self, project_id):
        """Получение файлов включенных в экспорт"""
        with self.get_connection() as conn:
            conn.row_factory = self.dict_factory
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM files 
                WHERE project_id = ? AND is_included = 1 
                ORDER BY file_order ASC, name ASC
            ''', (project_id,))
            
            return cursor.fetchall()
    
    def toggle_file_inclusion(self, file_id, is_included):
        """Переключение включения файла в экспорт"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE files 
                SET is_included = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (is_included, file_id))
            
            conn.commit()
    
    def update_file_order(self, project_id, file_orders):
        """Обновление порядка файлов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for file_id, order in file_orders:
                cursor.execute('''
                    UPDATE files 
                    SET file_order = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND project_id = ?
                ''', (order, file_id, project_id))
            
            conn.commit()

    def get_folder_states(self, project_id):
        """Получение состояний папок"""
        with self.get_connection() as conn:
            conn.row_factory = self.dict_factory
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM folder_states 
                WHERE project_id = ?
            ''', (project_id,))
            
            return cursor.fetchall()

    def set_folder_state(self, project_id, folder_path, is_selected=None, is_expanded=None):
        """Установка состояния папки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже запись
            cursor.execute('''
                SELECT id FROM folder_states 
                WHERE project_id = ? AND folder_path = ?
            ''', (project_id, folder_path))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем существующую запись
                updates = []
                values = []
                
                if is_selected is not None:
                    updates.append('is_selected = ?')
                    values.append(is_selected)
                
                if is_expanded is not None:
                    updates.append('is_expanded = ?')
                    values.append(is_expanded)
                
                if updates:
                    updates.append('updated_at = CURRENT_TIMESTAMP')
                    values.extend([project_id, folder_path])
                    
                    cursor.execute(f'''
                        UPDATE folder_states 
                        SET {', '.join(updates)}
                        WHERE project_id = ? AND folder_path = ?
                    ''', values)
            else:
                # Создаем новую запись
                cursor.execute('''
                    INSERT INTO folder_states (project_id, folder_path, is_selected, is_expanded)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, folder_path, 
                      is_selected if is_selected is not None else 0,
                      is_expanded if is_expanded is not None else 0))
            
            conn.commit()

    def remove_files_from_folder(self, project_id, folder_path):
        """Удаление файлов из указанной папки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Удаляем файлы, которые находятся в указанной папке
            cursor.execute('''
                DELETE FROM files 
                WHERE project_id = ? AND (
                    relative_path = ? OR 
                    relative_path LIKE ?
                )
            ''', (project_id, folder_path, f"{folder_path}%"))
            
            conn.commit()

    def add_files_to_project(self, project_id, files_data):
        """Добавление файлов в проект (в конец списка)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем максимальный порядок файлов
            cursor.execute('''
                SELECT COALESCE(MAX(file_order), 0) FROM files 
                WHERE project_id = ?
            ''', (project_id,))
            
            max_order = cursor.fetchone()[0]
            
            # Добавляем файлы
            for i, file_data in enumerate(files_data):
                cursor.execute('''
                    INSERT OR IGNORE INTO files 
                    (project_id, name, path, relative_path, size, file_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    project_id,
                    file_data['name'],
                    file_data['path'],
                    file_data.get('relative_path', ''),
                    file_data.get('size', 0),
                    max_order + i + 1
                ))
            
            conn.commit()
    
    def get_setting(self, key):
        """Получение настройки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            
            return result[0] if result else None
    
    def set_setting(self, key, value):
        """Установка настройки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value) 
                VALUES (?, ?)
            ''', (key, value))
            
            conn.commit()
    
    def remove_setting(self, key):
        """Удаление настройки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM settings WHERE key = ?', (key,))
            conn.commit()
    
    def get_all_settings(self):
        """Получение всех настроек"""
        with self.get_connection() as conn:
            conn.row_factory = self.dict_factory
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM settings')
            return cursor.fetchall()
    
    def close(self):
        """Закрытие соединения"""
        pass  # Используем контекстный менеджер, соединение закрывается автоматически


# Глобальный экземпляр базы данных
db = Database() 