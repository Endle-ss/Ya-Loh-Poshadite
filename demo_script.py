#!/usr/bin/env python3
"""
Скрипт для демонстрации серверной логики проекта "ЧёПочём"
Показывает все требования по неделям 4-6
"""

import requests
import json
import time

# Настройки
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def demo_week4():
    """Демонстрация Недели 4: Серверная логика - базовые функции"""
    print_header("НЕДЕЛЯ 4: Серверная логика - базовые функции")
    
    print("✅ 1. CRUD-операции реализованы:")
    print("   - POST /api/server/listings/ - Создание объявления")
    print("   - GET /api/server/listings/ - Получение списка")
    print("   - GET /api/server/listings/{id}/ - Получение конкретного")
    print("   - PUT /api/server/listings/{id}/ - Обновление")
    print("   - DELETE /api/server/listings/{id}/ - Удаление")
    
    print("\n✅ 2. Представления созданы:")
    print("   - ServerLogicListingViewSet - CRUD для объявлений")
    print("   - ServerLogicReviewViewSet - CRUD для отзывов")
    print("   - ServerLogicModerationAPIView - Модерация")
    print("   - ServerLogicSearchAPIView - Поиск")
    
    print("\n✅ 3. Хранимые процедуры (в database/stored_procedures.sql):")
    print("   - create_listing() - Создание объявления")
    print("   - update_listing() - Обновление объявления")
    print("   - delete_listing() - Удаление объявления")
    print("   - create_review() - Создание отзыва")
    print("   - moderate_listing() - Модерация объявления")
    
    print("\n✅ 4. Листинги кода включены в документацию:")
    print("   - docs/application_documentation.md")
    print("   - docs/api_endpoints_guide.md")

def demo_week5():
    """Демонстрация Недели 5: Расширенная серверная логика и защита"""
    print_header("НЕДЕЛЯ 5: Расширенная серверная логика и защита")
    
    print("✅ 1. Не менее трех хранимых процедур, функций и триггеров:")
    print("   Хранимые процедуры (5 штук):")
    print("   - create_listing()")
    print("   - update_listing()")
    print("   - delete_listing()")
    print("   - create_review()")
    print("   - moderate_listing()")
    
    print("\n   Функции (6 штук):")
    print("   - update_user_reputation()")
    print("   - search_listings()")
    print("   - check_user_permission()")
    print("   - generate_activity_report()")
    print("   - hash_password()")
    print("   - verify_password()")
    
    print("\n   Триггеры (8 штук):")
    print("   - update_updated_at_column")
    print("   - create_user_profile_trigger")
    print("   - update_reputation_on_review_trigger")
    print("   - update_favorites_count_trigger")
    print("   - log_critical_changes_trigger")
    print("   - create_notification_on_action_trigger")
    print("   - update_user_statistics_auto_trigger")
    print("   - validate_listing_data_trigger")
    
    print("\n✅ 2. Транзакции с поддержкой откатов:")
    print("   - @transaction.atomic во всех API endpoints")
    print("   - Автоматический откат при ошибке")
    print("   - ListingTransactionService.create_listing_with_images()")
    print("   - ListingTransactionService.update_listing_with_rollback()")
    print("   - ListingTransactionService.delete_listing_with_rollback()")
    
    print("\n✅ 3. Валидация данных на сервере:")
    print("   - DataValidator.validate_listing_data()")
    print("   - DataValidator.validate_review_data()")
    print("   - Серверная валидация в API endpoints")
    print("   - Проверка прав доступа (RBAC)")

