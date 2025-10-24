from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),
    
    # Аутентификация
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Объявления
    path('listing/<int:listing_id>/', views.listing_detail, name='listing_detail'),
    path('create-listing/', views.create_listing, name='create_listing'),
    path('edit-listing/<int:listing_id>/', views.edit_listing, name='edit_listing'),
    path('toggle-favorite/<int:listing_id>/', views.toggle_favorite, name='toggle_favorite'),
    
    # Профили пользователей
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('favorites/', views.favorites, name='favorites'),
    
    # Отзывы
    path('create-review/<str:username>/', views.create_review, name='create_review'),
    
    # Жалобы
    path('create-report/', views.create_report, name='create_report'),
    
    # Модерация
    path('moderation/', views.moderation_dashboard, name='moderation_dashboard'),
    path('moderate-listing/<int:listing_id>/', views.moderate_listing, name='moderate_listing'),
    
    # Уведомления
    path('notifications/', views.notifications, name='notifications'),
]
