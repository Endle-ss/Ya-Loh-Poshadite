from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import connection
import os
import shutil
from datetime import datetime, timedelta
import logging
import tarfile

logger = logging.getLogger(__name__)


class BackupManager:
    """Менеджер резервного копирования (backup/restore БД и медиа)

    Работает как с SQLite (по умолчанию в проекте), так и с PostgreSQL.
    Для SQLite используется простое копирование файла БД без внешних утилит.
    Для PostgreSQL используются стандартные утилиты `pg_dump` и `psql` (должны быть установлены в системе).
    """

    def __init__(self):
        self.backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        self.media_dir = os.path.join(settings.BASE_DIR, 'media')
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_full_backup(self, created_by=None):
        """Создание полной резервной копии (БД + media + ключевые настройки)."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"full_backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            # Логирование начала резервного копирования (если есть служебная таблица)
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
        """Создание инкрементальной резервной копии.

        Для SQLite инкрементальные бэкапы не поддерживаются — будет выброшено
        понятное исключение. Для PostgreSQL используются таблицы `backup_log`
        и `audit_log`, создаваемые SQL-скриптами из директории `database/`.
        """
        engine = settings.DATABASES['default']['ENGINE']
        if engine == 'django.db.backends.sqlite3':
            raise RuntimeError("Инкрементальные бэкапы для SQLite не поддерживаются. "
                               "Используйте полную резервную копию (create-full).")

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
        """Восстановление из резервной копии."""
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
        """Очистка старых резервных копий.

        Если таблица `backup_log` отсутствует (например, при использовании
        только SQLite без SQL-скриптов), метод просто удаляет старые файлы
        из директории `backups` по дате изменения.
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # Попытка очистки через служебную таблицу (PostgreSQL)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, file_path FROM backup_log 
                    WHERE created_at < %s AND status = 'success'
                    """,
                    [cutoff_date],
                )
                old_backups = cursor.fetchall()
        except Exception:
            old_backups = []

        deleted_count = 0

        # Удаляем файлы, известные базе
        for backup_id, file_path in old_backups:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)

                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE backup_log 
                        SET status = 'deleted', completed_at = %s
                        WHERE id = %s
                        """,
                        [timezone.now(), backup_id],
                    )

                deleted_count += 1
            except Exception as e:
                logger.error(f"Ошибка удаления бэкапа {file_path}: {str(e)}")

        # Дополнительно чистим старые файлы напрямую в файловой системе
        for name in os.listdir(self.backup_dir):
            path = os.path.join(self.backup_dir, name)
            try:
                if os.path.isfile(path):
                    mtime = datetime.fromtimestamp(os.path.getmtime(path))
                    if mtime < cutoff_date:
                        os.remove(path)
                        deleted_count += 1
            except Exception as e:
                logger.error(f"Ошибка очистки файла {path}: {str(e)}")

        logger.info(f"Удалено {deleted_count} старых резервных копий")
        return deleted_count

    def _backup_database(self, backup_path):
        """Резервное копирование базы данных."""
        db_path = os.path.join(backup_path, 'database')
        os.makedirs(db_path, exist_ok=True)

        engine = settings.DATABASES['default']['ENGINE']

        if engine == 'django.db.backends.sqlite3':
            # Для SQLite просто копируем файл
            db_file = settings.DATABASES['default']['NAME']
            shutil.copy2(db_file, os.path.join(db_path, 'db.sqlite3'))

        elif 'postgresql' in engine:
            # Для PostgreSQL используем pg_dump
            import subprocess

            db_config = settings.DATABASES['default']
            dump_file = os.path.join(db_path, 'database.sql')

            cmd = [
                'pg_dump',
                '-h',
                db_config.get('HOST', '') or 'localhost',
                '-p',
                str(db_config.get('PORT', '') or 5432),
                '-U',
                db_config['USER'],
                '-d',
                db_config['NAME'],
                '-f',
                dump_file,
            ]

            env = os.environ.copy()
            if db_config.get('PASSWORD'):
                env['PGPASSWORD'] = db_config['PASSWORD']

            subprocess.run(cmd, check=True, env=env)

    def _backup_media_files(self, backup_path):
        """Резервное копирование медиа файлов."""
        media_backup_path = os.path.join(backup_path, 'media')

        if os.path.exists(self.media_dir):
            shutil.copytree(self.media_dir, media_backup_path)

    def _backup_settings(self, backup_path):
        """Резервное копирование основных файлов настроек проекта."""
        settings_backup_path = os.path.join(backup_path, 'settings')
        os.makedirs(settings_backup_path, exist_ok=True)

        # Копирование важных файлов настроек
        important_files = [
            os.path.join('chepochem_project', 'settings.py'),
            'requirements.txt',
            'manage.py',
        ]

        for rel_path in important_files:
            file_path = os.path.join(settings.BASE_DIR, rel_path)
            if os.path.exists(file_path):
                shutil.copy2(file_path, settings_backup_path)

    def _backup_database_changes(self, backup_path, since_date):
        """Резервное копирование изменений в базе данных (PostgreSQL + audit_log)."""
        db_path = os.path.join(backup_path, 'database_changes')
        os.makedirs(db_path, exist_ok=True)

        # Экспорт изменений в JSON
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name, operation, old_data, new_data, created_at
                    FROM audit_log 
                    WHERE created_at > %s
                    ORDER BY created_at
                    """,
                    [since_date],
                )
                changes = cursor.fetchall()
        except Exception as e:
            logger.error(f"Не удалось прочитать audit_log для инкрементального бэкапа: {e}")
            changes = []

        import json

        changes_file = os.path.join(db_path, 'changes.json')
        with open(changes_file, 'w', encoding='utf-8') as f:
            json.dump(changes, f, default=str, ensure_ascii=False, indent=2)

    def _backup_new_media_files(self, backup_path, since_date):
        """Резервное копирование новых медиа файлов.

        Для простоты копируем все медиа файлы.
        """
        media_backup_path = os.path.join(backup_path, 'new_media')
        os.makedirs(media_backup_path, exist_ok=True)

        if os.path.exists(self.media_dir):
            shutil.copytree(self.media_dir, media_backup_path)

    def _create_archive(self, backup_path, backup_name):
        """Создание архива резервной копии (tar.gz, кросс-платформенно)."""
        archive_path = os.path.join(self.backup_dir, f"{backup_name}.tar.gz")

        # Создание tar.gz архива через стандартный модуль tarfile
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(backup_path, arcname=os.path.basename(backup_path))

        return archive_path

    def _extract_archive(self, archive_path):
        """Извлечение архива (tar.gz, кросс-платформенно)."""
        extract_root = os.path.join(self.backup_dir, 'temp_restore')
        os.makedirs(extract_root, exist_ok=True)

        # Распаковка архива в temp_restore и определение корневой папки внутри архива
        members = []
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=extract_root)
            members = [m for m in tar.getmembers() if m.isdir()]

        # В архиве внутри лежит папка с именем backup_name, возвращаем её путь
        # (первый каталог верхнего уровня)
        if members:
            top_dir_name = members[0].name.split('/')[0]
            return os.path.join(extract_root, top_dir_name)

        return extract_root

    def _restore_database(self, extract_path):
        """Восстановление базы данных из бэкапа."""
        db_path = os.path.join(extract_path, 'database')
        engine = settings.DATABASES['default']['ENGINE']

        if engine == 'django.db.backends.sqlite3':
            # Для SQLite копируем файл
            db_file = os.path.join(db_path, 'db.sqlite3')
            if os.path.exists(db_file):
                shutil.copy2(db_file, settings.DATABASES['default']['NAME'])

        elif 'postgresql' in engine:
            # Для PostgreSQL используем psql
            import subprocess

            db_config = settings.DATABASES['default']
            dump_file = os.path.join(db_path, 'database.sql')

            if os.path.exists(dump_file):
                cmd = [
                    'psql',
                    '-h',
                    db_config.get('HOST', '') or 'localhost',
                    '-p',
                    str(db_config.get('PORT', '') or 5432),
                    '-U',
                    db_config['USER'],
                    '-d',
                    db_config['NAME'],
                    '-f',
                    dump_file,
                ]

                env = os.environ.copy()
                if db_config.get('PASSWORD'):
                    env['PGPASSWORD'] = db_config['PASSWORD']

                subprocess.run(cmd, check=True, env=env)

    def _restore_media_files(self, extract_path):
        """Восстановление медиа файлов."""
        media_backup_path = os.path.join(extract_path, 'media')

        if os.path.exists(media_backup_path):
            if os.path.exists(self.media_dir):
                shutil.rmtree(self.media_dir)
            shutil.copytree(media_backup_path, self.media_dir)

    def _restore_settings(self, extract_path):
        """Восстановление настроек (опционально, с заменой файлов)."""
        settings_backup_path = os.path.join(extract_path, 'settings')

        if os.path.exists(settings_backup_path):
            for filename in os.listdir(settings_backup_path):
                src = os.path.join(settings_backup_path, filename)
                dst = os.path.join(settings.BASE_DIR, filename)
                shutil.copy2(src, dst)

    def _restore_database_changes(self, extract_path):
        """Заглушка для восстановления инкрементальных изменений.

        Для простоты пока не реализовано. Полное восстановление работает
        из полноценного бэкапа.
        """
        logger.warning("Восстановление инкрементальных изменений пока не реализовано.")

    def _restore_new_media_files(self, extract_path):
        """Восстановление новых медиа файлов (инкрементальный режим)."""
        new_media_path = os.path.join(extract_path, 'new_media')
        if os.path.exists(new_media_path):
            if not os.path.exists(self.media_dir):
                os.makedirs(self.media_dir, exist_ok=True)
            for root, dirs, files in os.walk(new_media_path):
                rel_root = os.path.relpath(root, new_media_path)
                target_root = os.path.join(self.media_dir, rel_root)
                os.makedirs(target_root, exist_ok=True)
                for file_name in files:
                    src = os.path.join(root, file_name)
                    dst = os.path.join(target_root, file_name)
                    shutil.copy2(src, dst)

    def _get_last_full_backup_date(self):
        """Получение даты последнего полного бэкапа через backup_log (если есть)."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT MAX(created_at) FROM backup_log 
                    WHERE backup_type = 'full' AND status = 'success'
                    """
                )
                result = cursor.fetchone()
        except Exception:
            result = (None,)

        return result[0] if result and result[0] else datetime.now() - timedelta(days=30)

    def _log_backup_start(self, backup_type, file_path, created_by):
        """Логирование начала резервного копирования (если есть backup_log)."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO backup_log (backup_type, file_path, status, created_by, created_at)
                    VALUES (%s, %s, 'in_progress', %s, %s)
                    """,
                    [backup_type, file_path, created_by, timezone.now()],
                )
        except Exception as e:
            logger.warning(f"Не удалось записать начало бэкапа в backup_log: {e}")

    def _log_backup_success(self, backup_type, file_path, created_by):
        """Логирование успешного завершения резервного копирования (если есть backup_log)."""
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE backup_log 
                    SET status = 'success', file_size = %s, completed_at = %s
                    WHERE backup_type = %s AND file_path = %s AND status = 'in_progress'
                    """,
                    [file_size, timezone.now(), backup_type, file_path],
                )
        except Exception as e:
            logger.warning(f"Не удалось записать успешный бэкап в backup_log: {e}")

    def _log_backup_error(self, backup_type, error_message, created_by):
        """Логирование ошибки резервного копирования (если есть backup_log)."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE backup_log 
                    SET status = 'failed', error_message = %s, completed_at = %s
                    WHERE backup_type = %s AND status = 'in_progress'
                    """,
                    [error_message, timezone.now(), backup_type],
                )
        except Exception as e:
            logger.warning(f"Не удалось записать ошибку бэкапа в backup_log: {e}")


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



