from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import connection
import os
import subprocess
import shutil
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """Менеджер резервного копирования"""
    
    def __init__(self):
        self.backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        self.media_dir = os.path.join(settings.BASE_DIR, 'media')
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_full_backup(self, created_by=None):
        """Создание полной резервной копии"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"full_backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Логирование начала резервного копирования
            self._log_backup_start('full', backup_path, created_by)
            
            # Создание директории для бэкапа
            os.makedirs(backup_path, exist_ok=True)
            
            # Резервное копирование базы данных
            self._backup_database(backup_path)
            
            # Резервное копирование медиа файлов
            self._backup_media_files(backup_path)
            
            # Резервное копирование настроек
            self._backup_settings(backup_path)
            
            # Создание архива
            archive_path = self._create_archive(backup_path, backup_filename)
            
            # Удаление временной директории
            shutil.rmtree(backup_path)
            
            # Логирование успешного завершения
            self._log_backup_success('full', archive_path, created_by)
            
            logger.info(f"Полная резервная копия создана: {archive_path}")
            return archive_path
            
        except Exception as e:
            logger.error(f"Ошибка создания полной резервной копии: {str(e)}")
            self._log_backup_error('full', str(e), created_by)
            raise
    
    def create_incremental_backup(self, created_by=None):
        """Создание инкрементальной резервной копии"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"incremental_backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Логирование начала резервного копирования
            self._log_backup_start('incremental', backup_path, created_by)
            
            # Создание директории для бэкапа
            os.makedirs(backup_path, exist_ok=True)
            
            # Получение последней даты полного бэкапа
            last_full_backup = self._get_last_full_backup_date()
            
            # Резервное копирование изменений в базе данных
            self._backup_database_changes(backup_path, last_full_backup)
            
            # Резервное копирование новых медиа файлов
            self._backup_new_media_files(backup_path, last_full_backup)
            
            # Создание архива
            archive_path = self._create_archive(backup_path, backup_filename)
            
            # Удаление временной директории
            shutil.rmtree(backup_path)
            
            # Логирование успешного завершения
            self._log_backup_success('incremental', archive_path, created_by)
            
            logger.info(f"Инкрементальная резервная копия создана: {archive_path}")
            return archive_path
            
        except Exception as e:
            logger.error(f"Ошибка создания инкрементальной резервной копии: {str(e)}")
            self._log_backup_error('incremental', str(e), created_by)
            raise
    
    def restore_from_backup(self, backup_path, restore_type='full'):
        """Восстановление из резервной копии"""
        try:
            logger.info(f"Начало восстановления из {backup_path}")
            
            # Извлечение архива
            extract_path = self._extract_archive(backup_path)
            
            if restore_type == 'full':
                # Восстановление базы данных
                self._restore_database(extract_path)
                
                # Восстановление медиа файлов
                self._restore_media_files(extract_path)
                
                # Восстановление настроек
                self._restore_settings(extract_path)
            
            elif restore_type == 'incremental':
                # Восстановление изменений
                self._restore_database_changes(extract_path)
                self._restore_new_media_files(extract_path)
            
            # Очистка временных файлов
            shutil.rmtree(extract_path)
            
            logger.info("Восстановление завершено успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка восстановления: {str(e)}")
            raise
    
    def cleanup_old_backups(self, retention_days=30):
        """Очистка старых резервных копий"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Получение списка старых бэкапов из базы данных
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, file_path FROM backup_log 
                    WHERE created_at < %s AND status = 'success'
                """, [cutoff_date])
                
                old_backups = cursor.fetchall()
            
            deleted_count = 0
            for backup_id, file_path in old_backups:
                try:
                    # Удаление файла
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # Обновление записи в базе данных
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE backup_log 
                            SET status = 'deleted', completed_at = %s
                            WHERE id = %s
                        """, [timezone.now(), backup_id])
                    
                    deleted_count += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка удаления бэкапа {file_path}: {str(e)}")
            
            logger.info(f"Удалено {deleted_count} старых резервных копий")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки старых бэкапов: {str(e)}")
            raise
    
    def _backup_database(self, backup_path):
        """Резервное копирование базы данных"""
        db_path = os.path.join(backup_path, 'database')
        os.makedirs(db_path, exist_ok=True)
        
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            # Для SQLite просто копируем файл
            db_file = settings.DATABASES['default']['NAME']
            shutil.copy2(db_file, os.path.join(db_path, 'db.sqlite3'))
        
        elif 'postgresql' in settings.DATABASES['default']['ENGINE']:
            # Для PostgreSQL используем pg_dump
            db_config = settings.DATABASES['default']
            dump_file = os.path.join(db_path, 'database.sql')
            
            cmd = [
                'pg_dump',
                '-h', db_config['HOST'],
                '-p', str(db_config['PORT']),
                '-U', db_config['USER'],
                '-d', db_config['NAME'],
                '-f', dump_file
            ]
            
            subprocess.run(cmd, check=True, env={'PGPASSWORD': db_config['PASSWORD']})
    
    def _backup_media_files(self, backup_path):
        """Резервное копирование медиа файлов"""
        media_backup_path = os.path.join(backup_path, 'media')
        
        if os.path.exists(self.media_dir):
            shutil.copytree(self.media_dir, media_backup_path)
    
    def _backup_settings(self, backup_path):
        """Резервное копирование настроек"""
        settings_backup_path = os.path.join(backup_path, 'settings')
        os.makedirs(settings_backup_path, exist_ok=True)
        
        # Копирование важных файлов настроек
        important_files = [
            'settings.py',
            'requirements.txt',
            'manage.py'
        ]
        
        for filename in important_files:
            file_path = os.path.join(settings.BASE_DIR, filename)
            if os.path.exists(file_path):
                shutil.copy2(file_path, settings_backup_path)
    
    def _backup_database_changes(self, backup_path, since_date):
        """Резервное копирование изменений в базе данных"""
        db_path = os.path.join(backup_path, 'database_changes')
        os.makedirs(db_path, exist_ok=True)
        
        # Экспорт изменений в JSON
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name, operation, old_data, new_data, created_at
                FROM audit_log 
                WHERE created_at > %s
                ORDER BY created_at
            """, [since_date])
            
            changes = cursor.fetchall()
        
        # Сохранение изменений в файл
        import json
        changes_file = os.path.join(db_path, 'changes.json')
        with open(changes_file, 'w', encoding='utf-8') as f:
            json.dump(changes, f, default=str, ensure_ascii=False, indent=2)
    
    def _backup_new_media_files(self, backup_path, since_date):
        """Резервное копирование новых медиа файлов"""
        media_backup_path = os.path.join(backup_path, 'new_media')
        os.makedirs(media_backup_path, exist_ok=True)
        
        # Здесь должна быть логика для копирования только новых файлов
        # Для простоты копируем все медиа файлы
        if os.path.exists(self.media_dir):
            shutil.copytree(self.media_dir, media_backup_path)
    
    def _create_archive(self, backup_path, backup_name):
        """Создание архива резервной копии"""
        archive_path = os.path.join(self.backup_dir, f"{backup_name}.tar.gz")
        
        # Создание tar.gz архива
        subprocess.run([
            'tar', '-czf', archive_path, '-C', self.backup_dir, backup_name
        ], check=True)
        
        return archive_path
    
    def _extract_archive(self, archive_path):
        """Извлечение архива"""
        extract_path = os.path.join(self.backup_dir, 'temp_restore')
        os.makedirs(extract_path, exist_ok=True)
        
        # Извлечение tar.gz архива
        subprocess.run([
            'tar', '-xzf', archive_path, '-C', extract_path
        ], check=True)
        
        return extract_path
    
    def _restore_database(self, extract_path):
        """Восстановление базы данных"""
        db_path = os.path.join(extract_path, 'database')
        
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            # Для SQLite копируем файл
            db_file = os.path.join(db_path, 'db.sqlite3')
            if os.path.exists(db_file):
                shutil.copy2(db_file, settings.DATABASES['default']['NAME'])
        
        elif 'postgresql' in settings.DATABASES['default']['ENGINE']:
            # Для PostgreSQL используем psql
            db_config = settings.DATABASES['default']
            dump_file = os.path.join(db_path, 'database.sql')
            
            if os.path.exists(dump_file):
                cmd = [
                    'psql',
                    '-h', db_config['HOST'],
                    '-p', str(db_config['PORT']),
                    '-U', db_config['USER'],
                    '-d', db_config['NAME'],
                    '-f', dump_file
                ]
                
                subprocess.run(cmd, check=True, env={'PGPASSWORD': db_config['PASSWORD']})
    
    def _restore_media_files(self, extract_path):
        """Восстановление медиа файлов"""
        media_backup_path = os.path.join(extract_path, 'media')
        
        if os.path.exists(media_backup_path):
            if os.path.exists(self.media_dir):
                shutil.rmtree(self.media_dir)
            shutil.copytree(media_backup_path, self.media_dir)
    
    def _restore_settings(self, extract_path):
        """Восстановление настроек"""
        settings_backup_path = os.path.join(extract_path, 'settings')
        
        if os.path.exists(settings_backup_path):
            # Копирование файлов настроек
            for filename in os.listdir(settings_backup_path):
                src = os.path.join(settings_backup_path, filename)
                dst = os.path.join(settings.BASE_DIR, filename)
                shutil.copy2(src, dst)
    
    def _get_last_full_backup_date(self):
        """Получение даты последнего полного бэкапа"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT MAX(created_at) FROM backup_log 
                WHERE backup_type = 'full' AND status = 'success'
            """)
            
            result = cursor.fetchone()
            return result[0] if result[0] else datetime.now() - timedelta(days=30)
    
    def _log_backup_start(self, backup_type, file_path, created_by):
        """Логирование начала резервного копирования"""
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO backup_log (backup_type, file_path, status, created_by, created_at)
                VALUES (%s, %s, 'in_progress', %s, %s)
            """, [backup_type, file_path, created_by, timezone.now()])
    
    def _log_backup_success(self, backup_type, file_path, created_by):
        """Логирование успешного завершения резервного копирования"""
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE backup_log 
                SET status = 'success', file_size = %s, completed_at = %s
                WHERE backup_type = %s AND file_path LIKE %s AND status = 'in_progress'
            """, [file_size, timezone.now(), backup_type, f"%{backup_type}%"])
    
    def _log_backup_error(self, backup_type, error_message, created_by):
        """Логирование ошибки резервного копирования"""
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE backup_log 
                SET status = 'failed', error_message = %s, completed_at = %s
                WHERE backup_type = %s AND status = 'in_progress'
            """, [error_message, timezone.now(), backup_type])


class Command(BaseCommand):
    """Команда управления резервным копированием"""
    help = 'Управление резервным копированием системы'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['create-full', 'create-incremental', 'restore', 'cleanup'],
            help='Действие для выполнения'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Путь к файлу резервной копии (для восстановления)'
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Количество дней хранения резервных копий'
        )
    
    def handle(self, *args, **options):
        backup_manager = BackupManager()
        
        try:
            if options['action'] == 'create-full':
                backup_path = backup_manager.create_full_backup()
                self.stdout.write(
                    self.style.SUCCESS(f'Полная резервная копия создана: {backup_path}')
                )
            
            elif options['action'] == 'create-incremental':
                backup_path = backup_manager.create_incremental_backup()
                self.stdout.write(
                    self.style.SUCCESS(f'Инкрементальная резервная копия создана: {backup_path}')
                )
            
            elif options['action'] == 'restore':
                if not options['file']:
                    self.stdout.write(
                        self.style.ERROR('Необходимо указать путь к файлу резервной копии')
                    )
                    return
                
                backup_manager.restore_from_backup(options['file'])
                self.stdout.write(
                    self.style.SUCCESS('Восстановление завершено успешно')
                )
            
            elif options['action'] == 'cleanup':
                deleted_count = backup_manager.cleanup_old_backups(options['retention_days'])
                self.stdout.write(
                    self.style.SUCCESS(f'Удалено {deleted_count} старых резервных копий')
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка: {str(e)}')
            )
