from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    User, Role, Category, Listing, ListingImage, Review, UserFavorite, 
    Report, ListingModeration, Notification, UserReputation
)
from .forms import (
    UserRegistrationForm, ListingForm, ReviewForm, ReportForm,
    UserProfileForm, ListingImageFormSet
)
from .django_orm_services import (
    ListingTransactionService, ReviewTransactionService, 
    ModerationTransactionService, DataValidator, SearchService
)
from .django_rbac_security import (
    require_permission, require_role, DjangoRBACManager, 
    DjangoAuditLogger, DjangoPasswordSecurityManager
)


def register(request):
    """Простая регистрация пользователя"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        
        # Простая валидация
        if not username or not email or not password1 or not password2:
            messages.error(request, 'Все обязательные поля должны быть заполнены')
            return render(request, 'chepochem_app/register.html')
        
        if password1 != password2:
            messages.error(request, 'Пароли не совпадают')
            return render(request, 'chepochem_app/register.html')
        
        if len(password1) < 4:
            messages.error(request, 'Пароль должен содержать минимум 4 символа')
            return render(request, 'chepochem_app/register.html')
        
        # Проверяем, что пользователь не существует
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
            return render(request, 'chepochem_app/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return render(request, 'chepochem_app/register.html')
        
        try:
            # Получаем роль пользователя
            user_role = Role.objects.get(name='user')
            
            # Создаем пользователя
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=user_role,
                is_active=True
            )
            
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании пользователя: {str(e)}')
            return render(request, 'chepochem_app/register.html')
    
    return render(request, 'chepochem_app/register.html')


def custom_login(request):
    """Простой view для входа"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Введите имя пользователя и пароль')
            return render(request, 'chepochem_app/login.html')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'chepochem_app/login.html')


def custom_logout(request):
    """Простой view для выхода"""
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'До свидания, {username}!')
    else:
        messages.info(request, 'Вы не были авторизованы')
    
    return redirect('home')


def home(request):
    """Главная страница с объявлениями"""
    listings = Listing.objects.filter(status='active').select_related('user', 'category').prefetch_related('listingimage_set')
    
    # Фильтрация по категории
    category_id = request.GET.get('category')
    if category_id:
        listings = listings.filter(category_id=category_id)
    
    # Поиск
    search_query = request.GET.get('search')
    if search_query:
        listings = listings.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    # Сортировка
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        listings = listings.order_by('price')
    elif sort_by == 'price_high':
        listings = listings.order_by('-price')
    elif sort_by == 'popular':
        listings = listings.order_by('-views_count')
    else:
        listings = listings.order_by('-created_at')
    
    paginator = Paginator(listings, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.filter(is_active=True, parent=None)
    
    # Получаем список ID товаров, которые уже в избранном у текущего пользователя
    favorited_listing_ids = set()
    if request.user.is_authenticated:
        favorited_listing_ids = set(
            UserFavorite.objects.filter(user=request.user)
            .values_list('listing_id', flat=True)
        )
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'search_query': search_query,
        'sort_by': sort_by,
        'favorited_listing_ids': favorited_listing_ids,
    }
    return render(request, 'chepochem_app/home.html', context)


def listing_detail(request, listing_id):
    """Детальная страница объявления"""
    listing = get_object_or_404(Listing, id=listing_id)
    
    # Увеличиваем счетчик просмотров
    if request.user != listing.user:
        listing.views_count += 1
        listing.save()
    
    images = listing.listingimage_set.all()
    reviews = Review.objects.filter(reviewed_user=listing.user).order_by('-created_at')[:5]
    
    # Проверяем, добавлено ли в избранное
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = UserFavorite.objects.filter(
            user=request.user, 
            listing=listing
        ).exists()
    
    # Флаг: может ли текущий пользователь модерировать/удалять это объявление
    can_moderate = False
    if request.user.is_authenticated:
        user_role = DjangoRBACManager.get_user_role(request.user)
        # Модераторы и админы могут удалять любые объявления
        if user_role in ['moderator', 'admin']:
            can_moderate = True

    context = {
        'listing': listing,
        'images': images,
        'reviews': reviews,
        'is_favorited': is_favorited,
        'can_moderate': can_moderate,
    }
    return render(request, 'chepochem_app/listing_detail.html', context)


