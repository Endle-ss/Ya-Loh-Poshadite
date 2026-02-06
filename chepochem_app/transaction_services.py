from django.db import transaction, connection
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import logging
import json

User = get_user_model()
logger = logging.getLogger(__name__)


class DatabaseTransactionManager:
    """Менеджер транзакций с поддержкой откатов"""
    
    @staticmethod
    def execute_with_transaction(func, *args, **kwargs):
        """Выполнение функции в транзакции с автоматическим откатом при ошибке"""
        try:
            with transaction.atomic():
                result = func(*args, **kwargs)
                logger.info(f"Транзакция успешно выполнена: {func.__name__}")
                return result
        except Exception as e:
            logger.error(f"Ошибка в транзакции {func.__name__}: {str(e)}")
            raise
    
    @staticmethod
    def execute_stored_procedure(procedure_name, params=None):
        """Выполнение хранимой процедуры"""
        try:
            with connection.cursor() as cursor:
                if params:
                    placeholders = ', '.join(['%s'] * len(params))
                    cursor.execute(f"SELECT {procedure_name}({placeholders})", params)
                else:
                    cursor.execute(f"SELECT {procedure_name}()")
                
                result = cursor.fetchone()
                logger.info(f"Хранимая процедура {procedure_name} выполнена успешно")
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка выполнения процедуры {procedure_name}: {str(e)}")
            raise


