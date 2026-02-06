"""
Middleware для автоматического логирования запросов
Неделя 6: Безопасность и администрирование
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from .activity_logger import EnhancedActivityLogger

logger = logging.getLogger('chepochem_app')


class ActivityLoggingMiddleware(MiddlewareMixin):
    """Middleware для автоматического логирования активности пользователей"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Обработка запроса - сохраняем время начала"""
        request._log_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Обработка ответа - логируем запрос"""
        try:
            # Вычисляем длительность запроса
            duration_ms = None
            if hasattr(request, '_log_start_time'):
                duration = time.time() - request._log_start_time
                duration_ms = int(duration * 1000)
            
            # Логируем только важные запросы
            if request.path.startswith('/api/') or response.status_code >= 400:
                EnhancedActivityLogger.log_api_request(
                    request=request,
                    response=response,
                    duration_ms=duration_ms
                )
            
            # Логируем ошибки сервера в error.log
            if response.status_code >= 500:
                import logging
                error_logger = logging.getLogger('chepochem_app.errors')
                user = getattr(request, 'user', None)
                error_logger.error(
                    f"ОШИБКА СЕРВЕРА {response.status_code}: {request.method} {request.path} | "
                    f"Пользователь: {user.username if user and user.is_authenticated else 'anonymous'} | "
                    f"IP: {EnhancedActivityLogger._get_client_ip(request)}"
                )
        
        except Exception as e:
            logger.error(f"Ошибка в ActivityLoggingMiddleware: {str(e)}")
        
        return response
    
    def process_exception(self, request, exception):
        """Обработка исключений - логируем в error.log"""
        try:
            import logging
            error_logger = logging.getLogger('chepochem_app.errors')
            user = getattr(request, 'user', None)
            error_logger.error(
                f"ИСКЛЮЧЕНИЕ: {type(exception).__name__}: {str(exception)} | "
                f"Путь: {request.method} {request.path} | "
                f"Пользователь: {user.username if user and user.is_authenticated else 'anonymous'} | "
                f"IP: {EnhancedActivityLogger._get_client_ip(request)}",
                exc_info=True  # Полный traceback
            )
        except Exception:
            pass  # Не логируем ошибки логирования
        
        return None


class SecurityMiddleware(MiddlewareMixin):
    """Middleware для отслеживания подозрительной активности"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Проверка на подозрительную активность"""
        try:
            # Проверка на частые запросы (базовая защита от DDoS)
            if request.path.startswith('/api/') or request.path.startswith('/admin/'):
                # Здесь можно добавить проверку частоты запросов
                pass
            
            # Проверка на попытки SQL инъекций в параметрах
            # Логируется в error.log если что-то подозрительное
            suspicious_patterns = [
                "'; DROP",
                "UNION SELECT",
                "OR 1=1",
                "<script>",
                "javascript:",
            ]
            
            query_string = request.META.get('QUERY_STRING', '')
            if any(pattern.lower() in query_string.lower() for pattern in suspicious_patterns):
                import logging
                error_logger = logging.getLogger('chepochem_app.errors')
                user = getattr(request, 'user', None)
                error_logger.warning(
                    f"ПОДОЗРИТЕЛЬНЫЙ ЗАПРОС: {request.method} {request.path} | "
                    f"Пользователь: {user.username if user and user.is_authenticated else 'anonymous'} | "
                    f"IP: {EnhancedActivityLogger._get_client_ip(request)} | "
                    f"Паттерн: потенциальная SQL инъекция"
                )
        
        except Exception as e:
            logger.debug(f"Ошибка в SecurityMiddleware: {str(e)}")
        
        return None

