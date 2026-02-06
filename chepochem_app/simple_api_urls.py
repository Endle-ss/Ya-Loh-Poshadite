from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import server_logic_api

# Серверная логика API роуты
server_router = DefaultRouter()
server_router.register(r'listings', server_logic_api.ServerLogicListingViewSet)
server_router.register(r'reviews', server_logic_api.ServerLogicReviewViewSet)
server_router.register(r'moderation', server_logic_api.ServerLogicModerationViewSet)
server_router.register(r'search', server_logic_api.ServerLogicSearchViewSet)

urlpatterns = [
    # Серверная логика API
    path('server/', include(server_router.urls)),
]
