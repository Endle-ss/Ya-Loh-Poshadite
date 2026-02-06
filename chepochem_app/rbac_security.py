from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from functools import wraps
from .transaction_services import SecurityManager
import logging

logger = logging.getLogger(__name__)


class RBACManager:
    """Менеджер системы контроля доступа на основе ролей (RBAC)"""
    
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
        
        # Проверка через базу данных
        has_db_permission = SecurityManager.check_user_permission(
            user.id, permission, entity_type, entity_id
        )
        
        if has_db_permission:
            return True
        
        # Дополнительная проверка для владельца ресурса
        if entity_type == 'listing' and entity_id:
            from .models import Listing
            try:
                listing = Listing.objects.get(id=entity_id)
                if listing.user_id == user.id:
                    return permission in ['edit_own_listing', 'delete_own_listing']
            except Listing.DoesNotExist:
                pass
        
        return False
    
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
        role = RBACManager.get_user_role(user)
        if not role:
            return []
        
        return RBACManager.ROLE_PERMISSIONS.get(role, [])


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
            if not RBACManager.has_permission(
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
            
            user_role = RBACManager.get_user_role(request.user)
            
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


class PermissionMixin:
    """Mixin для проверки разрешений в классах"""
    
    def check_permission(self, user, permission, entity_type=None, entity_id=None):
        """Проверка разрешения в классе"""
        return RBACManager.has_permission(user, permission, entity_type, entity_id)
    
    def get_user_permissions(self, user):
        """Получение разрешений пользователя в классе"""
        return RBACManager.get_user_permissions(user)


class SecurityMiddleware:
    """Middleware для дополнительной безопасности"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверка блокировки IP
        if SecurityManager.check_ip_blocked(request.META.get('REMOTE_ADDR')):
            logger.warning(f"Заблокированный IP {request.META.get('REMOTE_ADDR')} попытался получить доступ")
            return JsonResponse({'error': 'IP адрес заблокирован'}, status=403)
        
        response = self.get_response(request)
        
        # Логирование подозрительной активности
        if response.status_code == 403:
            logger.warning(
                f"403 ошибка для пользователя {getattr(request.user, 'username', 'anonymous')} "
                f"с IP {request.META.get('REMOTE_ADDR')} на {request.path}"
            )
        
        return response


class AuditLogger:
    """Логгер для аудита действий пользователей"""
    
    @staticmethod
    def log_user_action(user, action, entity_type=None, entity_id=None, details=None, request=None):
        """Логирование действия пользователя"""
        from .transaction_services import UserActivityLogger
        
        UserActivityLogger.log_activity(
            user_id=user.id if user.is_authenticated else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            request=request
        )
    
    @staticmethod
    def log_security_event(event_type, user=None, ip_address=None, details=None):
        """Логирование событий безопасности"""
        logger.warning(
            f"Событие безопасности: {event_type}, "
            f"Пользователь: {getattr(user, 'username', 'anonymous')}, "
            f"IP: {ip_address}, "
            f"Детали: {details}"
        )


class PasswordSecurityManager:
    """Менеджер безопасности паролей"""
    
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
        """Валидация силы пароля"""
        errors = []
        
        if len(password) < 8:
            errors.append('Пароль должен содержать минимум 8 символов')
        
        if not any(c.isupper() for c in password):
            errors.append('Пароль должен содержать хотя бы одну заглавную букву')
        
        if not any(c.islower() for c in password):
            errors.append('Пароль должен содержать хотя бы одну строчную букву')
        
        if not any(c.isdigit() for c in password):
            errors.append('Пароль должен содержать хотя бы одну цифру')
        
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            errors.append('Пароль должен содержать хотя бы один специальный символ')
        
        return errors
    
    @staticmethod
    def check_password_history(user, new_password):
        """Проверка истории паролей (предотвращение повторного использования)"""
        # Здесь должна быть логика проверки последних N паролей
        # Для простоты возвращаем True
        return True


class SessionSecurityManager:
    """Менеджер безопасности сессий"""
    
    @staticmethod
    def create_secure_session(user, request):
        """Создание безопасной сессии"""
        from django.contrib.auth import login
        
        # Очистка старых сессий пользователя
        SessionSecurityManager.cleanup_user_sessions(user)
        
        # Создание новой сессии
        login(request, user)
        
        # Логирование входа
        AuditLogger.log_user_action(
            user=user,
            action='login',
            request=request
        )
    
    @staticmethod
    def cleanup_user_sessions(user):
        """Очистка старых сессий пользователя"""
        from django.contrib.sessions.models import Session
        from django.contrib.auth.models import AnonymousUser
        
        # Удаление всех сессий пользователя кроме текущей
        user_sessions = Session.objects.filter(
            expire_date__gte=timezone.now()
        )
        
        for session in user_sessions:
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(user.id):
                session.delete()
    
    @staticmethod
    def invalidate_user_sessions(user):
        """Принудительное завершение всех сессий пользователя"""
        SessionSecurityManager.cleanup_user_sessions(user)
        
        # Логирование принудительного завершения сессий
        AuditLogger.log_security_event(
            event_type='force_logout',
            user=user,
            details={'reason': 'Security policy enforcement'}
        )



