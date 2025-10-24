from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class Role(models.Model):
    """Роли пользователей"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Расширенная модель пользователя"""
    email = models.EmailField(unique=True, verbose_name="Электронная почта")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Аватар")
    is_verified = models.BooleanField(default=False, verbose_name="Подтвержден")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    role = models.ForeignKey(Role, on_delete=models.SET_DEFAULT, default=1, verbose_name="Роль")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="Дата обновления")
    last_login = models.DateTimeField(blank=True, null=True, verbose_name="Последний вход")
    
    # Добавляем related_name для избежания конфликтов
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="chepochem_user_set",
        related_query_name="chepochem_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="chepochem_user_set",
        related_query_name="chepochem_user",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """Профиль пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    bio = models.TextField(blank=True, verbose_name="Биография")
    location = models.CharField(max_length=255, blank=True, verbose_name="Местоположение")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Дата рождения")
    gender = models.CharField(max_length=20, blank=True, verbose_name="Пол")
    website = models.URLField(blank=True, verbose_name="Веб-сайт")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"Профиль {self.user.username}"


class UserReputation(models.Model):
    """Репутация пользователя"""
    REPUTATION_LEVELS = [
        ('newbie', 'Новичок'),
        ('trusted', 'Доверенный'),
        ('expert', 'Эксперт'),
        ('master', 'Мастер'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    total_score = models.IntegerField(default=0, verbose_name="Общий балл")
    positive_reviews = models.IntegerField(default=0, verbose_name="Положительные отзывы")
    negative_reviews = models.IntegerField(default=0, verbose_name="Отрицательные отзывы")
    neutral_reviews = models.IntegerField(default=0, verbose_name="Нейтральные отзывы")
    reputation_level = models.CharField(max_length=20, choices=REPUTATION_LEVELS, default='newbie', verbose_name="Уровень репутации")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Репутация пользователя"
        verbose_name_plural = "Репутация пользователей"

    def __str__(self):
        return f"Репутация {self.user.username}"

    def update_reputation(self):
        """Обновление уровня репутации на основе отзывов"""
        total_reviews = self.positive_reviews + self.negative_reviews + self.neutral_reviews
        
        if total_reviews == 0:
            self.reputation_level = 'newbie'
        elif self.positive_reviews >= total_reviews * 0.8:
            self.reputation_level = 'master'
        elif self.positive_reviews >= total_reviews * 0.6:
            self.reputation_level = 'expert'
        else:
            self.reputation_level = 'trusted'
        
        self.save()


class Category(models.Model):
    """Категории товаров"""
    name = models.CharField(max_length=100, verbose_name="Название")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Слаг")
    description = models.TextField(blank=True, verbose_name="Описание")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Иконка")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, verbose_name="Родительская категория")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    sort_order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Listing(models.Model):
    """Объявления"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('pending', 'На модерации'),
        ('active', 'Активно'),
        ('paused', 'Приостановлено'),
        ('sold', 'Продано'),
        ('rejected', 'Отклонено'),
        ('expired', 'Истекло'),
    ]

    CONDITION_CHOICES = [
        ('new', 'Новое'),
        ('used', 'Б/у'),
        ('broken', 'Неисправное'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Категория")
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Цена")
    currency = models.CharField(max_length=3, default='RUB', verbose_name="Валюта")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='used', verbose_name="Состояние")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Статус")
    location = models.CharField(max_length=255, verbose_name="Местоположение")
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True, verbose_name="Широта")
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True, verbose_name="Долгота")
    is_negotiable = models.BooleanField(default=True, verbose_name="Торгуется")
    is_urgent = models.BooleanField(default=False, verbose_name="Срочное")
    views_count = models.IntegerField(default=0, verbose_name="Количество просмотров")
    favorites_count = models.IntegerField(default=0, verbose_name="Количество избранных")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="Дата обновления")
    published_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата публикации")
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата истечения")

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        if self.status == 'active' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class ListingImage(models.Model):
    """Изображения объявлений"""
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, verbose_name="Объявление")
    image = models.ImageField(upload_to='listings/', verbose_name="Изображение")
    thumbnail = models.ImageField(upload_to='listings/thumbnails/', blank=True, null=True, verbose_name="Миниатюра")
    alt_text = models.CharField(max_length=255, blank=True, verbose_name="Альтернативный текст")
    sort_order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    is_primary = models.BooleanField(default=False, verbose_name="Основное")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Изображение объявления"
        verbose_name_plural = "Изображения объявлений"
        ordering = ['sort_order']

    def __str__(self):
        return f"Изображение для {self.listing.title}"