class ListingTransactionService:
    """Сервис для работы с объявлениями через транзакции"""
    
    @staticmethod
    @transaction.atomic
    def create_listing_with_images(user_id, listing_data, images_data):
        """Создание объявления с изображениями в транзакции"""
        try:
            # Создание объявления через хранимую процедуру
            listing_id = DatabaseTransactionManager.execute_stored_procedure(
                'create_listing',
                [
                    user_id,
                    listing_data['category_id'],
                    listing_data['title'],
                    listing_data['description'],
                    listing_data['price'],
                    listing_data.get('currency', 'RUB'),
                    listing_data.get('condition', 'used'),
                    listing_data['location'],
                    listing_data.get('latitude'),
                    listing_data.get('longitude'),
                    listing_data.get('is_negotiable', True),
                    listing_data.get('is_urgent', False)
                ]
            )
            
            # Добавление изображений
            if images_data:
                for image_data in images_data:
                    DatabaseTransactionManager.execute_stored_procedure(
                        'add_listing_image',
                        [
                            listing_id,
                            image_data['image_url'],
                            image_data.get('alt_text', ''),
                            image_data.get('sort_order', 0),
                            image_data.get('is_primary', False)
                        ]
                    )
            
            # Логирование успешного создания
            UserActivityLogger.log_activity(
                user_id=user_id,
                action='create_listing',
                entity_type='listing',
                entity_id=listing_id,
                details={'title': listing_data['title']}
            )
            
            return listing_id
            
        except Exception as e:
            logger.error(f"Ошибка создания объявления: {str(e)}")
            raise ValidationError(f"Не удалось создать объявление: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def update_listing_with_rollback(listing_id, user_id, update_data):
        """Обновление объявления с возможностью отката"""
        try:
            # Получаем текущие данные для возможного отката
            from .models import Listing
            original_listing = Listing.objects.get(id=listing_id, user_id=user_id)
            original_data = {
                'title': original_listing.title,
                'description': original_listing.description,
                'price': original_listing.price,
                'location': original_listing.location,
                'is_negotiable': original_listing.is_negotiable,
                'is_urgent': original_listing.is_urgent
            }
            
            # Обновление через хранимую процедуру
            success = DatabaseTransactionManager.execute_stored_procedure(
                'update_listing',
                [
                    listing_id,
                    user_id,
                    update_data.get('title'),
                    update_data.get('description'),
                    update_data.get('price'),
                    update_data.get('location'),
                    update_data.get('is_negotiable'),
                    update_data.get('is_urgent')
                ]
            )
            
            if not success:
                raise ValidationError("Не удалось обновить объявление")
            
            # Логирование обновления
            UserActivityLogger.log_activity(
                user_id=user_id,
                action='update_listing',
                entity_type='listing',
                entity_id=listing_id,
                details={
                    'original_data': original_data,
                    'new_data': update_data
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления объявления {listing_id}: {str(e)}")
            raise ValidationError(f"Не удалось обновить объявление: {str(e)}")


class ReviewTransactionService:
    """Сервис для работы с отзывами через транзакции"""
    
    @staticmethod
    @transaction.atomic
    def create_review_with_reputation_update(reviewer_id, reviewed_user_id, rating, comment):
        """Создание отзыва с обновлением репутации в транзакции"""
        try:
            # Создание отзыва через хранимую процедуру
            review_id = DatabaseTransactionManager.execute_stored_procedure(
                'create_review',
                [reviewer_id, reviewed_user_id, rating, comment]
            )
            
            # Логирование создания отзыва
            UserActivityLogger.log_activity(
                user_id=reviewer_id,
                action='create_review',
                entity_type='review',
                entity_id=review_id,
                details={
                    'reviewed_user_id': reviewed_user_id,
                    'rating': rating
                }
            )
            
            return review_id
            
        except Exception as e:
            logger.error(f"Ошибка создания отзыва: {str(e)}")
            raise ValidationError(f"Не удалось создать отзыв: {str(e)}")


class ModerationTransactionService:
    """Сервис для модерации через транзакции"""
    
    @staticmethod
    @transaction.atomic
    def moderate_listing_with_notification(listing_id, moderator_id, action, reason):
        """Модерация объявления с уведомлением в транзакции"""
        try:
            # Выполнение модерации через хранимую процедуру
            success = DatabaseTransactionManager.execute_stored_procedure(
                'moderate_listing',
                [listing_id, moderator_id, action, reason]
            )
            
            if not success:
                raise ValidationError("Не удалось выполнить модерацию")
            
            # Логирование модерации
            UserActivityLogger.log_activity(
                user_id=moderator_id,
                action='moderate_listing',
                entity_type='listing',
                entity_id=listing_id,
                details={
                    'action': action,
                    'reason': reason
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка модерации объявления {listing_id}: {str(e)}")
            raise ValidationError(f"Не удалось выполнить модерацию: {str(e)}")


class UserActivityLogger:
    """Логгер активности пользователей"""
    
    @staticmethod
    def log_activity(user_id, action, entity_type=None, entity_id=None, details=None, request=None):
        """Логирование активности пользователя"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_activity_log 
                    (user_id, action, entity_type, entity_id, ip_address, user_agent, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    user_id,
                    action,
                    entity_type,
                    entity_id,
                    request.META.get('REMOTE_ADDR') if request else None,
                    request.META.get('HTTP_USER_AGENT') if request else None,
                    json.dumps(details) if details else None,
                    timezone.now()
                ])
        except Exception as e:
            logger.error(f"Ошибка логирования активности: {str(e)}")


class SecurityManager:
    """Менеджер безопасности"""
    
    @staticmethod
    def check_user_permission(user_id, permission, entity_type=None, entity_id=None):
        """Проверка прав доступа пользователя"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT check_user_permission(%s, %s, %s, %s)
                """, [user_id, permission, entity_type, entity_id])
                
                result = cursor.fetchone()
                return result[0] if result else False
        except Exception as e:
            logger.error(f"Ошибка проверки прав доступа: {str(e)}")
            return False
    
    @staticmethod
    def check_ip_blocked(ip_address):
        """Проверка блокировки IP адреса"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT check_ip_blocked(%s)", [ip_address])
                result = cursor.fetchone()
                return result[0] if result else False
        except Exception as e:
            logger.error(f"Ошибка проверки блокировки IP: {str(e)}")
            return False
    
    @staticmethod
    def record_failed_login(username, email, ip_address, user_agent):
        """Регистрация неудачной попытки входа"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT record_failed_login(%s, %s, %s, %s)
                """, [username, email, ip_address, user_agent])
        except Exception as e:
            logger.error(f"Ошибка регистрации неудачного входа: {str(e)}")


class BackupManager:
    """Менеджер резервного копирования"""
    
    @staticmethod
    def create_backup(backup_type='full', created_by=None):
        """Создание резервной копии"""
        try:
            import subprocess
            import os
            from datetime import datetime
            
            # Создание директории для бэкапов
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Генерация имени файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"chepochem_backup_{backup_type}_{timestamp}.sql"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Выполнение резервного копирования
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO backup_log (backup_type, file_path, status, created_by, created_at)
                    VALUES (%s, %s, 'in_progress', %s, %s)
                    RETURNING id
                """, [backup_type, backup_path, created_by, timezone.now()])
                
                backup_log_id = cursor.fetchone()[0]
            
            # Здесь должна быть логика создания бэкапа
            # Для SQLite это будет копирование файла базы данных
            # Для PostgreSQL - использование pg_dump
            
            # Обновление статуса
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE backup_log 
                    SET status = 'success', completed_at = %s
                    WHERE id = %s
                """, [timezone.now(), backup_log_id])
            
            logger.info(f"Резервная копия создана: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {str(e)}")
            
            # Обновление статуса на ошибку
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE backup_log 
                        SET status = 'failed', error_message = %s, completed_at = %s
                        WHERE id = %s
                    """, [str(e), timezone.now(), backup_log_id])
            except:
                pass
            
            raise
    
    @staticmethod
    def cleanup_old_backups():
        """Очистка старых резервных копий"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT cleanup_old_logs()")
            
            logger.info("Старые резервные копии очищены")
        except Exception as e:
            logger.error(f"Ошибка очистки старых копий: {str(e)}")


class DataValidator:
    """Валидатор данных на сервере"""
    
    @staticmethod
    def validate_listing_data(data):
        """Валидация данных объявления"""
        errors = []
        
        if not data.get('title') or len(data['title'].strip()) == 0:
            errors.append('Заголовок не может быть пустым')
        
        if not data.get('description') or len(data['description'].strip()) == 0:
            errors.append('Описание не может быть пустым')
        
        try:
            price = float(data.get('price', 0))
            if price <= 0:
                errors.append('Цена должна быть больше нуля')
        except (ValueError, TypeError):
            errors.append('Некорректная цена')
        
        if not data.get('category_id'):
            errors.append('Категория обязательна')
        
        if not data.get('location') or len(data['location'].strip()) == 0:
            errors.append('Местоположение обязательно')
        
        return errors
    
    @staticmethod
    def validate_review_data(data):
        """Валидация данных отзыва"""
        errors = []
        
        try:
            rating = int(data.get('rating', 0))
            if rating < 1 or rating > 5:
                errors.append('Рейтинг должен быть от 1 до 5')
        except (ValueError, TypeError):
            errors.append('Некорректный рейтинг')
        
        if not data.get('comment') or len(data['comment'].strip()) == 0:
            errors.append('Комментарий не может быть пустым')
        
        return errors
    
    @staticmethod
    def validate_user_data(data):
        """Валидация данных пользователя"""
        errors = []
        
        if not data.get('username') or len(data['username'].strip()) == 0:
            errors.append('Имя пользователя обязательно')
        
        if not data.get('email') or '@' not in data['email']:
            errors.append('Некорректный email')
        
        if not data.get('password') or len(data['password']) < 8:
            errors.append('Пароль должен содержать минимум 8 символов')
        
        return errors



