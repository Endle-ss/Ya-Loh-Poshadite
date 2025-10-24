from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db import connection
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class DjangoRBACManager:
    """Менеджер системы контроля доступа на основе ролей (RBAC) для Django ORM"""
    
    # Определение разрешений для каждой роли
    ROLE_PERMISSIONS = {
        'user': [
            'create_listing',
            'edit_own_listing',
            'delete_own_listing',
            'leave_review',
            'report_content',
            'manage_favorites',
            'view_profile',
            'view_own_notifications'
        ],
        'moderator': [
            'create_listing',
            'edit_own_listing',
            'delete_own_listing',
            'leave_review',
            'report_content',
            'manage_favorites',
            'view_profile',
            'view_own_notifications',
            'moderate_listings',
            'view_reports',
            'ban_users',
            'view_moderation_log',
            'view_all_notifications'
        ],
        'admin': [
            'create_listing',
            'edit_own_listing',
            'delete_own_listing',
            'leave_review',
            'report_content',
            'manage_favorites',
            'view_profile',
            'view_own_notifications',
            'moderate_listings',
            'view_reports',
            'ban_users',
            'view_moderation_log',
            'view_all_notifications',
            'manage_users',
            'manage_categories',
            'manage_roles',
            'view_statistics',
            'system_settings',
            'backup_management',
            'view_audit_log',
            'manage_permissions'
        ]
    }
    
    @staticmethod
    def has_permission(user, permission, entity_type=None, entity_id=None):
        """Проверка наличия разрешения у пользователя"""
        if not user.is_authenticated:
            return False
        
        # Получение роли пользователя
        user_role = DjangoRBACManager.get_user_role(user)
        if not user_role:
            return False
        
        # Проверка прав администратора
        if user_role == 'admin':
            return True
        
        # Проверка прав модератора
        if user_role == 'moderator' and permission in ['moderate_listings', 'view_reports', 'ban_users']:
            return True
        
        # Проверка прав владельца ресурса
        if entity_type == 'listing' and entity_id:
            from .models import Listing
            try:
                listing = Listing.objects.get(id=entity_id)
                if listing.user_id == user.id:
                    return permission in ['edit_own_listing', 'delete_own_listing']
            except Listing.DoesNotExist:
                pass
        
        # Проверка конкретных разрешений
        return permission in DjangoRBACManager.ROLE_PERMISSIONS.get(user_role, [])
    
    @staticmethod
    def get_user_role(user):
        """Получение роли пользователя"""
        if not user.is_authenticated:
            return None
        
        try:
            return user.role.name
        except AttributeError:
            return 'user'
    
    @staticmethod
    def get_user_permissions(user):
        """Получение всех разрешений пользователя"""
        role = DjangoRBACManager.get_user_role(user)
        if not role:
            return []
        
        return DjangoRBACManager.ROLE_PERMISSIONS.get(role, [])


def require_permission(permission, entity_type=None, entity_id_param='id'):
    """Декоратор для проверки разрешений"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': 'Требуется авторизация'}, status=401)
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            # Получение entity_id из параметров
            entity_id = kwargs.get(entity_id_param) if entity_id_param else None
            
            # Проверка разрешения
            if not DjangoRBACManager.has_permission(
                request.user, permission, entity_type, entity_id
            ):
                logger.warning(
                    f"Пользователь {request.user.username} попытался выполнить действие "
                    f"{permission} без соответствующих прав"
                )
                
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': 'Недостаточно прав'}, status=403)
                
                raise PermissionDenied("Недостаточно прав для выполнения этого действия")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles):
    """Декоратор для проверки роли пользователя"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': 'Требуется авторизация'}, status=401)
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            user_role = DjangoRBACManager.get_user_role(request.user)
            
            if user_role not in roles:
                logger.warning(
                    f"Пользователь {request.user.username} с ролью {user_role} "
                    f"попытался получить доступ к ресурсу, требующему роли {roles}"
                )
                
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({'error': 'Недостаточно прав'}, status=403)
                
                raise PermissionDenied("Недостаточно прав для доступа к этому ресурсу")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Готовые декораторы для часто используемых проверок
require_user = require_role('user', 'moderator', 'admin')
require_moderator = require_role('moderator', 'admin')
require_admin = require_role('admin')

require_listing_permission = require_permission('create_listing', 'listing')
require_moderation_permission = require_permission('moderate_listings', 'listing')
require_user_management = require_permission('manage_users', 'user')