class Review(models.Model):
    """Отзывы"""
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given', verbose_name="Автор отзыва")
    reviewed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received', verbose_name="Получатель отзыва")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Оценка")
    comment = models.TextField(verbose_name="Комментарий")
    is_positive = models.BooleanField(verbose_name="Положительный")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']
        unique_together = ['reviewer', 'reviewed_user']

    def __str__(self):
        return f"Отзыв от {self.reviewer.username} для {self.reviewed_user.username}"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        self.is_positive = self.rating >= 4
        super().save(*args, **kwargs)
        
        # Обновляем репутацию пользователя
        self.update_user_reputation()

    def update_user_reputation(self):
        """Обновление репутации пользователя после отзыва"""
        reputation, created = UserReputation.objects.get_or_create(user=self.reviewed_user)
        
        if self.is_positive:
            reputation.positive_reviews += 1
        elif self.rating <= 2:
            reputation.negative_reviews += 1
        else:
            reputation.neutral_reviews += 1
        
        reputation.total_score += self.rating
        reputation.update_reputation()


class UserFavorite(models.Model):
    """Избранные объявления"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, verbose_name="Объявление")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Избранное объявление"
        verbose_name_plural = "Избранные объявления"
        unique_together = ['user', 'listing']

    def __str__(self):
        return f"{self.user.username} добавил в избранное {self.listing.title}"


class Report(models.Model):
    """Жалобы"""
    REPORT_TYPES = [
        ('spam', 'Спам'),
        ('inappropriate', 'Неподходящий контент'),
        ('fraud', 'Мошенничество'),
        ('duplicate', 'Дубликат'),
        ('other', 'Другое'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Ожидает рассмотрения'),
        ('in_progress', 'В работе'),
        ('resolved', 'Решено'),
        ('dismissed', 'Отклонено'),
    ]

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made', verbose_name="Подавший жалобу")
    reported_user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='reports_received', verbose_name="На кого подана жалоба")
    reported_listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="На какое объявление подана жалоба")
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES, verbose_name="Тип жалобы")
    description = models.TextField(verbose_name="Описание")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='reports_moderated', verbose_name="Модератор")
    resolution = models.TextField(blank=True, verbose_name="Решение")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата решения")

    class Meta:
        verbose_name = "Жалоба"
        verbose_name_plural = "Жалобы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Жалоба от {self.reporter.username}"


class ListingModeration(models.Model):
    """Модерация объявлений"""
    ACTION_CHOICES = [
        ('approve', 'Одобрить'),
        ('reject', 'Отклонить'),
        ('pause', 'Приостановить'),
        ('unpause', 'Возобновить'),
    ]

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, verbose_name="Объявление")
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Модератор")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Действие")
    reason = models.TextField(blank=True, verbose_name="Причина")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Модерация объявления"
        verbose_name_plural = "Модерация объявлений"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} объявления {self.listing.title}"


class Notification(models.Model):
    """Уведомления"""
    NOTIFICATION_TYPES = [
        ('listing_approved', 'Объявление одобрено'),
        ('listing_rejected', 'Объявление отклонено'),
        ('new_review', 'Новый отзыв'),
        ('new_message', 'Новое сообщение'),
        ('listing_expired', 'Объявление истекло'),
        ('report_resolved', 'Жалоба рассмотрена'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, verbose_name="Тип")
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    content = models.TextField(blank=True, verbose_name="Содержание")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    related_entity_type = models.CharField(max_length=50, blank=True, verbose_name="Тип связанной сущности")
    related_entity_id = models.IntegerField(blank=True, null=True, verbose_name="ID связанной сущности")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']

    def __str__(self):
        return f"Уведомление для {self.user.username}: {self.title}"


class UserStatistics(models.Model):
    """Статистика пользователей"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    listings_count = models.IntegerField(default=0, verbose_name="Количество объявлений")
    sold_count = models.IntegerField(default=0, verbose_name="Количество проданных")
    purchased_count = models.IntegerField(default=0, verbose_name="Количество купленных")
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Общий доход")
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Общие расходы")
    response_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Процент ответов")
    average_response_time = models.IntegerField(default=0, verbose_name="Среднее время ответа (минуты)")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Статистика пользователя"
        verbose_name_plural = "Статистика пользователей"

    def __str__(self):
        return f"Статистика {self.user.username}"