@login_required
def delete_listing(request, listing_id):
    """Удаление объявления.

    - Владелец может удалять своё объявление (delete_own_listing).
    - Модератор/админ может удалять любое объявление.
    """
    listing = get_object_or_404(Listing, id=listing_id)

    user_role = DjangoRBACManager.get_user_role(request.user)

    is_owner = listing.user_id == request.user.id
    is_moderator_or_admin = user_role in ['moderator', 'admin']

    if not (is_owner or is_moderator_or_admin):
        return HttpResponseForbidden("Недостаточно прав для удаления объявления")

    if request.method == 'POST':
        title = listing.title
        listing.delete()
        messages.success(request, f'Объявление "{title}" было удалено.')
        # Возвращаем на панель модерации, если модератор, иначе в профиль пользователя
        if is_moderator_or_admin:
            return redirect('moderation_dashboard')
        return redirect('user_profile', username=request.user.username)

    # Если кто-то открыл URL GET‑ом — просто редиректим без удаления
    return redirect('listing_detail', listing_id=listing_id)


@login_required
@require_permission('create_listing')
def create_listing(request):
    """Создание нового объявления с транзакциями"""
    if request.method == 'POST':
        form = ListingForm(request.POST)
        formset = ListingImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            # Валидация данных на сервере
            # Правильная обработка чекбоксов: если не отмечен, то False (для is_urgent) или True (для is_negotiable по умолчанию)
            is_negotiable = form.cleaned_data.get('is_negotiable', True)  # По умолчанию True в модели
            is_urgent = form.cleaned_data.get('is_urgent', False)  # По умолчанию False в модели
            
            listing_data = {
                'title': form.cleaned_data['title'],
                'description': form.cleaned_data['description'],
                'price': form.cleaned_data['price'],
                'category_id': form.cleaned_data['category'].id,
                'currency': form.cleaned_data.get('currency', 'RUB'),
                'condition': form.cleaned_data.get('condition', 'used'),
                'location': form.cleaned_data['location'],
                'is_negotiable': is_negotiable,
                'is_urgent': is_urgent
            }
            
            validation_errors = DataValidator.validate_listing_data(listing_data)
            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)
                return render(request, 'chepochem_app/create_listing.html', {
                    'form': form, 'formset': formset
                })
            
            # Подготовка данных изображений - передаем сам файл
            images_data = []
            for image_form in formset:
                if image_form.cleaned_data and image_form.cleaned_data.get('image'):
                    images_data.append({
                        'image': image_form.cleaned_data['image'],  # Передаем сам файл
                        'alt_text': image_form.cleaned_data.get('alt_text', ''),
                        'sort_order': image_form.cleaned_data.get('sort_order', 0),
                        'is_primary': image_form.cleaned_data.get('is_primary', False)
                    })
            
            try:
                # Создание объявления через транзакцию
                listing_id = ListingTransactionService.create_listing_with_images(
                    request.user.id, listing_data, images_data
                )
                
                messages.success(request, 'Объявление создано и отправлено на модерацию!')
                return redirect('listing_detail', listing_id=listing_id)
                
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка при создании объявления: {str(e)}\n{traceback.format_exc()}")
                messages.error(request, f'Произошла ошибка при создании объявления: {str(e)}')
        else:
            # Если форма невалидна, показываем ошибки
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
            if not formset.is_valid():
                for form in formset:
                    if form.errors:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f'Изображение {field}: {error}')
    else:
        form = ListingForm()
        formset = ListingImageFormSet()
    
    context = {
        'form': form,
        'formset': formset,
    }
    return render(request, 'chepochem_app/create_listing.html', context)


