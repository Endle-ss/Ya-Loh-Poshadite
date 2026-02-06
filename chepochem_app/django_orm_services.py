from django.db import transaction, connection
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.db.models import Q, Count, Sum, Avg
import logging
import json
from datetime import datetime, timedelta

User = get_user_model()
logger = logging.getLogger(__name__)


class DjangoTransactionManager:
    """Менеджер транзакций для Django ORM"""
    
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
    def execute_raw_sql(query, params=None):
        """Выполнение сырого SQL запроса"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params or [])
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка выполнения SQL: {str(e)}")
            raise


class ListingTransactionService:
    """Сервис для работы с объявлениями через Django ORM"""
    
    @staticmethod
    @transaction.atomic
    def create_listing_with_images(user_id, listing_data, images_data):
        """Создание объявления с изображениями в транзакции"""
        try:
            from .models import Listing, ListingImage, UserStatistics
            
            # Валидация данных
            if not listing_data.get('title') or len(listing_data['title'].strip()) == 0:
                raise ValidationError('Заголовок не может быть пустым')
            
            if listing_data.get('price', 0) <= 0:
                raise ValidationError('Цена должна быть больше нуля')
            
            # Проверка существования пользователя
            user = User.objects.get(id=user_id, is_active=True)
            
            # Создание объявления
            listing = Listing.objects.create(
                user=user,
                category_id=listing_data['category_id'],
                title=listing_data['title'],
                description=listing_data['description'],
                price=listing_data['price'],
                currency=listing_data.get('currency', 'RUB'),
                condition=listing_data.get('condition', 'used'),
                location=listing_data['location'],
                latitude=listing_data.get('latitude'),
                longitude=listing_data.get('longitude'),
                is_negotiable=listing_data.get('is_negotiable', True),
                is_urgent=listing_data.get('is_urgent', False),
                status='pending'
            )
            
            # Добавление изображений
            if images_data:
                for image_data in images_data:
                    ListingImage.objects.create(
                        listing=listing,
                        image=image_data['image'],  # Передаем сам файл, Django сохранит его автоматически
                        alt_text=image_data.get('alt_text', ''),
                        sort_order=image_data.get('sort_order', 0),
                        is_primary=image_data.get('is_primary', False)
                    )
            
            # Обновление статистики пользователя
            stats, created = UserStatistics.objects.get_or_create(user=user)
            stats.listings_count += 1
            stats.save()
            
            # Логирование действия
            UserActivityLogger.log_activity(
                user_id=user_id,
                action='create_listing',
                entity_type='listing',
                entity_id=listing.id,
                details={'title': listing_data['title']}
            )
            
            return listing.id
            
        except Exception as e:
            logger.error(f"Ошибка создания объявления: {str(e)}")
            raise ValidationError(f"Не удалось создать объявление: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def update_listing_with_rollback(listing_id, user_id, update_data):
        """Обновление объявления с возможностью отката"""
        try:
            from .models import Listing
            
            # Получаем текущие данные для возможного отката
            listing = Listing.objects.get(id=listing_id, user_id=user_id)
            original_data = {
                'title': listing.title,
                'description': listing.description,
                'price': listing.price,
                'location': listing.location,
                'is_negotiable': listing.is_negotiable,
                'is_urgent': listing.is_urgent
            }
            
            # Валидация данных
            if update_data.get('title') and len(update_data['title'].strip()) == 0:
                raise ValidationError('Заголовок не может быть пустым')
            
            if update_data.get('price') and update_data['price'] <= 0:
                raise ValidationError('Цена должна быть больше нуля')
            
            # Обновление объявления
            listing.title = update_data.get('title', listing.title)
            listing.description = update_data.get('description', listing.description)
            listing.price = update_data.get('price', listing.price)
            listing.location = update_data.get('location', listing.location)
            listing.is_negotiable = update_data.get('is_negotiable', listing.is_negotiable)
            listing.is_urgent = update_data.get('is_urgent', listing.is_urgent)
            listing.status = 'pending'  # Снова отправляем на модерацию
            listing.save()
            
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
    
    @staticmethod
    @transaction.atomic
    def delete_listing_with_rollback(listing_id, user_id):
        """Удаление объявления с возможностью отката"""
        try:
            from .models import Listing, UserStatistics
            
            # Проверка прав доступа
            listing = Listing.objects.get(id=listing_id)
            user = User.objects.get(id=user_id)
            
            # Проверка прав (владелец или модератор/админ)
            if listing.user_id != user_id and user.role.name not in ['moderator', 'admin']:
                raise ValidationError('Нет прав на удаление объявления')
            
            # Логирование перед удалением
            UserActivityLogger.log_activity(
                user_id=user_id,
                action='delete_listing',
                entity_type='listing',
                entity_id=listing_id,
                details={'title': listing.title}
            )
            
            # Обновление статистики пользователя
            stats, created = UserStatistics.objects.get_or_create(user=listing.user)
            stats.listings_count = max(stats.listings_count - 1, 0)
            stats.save()
            
            # Удаление объявления (каскадное удаление изображений и избранного)
            listing.delete()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления объявления {listing_id}: {str(e)}")
            raise ValidationError(f"Не удалось удалить объявление: {str(e)}")


class ReviewTransactionService:
    """Сервис для работы с отзывами через Django ORM"""
    
    @staticmethod
    @transaction.atomic
    def create_review_with_reputation_update(reviewer_id, reviewed_user_id, rating, comment):
        """Создание отзыва с обновлением репутации в транзакции"""
        try:
            from .models import Review, UserReputation
            
            # Валидация входных данных
            if rating < 1 or rating > 5:
                raise ValidationError('Рейтинг должен быть от 1 до 5')
            
            if reviewer_id == reviewed_user_id:
                raise ValidationError('Нельзя оставить отзыв самому себе')
            
            # Проверка существования пользователей
            reviewer = User.objects.get(id=reviewer_id, is_active=True)
            reviewed_user = User.objects.get(id=reviewed_user_id, is_active=True)
            
            # Проверка на существующий отзыв
            if Review.objects.filter(reviewer_id=reviewer_id, reviewed_user_id=reviewed_user_id).exists():
                raise ValidationError('Отзыв уже существует')
            
            # Создание отзыва
            review = Review.objects.create(
                reviewer=reviewer,
                reviewed_user=reviewed_user,
                rating=rating,
                comment=comment,
                is_positive=(rating >= 4)
            )
            
            # Обновление репутации пользователя
            ReputationService.update_user_reputation(reviewed_user_id)
            
            # Логирование действия
            UserActivityLogger.log_activity(
                user_id=reviewer_id,
                action='create_review',
                entity_type='review',
                entity_id=review.id,
                details={
                    'reviewed_user_id': reviewed_user_id,
                    'rating': rating
                }
            )
            
            return review.id
            
        except Exception as e:
            logger.error(f"Ошибка создания отзыва: {str(e)}")
            raise ValidationError(f"Не удалось создать отзыв: {str(e)}")


class ModerationTransactionService:
    """Сервис для модерации через Django ORM"""
    
    @staticmethod
    @transaction.atomic
    def moderate_listing_with_notification(listing_id, moderator_id, action, reason):
        """Модерация объявления с уведомлением в транзакции"""
        try:
            from .models import Listing, ListingModeration, Notification
            
            # Проверка прав модератора
            moderator = User.objects.get(id=moderator_id)
            if moderator.role.name not in ['moderator', 'admin']:
                raise ValidationError('Недостаточно прав для модерации')
            
            # Получение объявления
            listing = Listing.objects.get(id=listing_id, status='pending')
            
            # Выполнение действия модерации
            if action == 'approve':
                listing.status = 'active'
                listing.published_at = timezone.now()
                listing.save()
                
                # Уведомление пользователя
                Notification.objects.create(
                    user=listing.user,
                    type='listing_approved',
                    title='Объявление одобрено',
                    content=f'Ваше объявление "{listing.title}" было одобрено и опубликовано.',
                    related_entity_type='listing',
                    related_entity_id=listing.id
                )
                
            elif action == 'reject':
                listing.status = 'rejected'
                listing.save()
                
                # Уведомление пользователя
                Notification.objects.create(
                    user=listing.user,
                    type='listing_rejected',
                    title='Объявление отклонено',
                    content=f'Ваше объявление "{listing.title}" было отклонено. Причина: {reason or "Не указана"}',
                    related_entity_type='listing',
                    related_entity_id=listing.id
                )
                
            else:
                raise ValidationError('Неверное действие модерации')
            
            # Запись действия модерации
            ListingModeration.objects.create(
                listing=listing,
                moderator=moderator,
                action=action,
                reason=reason
            )
            
            # Логирование действия
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


class ReputationService:
    """Сервис для работы с репутацией через Django ORM"""
    
    @staticmethod
    def update_user_reputation(user_id):
        """Обновление репутации пользователя"""
        try:
            from .models import UserReputation, Review
            
            # Подсчет отзывов
            reviews = Review.objects.filter(reviewed_user_id=user_id)
            total_reviews = reviews.count()
            positive_count = reviews.filter(is_positive=True).count()
            negative_count = reviews.filter(is_positive=False, rating__lte=2).count()
            neutral_count = reviews.filter(is_positive=False, rating__gt=2).count()
            total_score = reviews.aggregate(total=Sum('rating'))['total'] or 0
            
            # Определение уровня репутации
            if total_reviews == 0:
                reputation_level = 'newbie'
            elif positive_count >= total_reviews * 0.8:
                reputation_level = 'master'
            elif positive_count >= total_reviews * 0.6:
                reputation_level = 'expert'
            else:
                reputation_level = 'trusted'
            
            # Обновление или создание записи репутации
            reputation, created = UserReputation.objects.get_or_create(
                user_id=user_id,
                defaults={
                    'total_score': total_score,
                    'positive_reviews': positive_count,
                    'negative_reviews': negative_count,
                    'neutral_reviews': neutral_count,
                    'reputation_level': reputation_level
                }
            )
            
            if not created:
                reputation.total_score = total_score
                reputation.positive_reviews = positive_count
                reputation.negative_reviews = negative_count
                reputation.neutral_reviews = neutral_count
                reputation.reputation_level = reputation_level
                reputation.save()
            
        except Exception as e:
            logger.error(f"Ошибка обновления репутации пользователя {user_id}: {str(e)}")


class SearchService:
    """Сервис поиска через Django ORM"""
    
    @staticmethod
    def search_listings(search_query=None, category_id=None, min_price=None, 
                       max_price=None, location=None, sort_by='newest', 
                       limit=20, offset=0):
        """Поиск объявлений с фильтрацией"""
        try:
            from .models import Listing
            
            # Базовый запрос
            queryset = Listing.objects.filter(status='active').select_related(
                'user', 'category'
            ).prefetch_related('listingimage_set')
            
            # Применение фильтров
            if search_query:
                queryset = queryset.filter(
                    Q(title__icontains=search_query) | 
                    Q(description__icontains=search_query) |
                    Q(location__icontains=search_query)
                )
            
            if category_id:
                queryset = queryset.filter(category_id=category_id)
            
            if min_price:
                queryset = queryset.filter(price__gte=min_price)
            
            if max_price:
                queryset = queryset.filter(price__lte=max_price)
            
            if location:
                queryset = queryset.filter(location__icontains=location)
            
            # Сортировка
            if sort_by == 'price_low':
                queryset = queryset.order_by('price')
            elif sort_by == 'price_high':
                queryset = queryset.order_by('-price')
            elif sort_by == 'popular':
                queryset = queryset.order_by('-views_count')
            else:  # newest
                queryset = queryset.order_by('-created_at')
            
            # Пагинация
            total_count = queryset.count()
            listings = queryset[offset:offset + limit]
            
            return {
                'listings': list(listings),
                'total_count': total_count,
                'has_next': offset + limit < total_count,
                'has_previous': offset > 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка поиска объявлений: {str(e)}")
            return {'listings': [], 'total_count': 0, 'has_next': False, 'has_previous': False}


class UserActivityLogger:
    """Логгер активности пользователей для Django ORM"""
    
    @staticmethod
    def log_activity(user_id, action, entity_type=None, entity_id=None, details=None, request=None):
        """Логирование активности пользователя"""
        try:
            # Создаем таблицу логов, если её нет
            DjangoTransactionManager.execute_raw_sql("""
                CREATE TABLE IF NOT EXISTS user_activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action VARCHAR(100) NOT NULL,
                    entity_type VARCHAR(50),
                    entity_id INTEGER,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Вставляем запись
            DjangoTransactionManager.execute_raw_sql("""
                INSERT INTO user_activity_log 
                (user_id, action, entity_type, entity_id, ip_address, user_agent, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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


class DataValidator:
    """Валидатор данных на сервере для Django ORM"""
    
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



