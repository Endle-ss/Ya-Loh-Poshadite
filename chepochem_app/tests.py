"""
Базовые тесты для проекта
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import Role, Category, Listing, Review, UserSettings, AuditLog

User = get_user_model()


class UserModelTest(TestCase):
    """Тесты модели User"""
    
    def setUp(self):
        self.role = Role.objects.create(name='user', description='Обычный пользователь')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
    
    def test_user_creation(self):
        """Тест создания пользователя"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))
    
    def test_user_password_hashing(self):
        """Тест хеширования пароля"""
        self.assertNotEqual(self.user.password, 'testpass123')
        self.assertTrue(self.user.check_password('testpass123'))


class ListingModelTest(TestCase):
    """Тесты модели Listing"""
    
    def setUp(self):
        self.role = Role.objects.create(name='user')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category'
        )
    
    def test_listing_creation(self):
        """Тест создания объявления"""
        listing = Listing.objects.create(
            user=self.user,
            category=self.category,
            title='Тестовое объявление',
            description='Описание тестового объявления',
            price=1000.00,
            location='Москва'
        )
        self.assertEqual(listing.title, 'Тестовое объявление')
        self.assertEqual(listing.status, 'draft')
    
    def test_listing_validation(self):
        """Тест валидации объявления"""
        listing = Listing(
            user=self.user,
            category=self.category,
            title='Короткий',
            description='Описание',
            price=-100,
            location='Москва'
        )
        with self.assertRaises(Exception):
            listing.full_clean()


class ReviewModelTest(TestCase):
    """Тесты модели Review"""
    
    def setUp(self):
        self.role = Role.objects.create(name='user')
        self.reviewer = User.objects.create_user(
            username='reviewer',
            email='reviewer@example.com',
            password='testpass123',
            role=self.role
        )
        self.reviewed_user = User.objects.create_user(
            username='reviewed',
            email='reviewed@example.com',
            password='testpass123',
            role=self.role
        )
    
    def test_review_creation(self):
        """Тест создания отзыва"""
        review = Review.objects.create(
            reviewer=self.reviewer,
            reviewed_user=self.reviewed_user,
            rating=5,
            comment='Отличный пользователь!'
        )
        self.assertEqual(review.rating, 5)
        self.assertTrue(review.is_positive)
    
    def test_review_self_review_prevention(self):
        """Тест предотвращения отзыва самому себе"""
        review = Review(
            reviewer=self.reviewer,
            reviewed_user=self.reviewer,
            rating=5,
            comment='Тест'
        )
        with self.assertRaises(Exception):
            review.full_clean()


class APITest(TestCase):
    """Интеграционные тесты API"""
    
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.create(name='user')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category'
        )
    
    def test_listings_api_list(self):
        """Тест получения списка объявлений через API"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/api/listings/')
        self.assertEqual(response.status_code, 200)
    
    def test_listings_api_create(self):
        """Тест создания объявления через API"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'title': 'Тестовое объявление',
            'description': 'Описание',
            'price': 1000,
            'category': self.category.id,
            'location': 'Москва'
        }
        response = self.client.post('/api/listings/', data)
        self.assertEqual(response.status_code, 201)


class SecurityTest(TestCase):
    """Тесты безопасности"""
    
    def setUp(self):
        self.client = Client()
        self.user_role = Role.objects.create(name='user')
        self.admin_role = Role.objects.create(name='admin')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.user_role
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role=self.admin_role
        )
    
    def test_unauthorized_access(self):
        """Тест доступа неавторизованного пользователя"""
        response = self.client.get('/api/listings/')
        # Должен быть доступен для чтения
        self.assertIn(response.status_code, [200, 401])
    
    def test_role_based_access(self):
        """Тест разграничения доступа по ролям"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/api/statistics/')
        # Обычный пользователь не должен иметь доступа
        self.assertEqual(response.status_code, 403)


class TransactionTest(TestCase):
    """Тесты транзакций"""
    
    def setUp(self):
        self.role = Role.objects.create(name='user')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category'
        )
    
    def test_listing_creation_transaction(self):
        """Тест атомарности создания объявления"""
        from django.db import transaction
        from django.db.utils import IntegrityError
        
        try:
            with transaction.atomic():
                listing = Listing.objects.create(
                    user=self.user,
                    category=self.category,
                    title='Тест',
                    description='Описание',
                    price=1000,
                    location='Москва'
                )
                # Симулируем ошибку
                raise Exception("Test error")
        except Exception:
            pass
        
        # Объявление не должно быть создано
        self.assertEqual(Listing.objects.count(), 0)