@login_required
def edit_listing(request, listing_id):
    """Редактирование объявления"""
    listing = get_object_or_404(Listing, id=listing_id, user=request.user)
    
    if request.method == 'POST':
        form = ListingForm(request.POST, instance=listing)
        formset = ListingImageFormSet(request.POST, request.FILES, instance=listing)
        
        if form.is_valid() and formset.is_valid():
            listing = form.save(commit=False)
            listing.status = 'pending'  # Снова отправляем на модерацию
            listing.save()
            
            formset.save()
            
            messages.success(request, 'Объявление обновлено и отправлено на модерацию!')
            return redirect('listing_detail', listing_id=listing.id)
    else:
        form = ListingForm(instance=listing)
        formset = ListingImageFormSet(instance=listing)
    
    context = {
        'form': form,
        'formset': formset,
        'listing': listing,
    }
    return render(request, 'chepochem_app/edit_listing.html', context)


@login_required
def user_profile(request, username):
    """Профиль пользователя"""
    user = get_object_or_404(User, username=username)
    profile = getattr(user, 'userprofile', None)
    reputation = getattr(user, 'userreputation', None)
    statistics = getattr(user, 'userstatistics', None)
    
    # Все объявления пользователя с разными статусами
    all_listings = Listing.objects.filter(user=user).order_by('-created_at')
    
    # Группировка по статусам
    listings_by_status = {
        'pending': all_listings.filter(status='pending'),
        'active': all_listings.filter(status='active'),
        'rejected': all_listings.filter(status='rejected'),
        'draft': all_listings.filter(status='draft'),
        'sold': all_listings.filter(status='sold'),
        'paused': all_listings.filter(status='paused'),
    }
    
    # Статистика по статусам
    status_stats = {
        'pending': listings_by_status['pending'].count(),
        'active': listings_by_status['active'].count(),
        'rejected': listings_by_status['rejected'].count(),
        'draft': listings_by_status['draft'].count(),
        'sold': listings_by_status['sold'].count(),
        'paused': listings_by_status['paused'].count(),
    }
    
    # Отзывы о пользователе
    reviews = Review.objects.filter(reviewed_user=user).order_by('-created_at')
    
    # Определяем, является ли это профилем текущего пользователя
    is_own_profile = request.user == user
    
    context = {
        'profile_user': user,
        'profile': profile,
        'reputation': reputation,
        'statistics': statistics,
        'all_listings': all_listings,
        'listings_by_status': listings_by_status,
        'status_stats': status_stats,
        'reviews': reviews,
        'is_own_profile': is_own_profile,
    }
    return render(request, 'chepochem_app/user_profile.html', context)


