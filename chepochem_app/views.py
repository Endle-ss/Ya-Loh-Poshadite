from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    User, Category, Listing, ListingImage, Review, UserFavorite, 
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
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'search_query': search_query,
        'sort_by': sort_by,
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
    
    context = {
        'listing': listing,
        'images': images,
        'reviews': reviews,
        'is_favorited': is_favorited,
    }
    return render(request, 'chepochem_app/listing_detail.html', context)


@login_required
@require_permission('create_listing')
def create_listing(request):
    """Создание нового объявления с транзакциями"""
    if request.method == 'POST':
        form = ListingForm(request.POST)
        formset = ListingImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            # Валидация данных на сервере
            listing_data = {
                'title': form.cleaned_data['title'],
                'description': form.cleaned_data['description'],
                'price': form.cleaned_data['price'],
                'category_id': form.cleaned_data['category'].id,
                'location': form.cleaned_data['location'],
                'latitude': form.cleaned_data.get('latitude'),
                'longitude': form.cleaned_data.get('longitude'),
                'is_negotiable': form.cleaned_data.get('is_negotiable', True),
                'is_urgent': form.cleaned_data.get('is_urgent', False)
            }
            
            validation_errors = DataValidator.validate_listing_data(listing_data)
            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)
                return render(request, 'chepochem_app/create_listing.html', {
                    'form': form, 'formset': formset
                })
            
            # Подготовка данных изображений
            images_data = []
            for image_form in formset:
                if image_form.cleaned_data and image_form.cleaned_data.get('image'):
                    images_data.append({
                        'image_url': image_form.cleaned_data['image'].url,
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
                messages.error(request, 'Произошла ошибка при создании объявления')
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
    
    # Объявления пользователя
    listings = Listing.objects.filter(user=user, status='active').order_by('-created_at')
    
    # Отзывы о пользователе
    reviews = Review.objects.filter(reviewed_user=user).order_by('-created_at')
    
    context = {
        'profile_user': user,
        'profile': profile,
        'reputation': reputation,
        'statistics': statistics,
        'listings': listings,
        'reviews': reviews,
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
    listing = get_object_or_404(Listing, id=listing_id)
    favorite, created = UserFavorite.objects.get_or_create(
        user=request.user,
        listing=listing
    )
    
    if not created:
        favorite.delete()
        listing.favorites_count -= 1
        is_favorited = False
    else:
        listing.favorites_count += 1
        is_favorited = True
    
    listing.save()
    
    return JsonResponse({
        'is_favorited': is_favorited,
        'favorites_count': listing.favorites_count
    })


@login_required
def favorites(request):
    """Страница избранных объявлений"""
    favorites = UserFavorite.objects.filter(user=request.user).select_related('listing')
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
    
    # Объявления на модерации
    pending_listings = Listing.objects.filter(status='pending').order_by('created_at')
    
    # Жалобы
    pending_reports = Report.objects.filter(status='pending').order_by('created_at')
    
    context = {
        'pending_listings': pending_listings,
        'pending_reports': pending_reports,
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
