"""
Модуль для импорта и экспорта данных в CSV формате
"""
import csv
import io
from django.http import HttpResponse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Listing, User, Category, Review, UserFavorite
from .django_rbac_security import DjangoAuditLogger
import logging

logger = logging.getLogger(__name__)


class CSVExporter:
    """Класс для экспорта данных в CSV"""
    
    @staticmethod
    def export_listings(queryset, filename='listings_export.csv'):
        """Экспорт объявлений в CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Заголовок', 'Описание', 'Цена', 'Валюта', 'Состояние', 
            'Статус', 'Местоположение', 'Пользователь', 'Категория',
            'Просмотры', 'В избранном', 'Дата создания', 'Дата публикации'
        ])
        
        for listing in queryset.select_related('user', 'category'):
            writer.writerow([
                listing.id,
                listing.title,
                listing.description,
                listing.price,
                listing.currency,
                listing.get_condition_display(),
                listing.get_status_display(),
                listing.location,
                listing.user.username,
                listing.category.name,
                listing.views_count,
                listing.favorites_count,
                listing.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                listing.published_at.strftime('%Y-%m-%d %H:%M:%S') if listing.published_at else '',
            ])
        
        return response
    
    @staticmethod
    def export_users(queryset, filename='users_export.csv'):
        """Экспорт пользователей в CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Имя пользователя', 'Email', 'Имя', 'Фамилия', 
            'Телефон', 'Роль', 'Активен', 'Подтвержден', 'Дата регистрации'
        ])
        
        for user in queryset.select_related('role'):
            writer.writerow([
                user.id,
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                user.phone,
                user.role.name if user.role else '',
                'Да' if user.is_active else 'Нет',
                'Да' if user.is_verified else 'Нет',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response
    
    @staticmethod
    def export_reviews(queryset, filename='reviews_export.csv'):
        """Экспорт отзывов в CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Автор', 'Получатель', 'Оценка', 'Комментарий',
            'Положительный', 'Дата создания'
        ])
        
        for review in queryset.select_related('reviewer', 'reviewed_user'):
            writer.writerow([
                review.id,
                review.reviewer.username,
                review.reviewed_user.username,
                review.rating,
                review.comment,
                'Да' if review.is_positive else 'Нет',
                review.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response


class CSVImporter:
    """Класс для импорта данных из CSV"""
    
    @staticmethod
    @transaction.atomic
    def import_listings(csv_file, user, category_mapping=None):
        """
        Импорт объявлений из CSV
        
        Args:
            csv_file: Файл CSV
            user: Пользователь, который импортирует
            category_mapping: Словарь для маппинга категорий (name -> id)
        
        Returns:
            dict: Результат импорта с количеством успешных и ошибок
        """
        errors = []
        success_count = 0
        
        try:
            # Читаем CSV
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            for row_num, row in enumerate(reader, start=2):  # Начинаем с 2, т.к. 1 строка - заголовок
                try:
                    # Получаем категорию
                    category_name = row.get('Категория', '').strip()
                    if not category_name:
                        errors.append(f"Строка {row_num}: Категория не указана")
                        continue
                    
                    try:
                        if category_mapping and category_name in category_mapping:
                            category_id = category_mapping[category_name]
                        else:
                            category = Category.objects.get(name=category_name)
                            category_id = category.id
                    except Category.DoesNotExist:
                        errors.append(f"Строка {row_num}: Категория '{category_name}' не найдена")
                        continue
                    
                    # Создаем объявление
                    listing = Listing.objects.create(
                        user=user,
                        category_id=category_id,
                        title=row.get('Заголовок', '').strip(),
                        description=row.get('Описание', '').strip(),
                        price=float(row.get('Цена', 0)),
                        currency=row.get('Валюта', 'RUB').strip(),
                        condition=row.get('Состояние', 'used').strip(),
                        status='draft',  # По умолчанию черновик
                        location=row.get('Местоположение', '').strip(),
                    )
                    
                    success_count += 1
                    
                    # Логируем действие
                    DjangoAuditLogger.log_user_action(
                        user=user,
                        action='import',
                        entity_type='listing',
                        entity_id=listing.id,
                        details={'source': 'csv', 'row': row_num}
                    )
                    
                except Exception as e:
                    errors.append(f"Строка {row_num}: {str(e)}")
                    logger.error(f"Ошибка импорта строки {row_num}: {str(e)}")
            
            return {
                'success': True,
                'success_count': success_count,
                'error_count': len(errors),
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Критическая ошибка импорта: {str(e)}")
            return {
                'success': False,
                'success_count': success_count,
                'error_count': len(errors),
                'errors': [f"Критическая ошибка: {str(e)}"] + errors
            }
    
    @staticmethod
    def validate_csv_structure(csv_file, expected_columns):
        """
        Валидация структуры CSV файла
        
        Args:
            csv_file: Файл CSV
            expected_columns: Список ожидаемых колонок
        
        Returns:
            tuple: (is_valid, errors)
        """
        errors = []
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            # Проверяем наличие всех колонок
            if not reader.fieldnames:
                errors.append("CSV файл пуст или не содержит заголовков")
                return False, errors
            
            missing_columns = set(expected_columns) - set(reader.fieldnames)
            if missing_columns:
                errors.append(f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Ошибка чтения CSV: {str(e)}")
            return False, errors