@login_required
def edit_profile(request):
    """Редактирование профиля"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлен!')
            return redirect('user_profile', username=request.user.username)
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
    }
    return render(request, 'chepochem_app/edit_profile.html', context)


@login_required
@require_POST
def toggle_favorite(request, listing_id):
    """Добавление/удаление из избранного"""
    try:
        listing = get_object_or_404(Listing, id=listing_id)
        favorite, created = UserFavorite.objects.get_or_create(
            user=request.user,
            listing=listing
        )
        
        if not created:
            favorite.delete()
            is_favorited = False
        else:
            is_favorited = True
        
        # Обновляем счетчик из БД (триггер может обновить автоматически, но перезагружаем для надежности)
        listing.refresh_from_db()
        
        return JsonResponse({
            'is_favorited': is_favorited,
            'favorites_count': listing.favorites_count,
            'success': True
        })
    except Exception as e:
        import logging
        logger = logging.getLogger('chepochem_app.errors')
        logger.error(f'Error in toggle_favorite: {str(e)}')
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)


@login_required
def favorites(request):
    """Страница избранных объявлений"""
    favorites = UserFavorite.objects.filter(
        user=request.user,
        listing__isnull=False  # Исключаем удаленные объявления
    ).select_related('listing', 'listing__user', 'listing__category').order_by('-created_at')
    
    paginator = Paginator(favorites, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'chepochem_app/favorites.html', context)


@login_required
def create_review(request, username):
    """Создание отзыва"""
    reviewed_user = get_object_or_404(User, username=username)
    
    # Проверяем, не оставлял ли уже отзыв
    if Review.objects.filter(reviewer=request.user, reviewed_user=reviewed_user).exists():
        messages.error(request, 'Вы уже оставили отзыв этому пользователю!')
        return redirect('user_profile', username=username)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.reviewer = request.user
            review.reviewed_user = reviewed_user
            review.save()
            
            messages.success(request, 'Отзыв добавлен!')
            return redirect('user_profile', username=username)
    else:
        form = ReviewForm()
    
    context = {
        'form': form,
        'reviewed_user': reviewed_user,
    }
    return render(request, 'chepochem_app/create_review.html', context)


@login_required
def create_report(request):
    """Создание жалобы"""
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.save()
            
            messages.success(request, 'Жалоба отправлена!')
            return redirect('home')
    else:
        form = ReportForm()
    
    context = {
        'form': form,
    }
    return render(request, 'chepochem_app/create_report.html', context)


# Модераторские функции
@login_required
@require_role('moderator', 'admin')
def moderation_dashboard(request):
    """Панель модератора"""
    
    # Получаем фильтр по статусу из GET параметров
    status_filter = request.GET.get('status', 'pending')
    
    # Все объявления с фильтрацией
    all_listings = Listing.objects.all()
    if status_filter and status_filter != 'all':
        all_listings = all_listings.filter(status=status_filter)
    
    # Объявления на модерации (для статистики)
    pending_listings = Listing.objects.filter(status='pending').order_by('created_at')
    
    # Статистика по статусам
    listings_stats = {
        'all': Listing.objects.count(),
        'pending': Listing.objects.filter(status='pending').count(),
        'active': Listing.objects.filter(status='active').count(),
        'rejected': Listing.objects.filter(status='rejected').count(),
        'draft': Listing.objects.filter(status='draft').count(),
        'sold': Listing.objects.filter(status='sold').count(),
    }
    
    # Жалобы
    pending_reports = Report.objects.filter(status='pending').order_by('created_at')
    
    # Статистика модерации за сегодня
    today = timezone.now().date()
    approved_today = ListingModeration.objects.filter(
        action='approve',
        created_at__date=today
    ).count()
    rejected_today = ListingModeration.objects.filter(
        action='reject',
        created_at__date=today
    ).count()
    
    context = {
        'pending_listings': pending_listings,
        'all_listings': all_listings.order_by('-created_at'),
        'listings_stats': listings_stats,
        'status_filter': status_filter,
        'pending_reports': pending_reports,
        'approved_today': approved_today,
        'rejected_today': rejected_today,
    }
    return render(request, 'chepochem_app/moderation_dashboard.html', context)


@login_required
@require_permission('moderate_listings', 'listing', 'listing_id')
def moderate_listing(request, listing_id):
    """Модерация объявления с транзакциями"""
    listing = get_object_or_404(Listing, id=listing_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')
        
        try:
            # Выполнение модерации через транзакцию
            success = ModerationTransactionService.moderate_listing_with_notification(
                listing_id, request.user.id, action, reason
            )
            
            if success:
                if action == 'approve':
                    messages.success(request, 'Объявление одобрено!')
                elif action == 'reject':
                    messages.success(request, 'Объявление отклонено!')
            else:
                messages.error(request, 'Не удалось выполнить модерацию')
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'Произошла ошибка при модерации')
        
        return redirect('moderation_dashboard')
    
    context = {
        'listing': listing,
    }
    return render(request, 'chepochem_app/moderate_listing.html', context)


@login_required
def notifications(request):
    """Уведомления пользователя"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Отмечаем все как прочитанные
    notifications.update(is_read=True)
    
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'chepochem_app/notifications.html', context)
