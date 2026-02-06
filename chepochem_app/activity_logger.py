"""
Улучшенная система логирования активности пользователей
Неделя 6: Безопасность и администрирование
"""
import json
import logging
from django.utils import timezone
from django.db import connection, transaction
from django.contrib.auth import get_user_model
import traceback

User = get_user_model()

# Логгеры для разных типов событий
activity_logger = logging.getLogger('chepochem_app.activity')
error_logger = logging.getLogger('chepochem_app.errors')
logger = logging.getLogger('chepochem_app')


class EnhancedActivityLogger:
    """Улучшенный логгер активности пользователей"""
    
    @staticmethod
    def _get_client_ip(request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    @staticmethod
    def _get_user_agent(request):
        """Получение User-Agent"""
        return request.META.get('HTTP_USER_AGENT', 'unknown')
    
    @staticmethod
    def _get_request_path(request):
        """Получение пути запроса"""
        return request.path
    
    @staticmethod
    def _get_request_method(request):
        """Получение метода запроса"""
        return request.method
    
    @staticmethod
    def _get_request_params(request):
        """Получение параметров запроса (GET/POST)"""
        params = {}
        if request.GET:
            params['GET'] = dict(request.GET)
        if hasattr(request, 'POST') and request.POST:
            params['POST'] = {k: v for k, v in request.POST.items() if k != 'password' and k != 'password1' and k != 'password2'}
        if hasattr(request, 'data') and request.data:
            data = dict(request.data)
            # Убираем пароли из данных
            if 'password' in data:
                data['password'] = '***HIDDEN***'
            if 'password1' in data:
                data['password1'] = '***HIDDEN***'
            if 'password2' in data:
                data['password2'] = '***HIDDEN***'
            params['data'] = data
        return params
    
    @classmethod
    def log_user_action(cls, user, action, entity_type=None, entity_id=None, 
                       details=None, request=None, success=True, error_message=None):
        """
        Логирование действия пользователя
        
        Args:
            user: Пользователь (может быть None для анонимных действий)
            action: Тип действия (create_listing, login, delete_review и т.д.)
            entity_type: Тип сущности (listing, review, user и т.д.)
            entity_id: ID сущности
            details: Дополнительные детали (dict)
            request: HTTP запрос (для извлечения IP, User-Agent и т.д.)
            success: Успешность операции
            error_message: Сообщение об ошибке (если есть)
        """
        try:
            user_id = user.id if user and user.is_authenticated else None
            username = user.username if user and user.is_authenticated else 'anonymous'
            
            # Подготовка данных для логирования
            log_data = {
                'user_id': user_id,
                'username': username,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'success': success,
                'timestamp': timezone.now().isoformat(),
            }
            
            # Информация из запроса
            if request:
                log_data['ip_address'] = cls._get_client_ip(request)
                log_data['user_agent'] = cls._get_user_agent(request)
                log_data['request_path'] = cls._get_request_path(request)
                log_data['request_method'] = cls._get_request_method(request)
                log_data['request_params'] = cls._get_request_params(request)
            
            # Дополнительные детали
            if details:
                log_data['details'] = details
            
            # Сообщение об ошибке
            if error_message:
                log_data['error_message'] = error_message
            
            # Логирование в файл (JSON формат)
            activity_logger.info(json.dumps(log_data, ensure_ascii=False))
            
            # Логирование в базу данных
            cls._log_to_database(log_data)
            
            # Логирование ошибок отдельно (только критические ошибки в error.log)
            if not success and error_message:
                error_logger.error(
                    f"ОШИБКА: Действие '{action}' пользователя '{username}' (ID: {user_id}) "
                    f"не выполнено: {error_message}"
                )
            
        except Exception as e:
            logger.error(f"Ошибка при логировании активности: {str(e)}\n{traceback.format_exc()}")
    
    @staticmethod
    def _log_to_database(log_data):
        """Сохранение лога в базу данных"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_activity_log 
                    (user_id, action, entity_type, entity_id, ip_address, user_agent, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    log_data.get('user_id'),
                    log_data.get('action'),
                    log_data.get('entity_type'),
                    log_data.get('entity_id'),
                    log_data.get('ip_address'),
                    log_data.get('user_agent'),
                    json.dumps(log_data.get('details', {}), ensure_ascii=False) if log_data.get('details') else None,
                    timezone.now()
                ])
        except Exception as e:
            # Если таблица не существует, просто пропускаем
            logger.debug(f"Не удалось сохранить лог в БД (возможно, таблица не создана): {str(e)}")
    
    @classmethod
    def log_security_event(cls, event_type, user=None, ip_address=None, 
                          details=None, request=None, severity='warning'):
        """
        Логирование события безопасности (теперь в error.log)
        
        Args:
            event_type: Тип события (login_failed, permission_denied, suspicious_activity и т.д.)
            user: Пользователь (если применимо)
            ip_address: IP адрес
            details: Дополнительные детали
            request: HTTP запрос
            severity: Уровень серьезности (info, warning, error, critical)
        """
        try:
            if request:
                ip_address = ip_address or cls._get_client_ip(request)
                user_agent = cls._get_user_agent(request)
                request_path = cls._get_request_path(request)
            else:
                user_agent = None
                request_path = None
            
            user_id = user.id if user and user.is_authenticated else None
            username = user.username if user and user.is_authenticated else 'anonymous'
            
            # Логируем в error.log
            log_message = (
                f"СОБЫТИЕ БЕЗОПАСНОСТИ [{severity.upper()}]: {event_type} | "
                f"Пользователь: {username} | "
                f"IP: {ip_address} | "
                f"Путь: {request_path} | "
                f"Детали: {details}"
            )
            
            if severity in ['critical', 'error']:
                error_logger.error(log_message)
            else:
                error_logger.warning(log_message)
            
            # Также логируем в базу данных
            cls._log_to_database({
                'user_id': user_id,
                'action': f'security_{event_type}',
                'ip_address': ip_address,
                'user_agent': user_agent,
                'details': {'event_type': event_type, 'severity': severity, **(details or {})}
            })
            
        except Exception as e:
            logger.error(f"Ошибка при логировании события безопасности: {str(e)}\n{traceback.format_exc()}")
    
    @classmethod
    def log_api_request(cls, request, response=None, duration_ms=None):
        """Логирование API запросов"""
        try:
            user = getattr(request, 'user', None)
            
            api_data = {
                'type': 'api_request',
                'method': cls._get_request_method(request),
                'path': cls._get_request_path(request),
                'user_id': user.id if user and user.is_authenticated else None,
                'username': user.username if user and user.is_authenticated else 'anonymous',
                'ip_address': cls._get_client_ip(request),
                'status_code': response.status_code if response else None,
                'duration_ms': duration_ms,
                'timestamp': timezone.now().isoformat(),
            }
            
            # Логируем только важные запросы или ошибки
            if response and (response.status_code >= 400 or duration_ms and duration_ms > 1000):
                activity_logger.info(json.dumps(api_data, ensure_ascii=False))
        
        except Exception as e:
            logger.debug(f"Ошибка при логировании API запроса: {str(e)}")
    
    @classmethod
    def log_transaction(cls, transaction_type, user, success=True, 
                       details=None, error=None, request=None):
        """Логирование транзакций"""
        try:
            cls.log_user_action(
                user=user,
                action=f'transaction_{transaction_type}',
                entity_type='transaction',
                details={
                    'transaction_type': transaction_type,
                    'success': success,
                    'error': str(error) if error else None,
                    **(details or {})
                },
                request=request,
                success=success,
                error_message=str(error) if error else None
            )
        except Exception as e:
            logger.error(f"Ошибка при логировании транзакции: {str(e)}")


# Удобные функции для быстрого использования
def log_action(user, action, entity_type=None, entity_id=None, details=None, request=None, success=True):
    """Удобная функция для логирования действий"""
    EnhancedActivityLogger.log_user_action(
        user=user, action=action, entity_type=entity_type, 
        entity_id=entity_id, details=details, request=request, success=success
    )


def log_security(event_type, user=None, ip_address=None, details=None, request=None, severity='warning'):
    """Удобная функция для логирования событий безопасности"""
    EnhancedActivityLogger.log_security_event(
        event_type=event_type, user=user, ip_address=ip_address,
        details=details, request=request, severity=severity
    )

