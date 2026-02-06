# Руководство по API endpoints для демонстрации

## 🎯 **Неделя 4. Серверная логика: базовые функции**

### **✅ CRUD-операции для объявлений:**

#### **Создание объявления:**
```bash
POST http://localhost:8000/api/server/listings/
Content-Type: application/json

{
    "category": 1,
    "title": "Продам iPhone 13",
    "description": "Отличное состояние, без царапин",
    "price": "45000.00",
    "currency": "RUB",
    "condition": "excellent",
    "location": "Москва",
    "is_negotiable": true,
    "is_urgent": false
}
```

#### **Получение списка объявлений:**
```bash
GET http://localhost:8000/api/server/listings/
```

#### **Получение конкретного объявления:**
```bash
GET http://localhost:8000/api/server/listings/1/
```

#### **Обновление объявления:**
```bash
PUT http://localhost:8000/api/server/listings/1/
Content-Type: application/json

{
    "title": "Продам iPhone 13 Pro",
    "price": "50000.00"
}
```

#### **Удаление объявления:**
```bash
DELETE http://localhost:8000/api/server/listings/1/
```

### **✅ Представления (Views) созданы:**

#### **API Views в `server_logic_api.py`:**
- `ServerLogicListingViewSet` - CRUD для объявлений
- `ServerLogicReviewViewSet` - CRUD для отзывов
- `ServerLogicModerationAPIView` - Модерация
- `ServerLogicSearchAPIView` - Поиск

#### **Обычные Views в `views.py`:**
- `home` - Главная страница
- `create_listing` - Создание объявления
- `listing_detail` - Детали объявления
- `user_profile` - Профиль пользователя

### **✅ Хранимые процедуры (эмулированы через Django ORM):**

#### **В `django_orm_services.py`:**
```python
class ListingTransactionService:
    @staticmethod
    @transaction.atomic
    def create_listing_with_images(user_id, listing_data, images_data):
        # Создание объявления с транзакциями
        
    @staticmethod
    @transaction.atomic
    def update_listing_with_rollback(listing_id, user_id, update_data):
        # Обновление с откатом при ошибке
        
    @staticmethod
    @transaction.atomic
    def delete_listing_with_rollback(listing_id, user_id):
        # Удаление с откатом при ошибке
```

---

## 🛡️ **Неделя 5. Расширенная серверная логика и защита**

### **✅ Не менее трех хранимых процедур, функций и триггеров:**

#### **1. Хранимые процедуры (в `database/stored_procedures.sql`):**
```sql
-- Создание объявления
CREATE OR REPLACE FUNCTION create_listing(...)

-- Обновление объявления  
CREATE OR REPLACE FUNCTION update_listing(...)

-- Удаление объявления
CREATE OR REPLACE FUNCTION delete_listing(...)

-- Создание отзыва
CREATE OR REPLACE FUNCTION create_review(...)

-- Модерация объявления
CREATE OR REPLACE FUNCTION moderate_listing(...)
```

#### **2. Функции (в `database/functions.sql`):**
```sql
-- Обновление репутации пользователя
CREATE OR REPLACE FUNCTION update_user_reputation(p_user_id INTEGER)

-- Поиск объявлений
CREATE OR REPLACE FUNCTION search_listings(...)

-- Проверка прав доступа
CREATE OR REPLACE FUNCTION check_user_permission(...)

-- Генерация отчета активности
CREATE OR REPLACE FUNCTION generate_activity_report(...)

-- Хеширование паролей
CREATE OR REPLACE FUNCTION hash_password(p_password TEXT)
```

#### **3. Триггеры (в `database/triggers.sql`):**
```sql
-- Автоматическое обновление updated_at
CREATE TRIGGER update_updated_at_column
    BEFORE UPDATE ON listings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Создание профиля пользователя
CREATE TRIGGER create_user_profile_trigger
    AFTER INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION create_user_profile();

-- Обновление репутации при изменении отзыва
CREATE TRIGGER update_reputation_on_review_trigger
    AFTER INSERT OR UPDATE OR DELETE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_reputation_on_review();
```

### **✅ Транзакции с поддержкой откатов:**

#### **В API endpoints:**
```python
@transaction.atomic
def create(self, request, *args, **kwargs):
    # Создание с автоматическим откатом при ошибке
    try:
        listing_id = ListingTransactionService.create_listing_with_images(...)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        # Автоматический откат транзакции
        return Response({'error': 'Ошибка создания'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

### **✅ Валидация данных на сервере:**

#### **В `django_orm_services.py`:**
```python
class DataValidator:
    @staticmethod
    def validate_listing_data(data):
        errors = []
        if not data.get('title') or len(data['title'].strip()) == 0:
            errors.append('Заголовок не может быть пустым')
        if data.get('price') and data['price'] <= 0:
            errors.append('Цена должна быть больше 0')
        return errors
```

#### **В API endpoints:**
```python
# Серверная валидация данных
validation_errors = DataValidator.validate_listing_data({
    'title': listing_data.get('title'),
    'description': listing_data.get('description'),
    'price': listing_data.get('price'),
    'category_id': listing_data.get('category').id,
    'location': listing_data.get('location')
})

if validation_errors:
    return Response({'errors': validation_errors}, status=status.HTTP_400_BAD_REQUEST)
```

---

## 🔐 **Неделя 6. Безопасность и администрирование**

### **✅ Разделение прав доступа (RBAC, минимум 3 уровня):**

#### **Роли в `models.py`:**
```python
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()

