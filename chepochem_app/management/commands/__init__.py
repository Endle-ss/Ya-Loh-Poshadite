from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from chepochem_app.models import Role, Category

User = get_user_model()


class Command(BaseCommand):
    help = 'Инициализация базовых данных для ЧёПочём'

    def handle(self, *args, **options):
        self.stdout.write('Создание ролей...')
        self.create_roles()
        
        self.stdout.write('Создание категорий...')
        self.create_categories()
        
        self.stdout.write('Создание администратора...')
        self.create_admin()
        
        self.stdout.write(self.style.SUCCESS('Инициализация завершена!'))

    def create_roles(self):
        roles_data = [
            ('user', 'Обычный пользователь'),
            ('moderator', 'Модератор'),
            ('admin', 'Администратор'),
        ]
        
        for name, description in roles_data:
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            if created:
                self.stdout.write(f'  Создана роль: {name}')

    def create_categories(self):
        categories_data = [
            ('Транспорт', 'transport', 'Автомобили, мотоциклы, велосипеды и запчасти', 'car'),
            ('Недвижимость', 'real-estate', 'Квартиры, дома, участки', 'home'),
            ('Работа', 'jobs', 'Вакансии и резюме', 'briefcase'),
            ('Услуги', 'services', 'Бытовые, профессиональные услуги', 'tools'),
            ('Личные вещи', 'personal', 'Одежда, обувь, аксессуары', 'user'),
            ('Для дома и дачи', 'home-garden', 'Мебель, техника, сад', 'home'),
            ('Хобби и отдых', 'hobby', 'Спорт, туризм, коллекционирование', 'heart'),
            ('Животные', 'animals', 'Питомцы, корм, аксессуары', 'paw'),
            ('Бизнес и оборудование', 'business', 'Оборудование, сырье, готовая продукция', 'briefcase'),
            ('Электроника', 'electronics', 'Телефоны, компьютеры, бытовая техника', 'smartphone'),
        ]
        
        for name, slug, description, icon in categories_data:
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'description': description,
                    'icon': icon
                }
            )
            if created:
                self.stdout.write(f'  Создана категория: {name}')

    def create_admin(self):
        admin_role = Role.objects.get(name='admin')
        
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@chepochem.ru',
                'first_name': 'Админ',
                'last_name': 'Админов',
                'phone': '+7-900-000-0001',
                'role': admin_role,
                'is_staff': True,
                'is_superuser': True,
                'is_verified': True,
            }
        )
        
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('  Создан администратор: admin / admin123')
        else:
            self.stdout.write('  Администратор уже существует')



