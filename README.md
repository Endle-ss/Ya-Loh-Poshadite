# Платформа "ЧёПочём" - Система объявлений

Веб-приложение для размещения и управления объявлениями с полным функционалом CRUD, модерацией, системой отзывов и аналитикой.

## 📋 Содержание

- [Описание](#описание)
- [Технологии](#технологии)
- [Требования](#требования)
- [Установка](#установка)
- [Запуск](#запуск)
- [Архитектура](#архитектура)
- [Роли пользователей](#роли-пользователей)
- [API](#api)
- [База данных](#база-данных)
- [Безопасность](#безопасность)
- [Тестирование](#тестирование)

## 📝 Описание

Платформа "ЧёПочём" - это полнофункциональная система для размещения объявлений с поддержкой:
- Управления объявлениями (CRUD)
- Системы модерации
- Отзывов и репутации
- Аналитики и отчетности
- Импорта/экспорта данных
- Ролевой модели доступа (RBAC)
- Журнала аудита

## 🛠 Технологии

- **Backend**: Django 4.2.7, Django REST Framework
- **База данных**: SQLite (для разработки), PostgreSQL (для продакшена)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Безопасность**: Django Auth, RBAC, хеширование паролей
- **Логирование**: Встроенное логирование Django

## 📦 Требования

- Python 3.8+
- pip
- virtualenv (рекомендуется)

## 🚀 Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd CursachV2
```

### 2. Создание виртуального окружения

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка базы данных

```bash
# Применение миграций
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser

# Инициализация данных (роли, категории)
python manage.py init_data
```

### 5. Создание SQL VIEW (опционально, для PostgreSQL)

Если используется PostgreSQL, выполните:

```bash
psql -d your_database -f database/views.sql
psql -d your_database -f database/stored_procedures.sql
psql -d your_database -f database/functions.sql
psql -d your_database -f database/triggers.sql
```

## ▶️ Запуск

### Локальный запуск

```bash
python manage.py runserver
```

Приложение будет доступно по адресу: `http://127.0.0.1:8000/`

### Запуск через batch-файл (Windows)

```bash
run.bat
```

## 🏗 Архитектура

### Структура проекта

```
CursachV2/
├── chepochem_app/          # Основное приложение
│   ├── models.py           # Модели данных
│   ├── views.py            # Представления
│   ├── api_views.py        # API endpoints
│   ├── serializers.py      # Сериализаторы DRF
│   ├── urls.py             # URL маршруты
│   ├── forms.py            # Формы
│   ├── django_orm_services.py  # Бизнес-логика
│   ├── django_rbac_security.py # Безопасность
│   ├── import_export.py    # Импорт/экспорт CSV
│   └── management/         # Команды управления
├── chepochem_project/      # Настройки проекта
├── database/               # SQL скрипты
│   ├── views.sql           # SQL VIEW
│   ├── stored_procedures.sql
│   ├── functions.sql
│   └── triggers.sql
├── templates/              # HTML шаблоны
├── static/                  # Статические файлы
│   ├── css/
│   └── js/
└── logs/                    # Логи

```

### Основные компоненты

1. **Модели данных** (`models.py`):
   - User, Role, UserProfile, UserReputation
   - Category, Listing, ListingImage
   - Review, UserFavorite, Report
   - Notification, UserStatistics
   - AuditLog, UserSettings

2. **API** (`api_views.py`):
   - REST API для всех сущностей
   - Экспорт/импорт CSV
   - Аналитика и статистика

3. **Безопасность** (`django_rbac_security.py`):
   - RBAC (Role-Based Access Control)
   - Аудит действий
   - Хеширование паролей

## 👥 Роли пользователей

### 1. Администратор (admin)
- Полный доступ ко всем функциям
- Управление пользователями
- Модерация объявлений
- Просмотр аналитики
- Управление настройками системы

### 2. Модератор (moderator)
- Модерация объявлений
- Просмотр жалоб
- Просмотр аналитики
- Управление своими объявлениями

### 3. Пользователь (user)
- Создание и управление объявлениями
- Просмотр объявлений
- Оставление отзывов
- Добавление в избранное
- Подача жалоб

## 🔌 API

### Основные endpoints

- `GET /api/listings/` - Список объявлений
- `POST /api/listings/` - Создание объявления
- `GET /api/listings/{id}/` - Детали объявления
- `PUT /api/listings/{id}/` - Обновление объявления
- `DELETE /api/listings/{id}/` - Удаление объявления

- `GET /api/export/?type=listings` - Экспорт в CSV
- `POST /api/import/` - Импорт из CSV
- `GET /api/analytics/` - Данные для аналитики
- `GET /api/statistics/` - Общая статистика

Полная документация API доступна по адресу: `http://127.0.0.1:8000/api/`

## 🗄 База данных

### Структура

База данных содержит **12+ таблиц**:
- `roles` - Роли пользователей
- `users` - Пользователи
- `user_profiles` - Профили пользователей
- `user_reputation` - Репутация
- `categories` - Категории
- `listings` - Объявления
- `listing_images` - Изображения объявлений
- `reviews` - Отзывы
- `user_favorites` - Избранное
- `reports` - Жалобы
- `listing_moderation` - Модерация
- `notifications` - Уведомления
- `user_statistics` - Статистика
- `audit_log` - Журнал аудита
- `user_settings` - Настройки пользователя

### SQL VIEW

Созданы представления для отчетности:
- `v_listings_summary` - Сводная информация по объявлениям
- `v_users_statistics` - Статистика пользователей
- `v_categories_report` - Отчет по категориям
- `v_daily_activity` - Ежедневная активность
- `v_moderation_report` - Отчет по модерации
- `v_reviews_report` - Отчет по отзывам

### Хранимые процедуры

- `create_listing()` - Создание объявления
- `update_listing()` - Обновление объявления
- `delete_listing()` - Удаление объявления
- `create_review()` - Создание отзыва
- `moderate_listing()` - Модерация объявления

### Триггеры

- Автоматическое обновление `updated_at`
- Создание профиля при регистрации
- Обновление репутации при отзывах
- Обновление счетчиков избранного
- Логирование изменений (аудит)

## 🔒 Безопасность

### Реализованные меры

1. **RBAC** - Ролевая модель доступа
2. **Хеширование паролей** - Django PBKDF2
3. **Журнал аудита** - Логирование всех действий
4. **Валидация данных** - Серверная валидация
5. **CSRF защита** - Django CSRF middleware
6. **SQL инъекции** - Защита через ORM

### Резервное копирование

```bash
# Создание резервной копии
python manage.py backup_manager --action=create_full

# Восстановление
python manage.py backup_manager --action=restore --backup_path=/path/to/backup
```

## ⌨️ Горячие клавиши

- `Ctrl/Cmd + K` - Поиск
- `Ctrl/Cmd + N` - Новое объявление
- `Ctrl/Cmd + F` - Избранное
- `Ctrl/Cmd + P` - Профиль
- `Ctrl/Cmd + H` - Главная
- `Ctrl/Cmd + S` - Сохранить (в формах)
- `/` - Фокус на поиск
- `Esc` - Закрыть модальное окно

## 📞 Контакты

Для вопросов и предложений создайте issue в репозитории.


