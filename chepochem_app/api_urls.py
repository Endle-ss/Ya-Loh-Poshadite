from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views, server_logic_api

# Обычные API роуты
router = DefaultRouter()
router.register(r'categories', api_views.CategoryViewSet)
router.register(r'users', api_views.UserViewSet)
router.register(r'favorites', api_views.UserFavoriteViewSet)
router.register(r'notifications', api_views.NotificationViewSet)

# Серверная логика API роуты
server_router = DefaultRouter()
server_router.register(r'listings', server_logic_api.ServerLogicListingViewSet)
server_router.register(r'reviews', server_logic_api.ServerLogicReviewViewSet)

urlpatterns = [
    # Обычные API роуты
    path('', include(router.urls)),
    
    # Серверная логика API
    path('server/', include(server_router.urls)),
    path('server/moderation/', server_logic_api.ServerLogicModerationAPIView.as_view(), name='server-moderation'),
    path('server/search/', server_logic_api.ServerLogicSearchAPIView.as_view(), name='server-search'),
    
    # Дополнительные endpoints
    path('search-suggestions/', api_views.SearchSuggestionsAPIView.as_view(), name='api-search-suggestions'),
    path('statistics/', api_views.StatisticsAPIView.as_view(), name='api-statistics'),
    path('analytics/', api_views.AnalyticsAPIView.as_view(), name='api-analytics'),
    path('export/', api_views.ExportAPIView.as_view(), name='api-export'),
    path('import/', api_views.ImportAPIView.as_view(), name='api-import'),
]