class DjangoAuditLogger:
    """Логгер для аудита действий пользователей через Django ORM"""
    
    @staticmethod
    def log_user_action(user, action, entity_type=None, entity_id=None, details=None, request=None):
        """Логирование действия пользователя"""
        try:
            from .django_orm_services import UserActivityLogger
            
            UserActivityLogger.log_activity(
                user_id=user.id if user.is_authenticated else None,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                request=request
            )
        except Exception as e:
            logger.error(f"Ошибка логирования действия пользователя: {str(e)}")
    
    @staticmethod
    def log_security_event(event_type, user=None, ip_address=None, details=None):
        """Логирование событий безопасности"""
        logger.warning(
            f"Событие безопасности: {event_type}, "
            f"Пользователь: {getattr(user, 'username', 'anonymous')}, "
            f"IP: {ip_address}, "
            f"Детали: {details}"
        )


class DjangoPasswordSecurityManager:
    """Менеджер безопасности паролей для Django"""
    
    @staticmethod
    def hash_password(password):
        """Хеширование пароля"""
        from django.contrib.auth.hashers import make_password
        return make_password(password)
    
    @staticmethod
    def verify_password(password, hashed_password):
        """Проверка пароля"""
        from django.contrib.auth.hashers import check_password
        return check_password(password, hashed_password)
    
    @staticmethod
    def validate_password_strength(password):
        """Валидация силы пароля (упрощенная для демонстрации)"""
        errors = []
        
        if len(password) < 4:
            errors.append('Пароль должен содержать минимум 4 символа')
        
        # Убираем остальные строгие требования для демонстрации
        
        return errors


class DjangoBackupManager:
    """Менеджер резервного копирования для Django ORM"""
    
    def __init__(self):
        from django.conf import settings
        import os
        self.backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        self.media_dir = os.path.join(settings.BASE_DIR, 'media')
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_full_backup(self, created_by=None):
        """Создание полной резервной копии"""
        try:
            import shutil
            import subprocess
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"full_backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Создание директории для бэкапа
            os.makedirs(backup_path, exist_ok=True)
            
            # Резервное копирование базы данных (SQLite)
            db_file = settings.DATABASES['default']['NAME']
            if os.path.exists(db_file):
                shutil.copy2(db_file, os.path.join(backup_path, 'db.sqlite3'))
            
            # Резервное копирование медиа файлов
            if os.path.exists(self.media_dir):
                shutil.copytree(self.media_dir, os.path.join(backup_path, 'media'))
            
            # Резервное копирование настроек
            settings_backup_path = os.path.join(backup_path, 'settings')
            os.makedirs(settings_backup_path, exist_ok=True)
            
            important_files = ['settings.py', 'requirements.txt', 'manage.py']
            for filename in important_files:
                file_path = os.path.join(settings.BASE_DIR, filename)
                if os.path.exists(file_path):
                    shutil.copy2(file_path, settings_backup_path)
            
            # Создание архива
            archive_path = self._create_archive(backup_path, backup_filename)
            
            # Удаление временной директории
            shutil.rmtree(backup_path)
            
            logger.info(f"Полная резервная копия создана: {archive_path}")
            return archive_path
            
        except Exception as e:
            logger.error(f"Ошибка создания полной резервной копии: {str(e)}")
            raise
    
    def _create_archive(self, backup_path, backup_name):
        """Создание архива резервной копии"""
        import tarfile
        import os
        
        archive_path = os.path.join(self.backup_dir, f"{backup_name}.tar.gz")
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(backup_path, arcname=backup_name)
        
        return archive_path
    
    def restore_from_backup(self, backup_path):
        """Восстановление из резервной копии"""
        try:
            import tarfile
            import shutil
            from django.conf import settings
            
            logger.info(f"Начало восстановления из {backup_path}")
            
            # Извлечение архива
            extract_path = os.path.join(self.backup_dir, 'temp_restore')
            os.makedirs(extract_path, exist_ok=True)
            
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(extract_path)
            
            # Восстановление базы данных
            db_file = os.path.join(extract_path, 'full_backup_*', 'db.sqlite3')
            if os.path.exists(db_file):
                shutil.copy2(db_file, settings.DATABASES['default']['NAME'])
            
            # Восстановление медиа файлов
            media_backup_path = os.path.join(extract_path, 'full_backup_*', 'media')
            if os.path.exists(media_backup_path):
                if os.path.exists(self.media_dir):
                    shutil.rmtree(self.media_dir)
                shutil.copytree(media_backup_path, self.media_dir)
            
            # Очистка временных файлов
            shutil.rmtree(extract_path)
            
            logger.info("Восстановление завершено успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка восстановления: {str(e)}")
            raise


# Алиасы для совместимости
RBACManager = DjangoRBACManager
AuditLogger = DjangoAuditLogger
PasswordSecurityManager = DjangoPasswordSecurityManager
BackupManager = DjangoBackupManager