# Роли: 'user', 'moderator', 'admin'
```

#### **Проверка прав в API:**
```python
# Проверка прав доступа (RBAC)
if listing.user != request.user and not request.user.role.name in ['moderator', 'admin']:
    return Response({'error': 'Нет прав на редактирование'}, status=status.HTTP_403_FORBIDDEN)

# Проверка прав модератора
if not request.user.role.name in ['moderator', 'admin']:
    return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
```

#### **Декораторы RBAC в `django_rbac_security.py`:**
```python
@require_permission('create_listing')
def create_listing(request):
    # Создание объявления с проверкой прав

@require_role('moderator')
def moderate_listing(request):
    # Модерация только для модераторов
```

### **✅ Пароли зашифрованы:**

#### **В `models.py`:**
```python
class User(AbstractUser):
    def save(self, *args, **kwargs):
        if not self.pk:  # Новый пользователь
            self.set_password(self.password)  # Автоматическое хеширование
        super().save(*args, **kwargs)
```

#### **В `django_rbac_security.py`:**
```python
class DjangoPasswordSecurityManager:
    @staticmethod
    def hash_password(password):
        return make_password(password)
    
    @staticmethod
    def verify_password(password, hashed):
        return check_password(password, hashed)
```

### **✅ Резервное копирование и восстановление:**

#### **В `management/commands/backup_manager.py`:**
```python
class BackupManager:
    def create_full_backup(self, created_by=None):
        # Создание полной резервной копии
        
    def create_incremental_backup(self, created_by=None):
        # Создание инкрементальной копии
        
    def restore_from_backup(self, backup_path, restore_type='full'):
        # Восстановление из резервной копии
```

#### **Команды Django:**
```bash
# Создание полной резервной копии
python manage.py backup_manager --action=create_full

# Создание инкрементальной копии
python manage.py backup_manager --action=create_incremental

# Восстановление из резервной копии
python manage.py backup_manager --action=restore --backup_path=/path/to/backup
```

### **✅ Логирование действий пользователей:**

#### **В `django_orm_services.py`:**
```python
class UserActivityLogger:
    @staticmethod
    def log_activity(user_id, action, entity_type, entity_id, details=None, request=None):
        # Логирование действий пользователей
        UserActivityLog.objects.create(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT') if request else None,
            details=details
        )
```

#### **В API endpoints:**
```python
# Логирование создания объявления
UserActivityLogger.log_activity(
    user_id=request.user.id,
    action='create_listing',
    entity_type='listing',
    entity_id=listing.id,
    details={'title': listing_data['title']},
    request=request
)

# Логирование просмотра
UserActivityLogger.log_activity(
    user_id=request.user.id if request.user.is_authenticated else None,
    action='view_listing',
    entity_type='listing',
    entity_id=listing.id,
    request=request
)
```

---

## 🎯 **Как показать преподавателю:**

### **1. Демонстрация API через браузер:**
```
http://localhost:8000/api/server/listings/
http://localhost:8000/api/server/reviews/
http://localhost:8000/api/server/moderation/
http://localhost:8000/api/server/search/
```

### **2. Демонстрация через Postman/curl:**

#### **Создание объявления:**
```bash
curl -X POST http://localhost:8000/api/server/listings/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "category": 1,
    "title": "Продам iPhone",
    "description": "Отличное состояние",
    "price": "45000.00",
    "location": "Москва"
  }'
```

#### **Модерация объявления:**
```bash
curl -X POST http://localhost:8000/api/server/moderation/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "listing_id": 1,
    "action": "approve",
    "reason": "Соответствует правилам"
  }'
```

### **3. Показать код:**

#### **Серверная логика в `server_logic_api.py`:**
- Транзакции с `@transaction.atomic`
- Валидация через `DataValidator`
- RBAC проверки
- Логирование через `UserActivityLogger`

#### **Хранимые процедуры в `database/`:**
- `stored_procedures.sql` - процедуры
- `functions.sql` - функции
- `triggers.sql` - триггеры
- `security_tables.sql` - таблицы безопасности

#### **Резервное копирование:**
```bash
python manage.py backup_manager --action=create_full
```

### **4. Показать логи:**
```bash
# Просмотр логов активности
python manage.py shell
>>> from chepochem_app.models import UserActivityLog
>>> UserActivityLog.objects.all().order_by('-created_at')[:10]
```

---

## 📊 **Итоговая проверка требований:**

### **✅ Неделя 4:**
- ✅ CRUD-операции: `POST/GET/PUT/DELETE /api/server/listings/`
- ✅ Представления: `ServerLogicListingViewSet`, `ServerLogicReviewViewSet`
- ✅ Хранимые процедуры: `create_listing`, `update_listing`, `delete_listing`
- ✅ Листинги кода: в `server_logic_api.py`

### **✅ Неделя 5:**
- ✅ 3+ хранимых процедур: `create_listing`, `update_listing`, `delete_listing`, `create_review`, `moderate_listing`
- ✅ 3+ функций: `update_user_reputation`, `search_listings`, `check_user_permission`
- ✅ 3+ триггеров: `update_updated_at_column`, `create_user_profile`, `update_reputation_on_review`
- ✅ Транзакции: `@transaction.atomic` во всех API endpoints
- ✅ Валидация: `DataValidator.validate_listing_data()`

### **✅ Неделя 6:**
- ✅ RBAC (3 уровня): `user`, `moderator`, `admin`
- ✅ Пароли зашифрованы: `make_password()`, `check_password()`
- ✅ Резервное копирование: `BackupManager`
- ✅ Логирование: `UserActivityLogger.log_activity()`
- ✅ Документация: `docs/application_documentation.md`

**ВСЁ РЕАЛИЗОВАНО И РАБОТАЕТ!** 🚀


