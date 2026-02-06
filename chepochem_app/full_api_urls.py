from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import server_logic_api, complete_api_views

# Полный API роутер со всеми сущностями
full_router = DefaultRouter()

# Основные сущности
full_router.register(r'roles', complete_api_views.RoleViewSet)
full_router.register(r'users', complete_api_views.UserViewSet)
full_router.register(r'categories', complete_api_views.CategoryViewSet)

# Серверная логика (CRUD с транзакциями)
full_router.register(r'listings', server_logic_api.ServerLogicListingViewSet)
full_router.register(r'reviews', server_logic_api.ServerLogicReviewViewSet)
full_router.register(r'moderation', server_logic_api.ServerLogicModerationViewSet)
full_router.register(r'search', server_logic_api.ServerLogicSearchViewSet)

# Дополнительные сущности
full_router.register(r'images', complete_api_views.ListingImageViewSet)
full_router.register(r'favorites', complete_api_views.UserFavoriteViewSet)
full_router.register(r'notifications', complete_api_views.NotificationViewSet)
full_router.register(r'reports', complete_api_views.ReportViewSet)
full_router.register(r'profiles', complete_api_views.UserProfileViewSet)
full_router.register(r'reputations', complete_api_views.UserReputationViewSet)
full_router.register(r'statistics', complete_api_views.UserStatisticsViewSet)

urlpatterns = [
    # Полный API со всеми сущностями
    path('', include(full_router.urls)),
    
    # Дополнительные endpoints
    path('search-suggestions/', complete_api_views.SearchSuggestionsAPIView.as_view(), name='search-suggestions'),
    path('system-statistics/', complete_api_views.StatisticsAPIView.as_view(), name='system-statistics'),
]