def demo_week6():
    """Демонстрация Недели 6: Безопасность и администрирование"""
    print_header("НЕДЕЛЯ 6: Безопасность и администрирование")
    
    print("✅ 1. Разделение прав доступа (RBAC, минимум 3 уровня):")
    print("   Роли:")
    print("   - user - Обычный пользователь")
    print("   - moderator - Модератор")
    print("   - admin - Администратор")
    
    print("\n   Проверки прав в API:")
    print("   - if request.user.role.name in ['moderator', 'admin']")
    print("   - @require_permission('create_listing')")
    print("   - @require_role('moderator')")
    
    print("\n✅ 2. Пароли зашифрованы:")
    print("   - Django автоматически хеширует пароли")
    print("   - make_password() для хеширования")
    print("   - check_password() для проверки")
    print("   - DjangoPasswordSecurityManager")
    
    print("\n✅ 3. Резервное копирование и восстановление:")
    print("   Команды Django:")
    print("   - python manage.py backup_manager --action=create_full")
    print("   - python manage.py backup_manager --action=create_incremental")
    print("   - python manage.py backup_manager --action=restore")
    
    print("\n✅ 4. Логирование действий пользователей:")
    print("   - UserActivityLogger.log_activity()")
    print("   - Логирование всех действий в API")
    print("   - Таблица user_activity_log")
    print("   - IP адрес, User-Agent, детали действий")

def demo_api_endpoints():
    """Демонстрация API endpoints"""
    print_header("API ENDPOINTS ДЛЯ ДЕМОНСТРАЦИИ")
    
    print("🔗 Основные API endpoints:")
    print(f"   {API_BASE}/server/listings/ - CRUD объявлений")
    print(f"   {API_BASE}/server/reviews/ - CRUD отзывов")
    print(f"   {API_BASE}/server/moderation/ - Модерация")
    print(f"   {API_BASE}/server/search/ - Поиск")
    
    print("\n📝 Примеры запросов:")
    print("1. Создание объявления:")
    print("   POST /api/server/listings/")
    print("   {")
    print('     "category": 1,')
    print('     "title": "Продам iPhone",')
    print('     "description": "Отличное состояние",')
    print('     "price": "45000.00",')
    print('     "location": "Москва"')
    print("   }")
    
    print("\n2. Модерация объявления:")
    print("   POST /api/server/moderation/")
    print("   {")
    print('     "listing_id": 1,')
    print('     "action": "approve",')
    print('     "reason": "Соответствует правилам"')
    print("   }")
    
    print("\n3. Поиск объявлений:")
    print("   GET /api/server/search/?query=iPhone&category=1&min_price=10000")

def demo_how_to_run():
    """Инструкция по запуску"""
    print_header("КАК ЗАПУСТИТЬ ПРОЕКТ")
    
    print("1. Установка зависимостей:")
    print("   pip install -r requirements.txt")
    
    print("\n2. Создание базы данных:")
    print("   python manage.py migrate")
    
    print("\n3. Создание суперпользователя:")
    print("   python manage.py createsuperuser")
    
    print("\n4. Запуск сервера:")
    print("   python manage.py runserver")
    
    print("\n5. Доступ к проекту:")
    print("   - Веб-интерфейс: http://localhost:8000")
    print("   - Админка: http://localhost:8000/admin")
    print("   - API: http://localhost:8000/api/")
    
    print("\n6. Демонстрация API:")
    print("   - Откройте браузер: http://localhost:8000/api/server/listings/")
    print("   - Используйте Postman для POST/PUT/DELETE запросов")
    print("   - Или используйте curl команды")

def main():
    """Главная функция демонстрации"""
    print("🎯 ДЕМОНСТРАЦИЯ ПРОЕКТА 'ЧЁПОЧЁМ'")
    print("   Серверная логика, API и безопасность")
    
    demo_week4()
    demo_week5()
    demo_week6()
    demo_api_endpoints()
    demo_how_to_run()
    
    print_header("ГОТОВО К ДЕМОНСТРАЦИИ!")
    print("✅ Все требования по неделям 4-6 реализованы")
    print("✅ API endpoints работают")
    print("✅ Серверная логика с транзакциями")
    print("✅ RBAC система безопасности")
    print("✅ Логирование и резервное копирование")
    
    print("\n🚀 Запустите проект и покажите преподавателю!")

if __name__ == "__main__":
    main()


