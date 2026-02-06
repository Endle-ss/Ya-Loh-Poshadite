from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    Role, UserProfile, UserReputation, Category, Listing, 
    ListingImage, Review, UserFavorite, Report, 
    ListingModeration, Notification, UserStatistics
)
from .serializers import (
    RoleSerializer, UserSerializer, UserProfileSerializer, 
    UserReputationSerializer, UserStatisticsSerializer, CategorySerializer,
    ListingSerializer, ListingImageSerializer, ReviewSerializer, 
    UserFavoriteSerializer, ReportSerializer, ListingModerationSerializer, 
    NotificationSerializer
)

User = get_user_model()


class RoleViewSet(viewsets.ModelViewSet):
    """API для ролей"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """API для пользователей (только чтение)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.select_related('role', 'profile', 'reputation', 'statistics')
        
        # Фильтрация по роли
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role__name=role)
        
        # Фильтрация по статусу
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-created_at')


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для категорий (только чтение)"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset.order_by('sort_order', 'name')


class ListingImageViewSet(viewsets.ModelViewSet):
    """API для изображений объявлений"""
    queryset = ListingImage.objects.all()
    serializer_class = ListingImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = ListingImage.objects.select_related('listing')
        
        # Фильтрация по объявлению
        listing_id = self.request.query_params.get('listing')
        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)
        
        return queryset.order_by('sort_order', 'created_at')


class UserFavoriteViewSet(viewsets.ModelViewSet):
    """API для избранных объявлений"""
    queryset = UserFavorite.objects.all()
    serializer_class = UserFavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserFavorite.objects.filter(user=self.request.user).select_related('listing')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReportViewSet(viewsets.ModelViewSet):
    """API для жалоб"""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Report.objects.select_related('reporter', 'reported_user', 'moderator')
        
        # Фильтрация по статусу
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Фильтрация по типу жалобы
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class ListingModerationViewSet(viewsets.ReadOnlyModelViewSet):
    """API для модерации объявлений (только чтение)"""
    queryset = ListingModeration.objects.all()
    serializer_class = ListingModerationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ListingModeration.objects.select_related('listing', 'moderator')
        
        # Фильтрация по действию
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        return queryset.order_by('-created_at')


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API для уведомлений (только чтение)"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Отметить уведомление как прочитанное"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Отметить все уведомления как прочитанные"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read'})


class UserProfileViewSet(viewsets.ModelViewSet):
    """API для профилей пользователей"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserProfile.objects.select_related('user')


class UserReputationViewSet(viewsets.ReadOnlyModelViewSet):
    """API для репутации пользователей (только чтение)"""
    queryset = UserReputation.objects.all()
    serializer_class = UserReputationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserReputation.objects.select_related('user').order_by('-reputation_level', '-total_score')


class UserStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    """API для статистики пользователей (только чтение)"""
    queryset = UserStatistics.objects.all()
    serializer_class = UserStatisticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserStatistics.objects.select_related('user').order_by('-listings_count', '-total_earnings')


class SearchSuggestionsAPIView(APIView):
    """API для поисковых подсказок"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        query = request.query_params.get('query', '').strip()
        if len(query) < 2:
            return Response({'suggestions': []})
        
        # Поиск похожих заголовков объявлений
        suggestions = Listing.objects.filter(
            title__icontains=query,
            status='active'
        ).values_list('title', flat=True).distinct()[:10]
        
        return Response({'suggestions': list(suggestions)})


class StatisticsAPIView(APIView):
    """API для статистики системы"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Общая статистика
        total_users = User.objects.count()
        total_listings = Listing.objects.count()
        active_listings = Listing.objects.filter(status='active').count()
        total_reviews = Review.objects.count()
        
        # Статистика по ролям
        users_by_role = {}
        for role in Role.objects.all():
            users_by_role[role.name] = User.objects.filter(role=role).count()
        
        # Статистика по категориям
        listings_by_category = {}
        for category in Category.objects.filter(is_active=True):
            listings_by_category[category.name] = Listing.objects.filter(category=category).count()
        
        return Response({
            'total_users': total_users,
            'total_listings': total_listings,
            'active_listings': active_listings,
            'total_reviews': total_reviews,
            'users_by_role': users_by_role,
            'listings_by_category': listings_by_category
        })


