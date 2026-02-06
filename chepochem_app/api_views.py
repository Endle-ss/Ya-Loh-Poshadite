from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    Role, UserProfile, UserReputation, Category, Listing, 
    ListingImage, Review, UserFavorite, Report, 
    ListingModeration, Notification, UserStatistics
)
from .serializers import (
    RoleSerializer, UserSerializer, UserProfileSerializer, 
    UserReputationSerializer, UserStatisticsSerializer, CategorySerializer,
    ListingSerializer, ListingCreateSerializer, ListingImageSerializer,
    ReviewSerializer, ReviewCreateSerializer, UserFavoriteSerializer,
    ReportSerializer, ListingModerationSerializer, NotificationSerializer,
    SearchSerializer
)
from .django_orm_services import (
    ListingTransactionService, ReviewTransactionService, 
    ModerationTransactionService, DataValidator, SearchService
)
from .django_rbac_security import require_permission, require_role

User = get_user_model()


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset.order_by('sort_order', 'name')


class ListingViewSet(viewsets.ModelViewSet):
    """API для объявлений"""
    queryset = Listing.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return ListingCreateSerializer
        return ListingSerializer
    
    def get_queryset(self):
        """Получение объявлений с фильтрацией"""
        queryset = Listing.objects.select_related('user', 'category').prefetch_related('listingimage_set')
        
        # Фильтрация по статусу
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            # По умолчанию показываем только активные
            queryset = queryset.filter(status='active')
        
        # Фильтрация по категории
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Фильтрация по пользователю
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Поиск
        search_query = self.request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(location__icontains=search_query)
            )
        
        # Фильтрация по цене
        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Сортировка
        sort_by = self.request.query_params.get('sort', 'newest')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-views_count')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        else:  # newest
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def perform_create(self, serializer):
        """Создание объявления с привязкой к пользователю"""
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Обновление объявления с проверкой прав"""
        listing = self.get_object()
        if listing.user != self.request.user and not self.request.user.role.name in ['moderator', 'admin']:
            raise ValidationError("Нет прав на редактирование объявления")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Удаление объявления с проверкой прав"""
        if instance.user != self.request.user and not self.request.user.role.name in ['moderator', 'admin']:
            raise ValidationError("Нет прав на удаление объявления")
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Добавление/удаление из избранного"""
        listing = self.get_object()
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
        
        return Response({
            'is_favorited': is_favorited,
            'favorites_count': listing.favorites_count
        })
    
    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """Увеличение счетчика просмотров"""
        listing = self.get_object()
        if request.user != listing.user:
            listing.views_count += 1
            listing.save()
        return Response({'views_count': listing.views_count})


class ReviewViewSet(viewsets.ModelViewSet):
    """API для отзывов"""
    queryset = Review.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def get_queryset(self):
        """Получение отзывов с фильтрацией"""
        queryset = Review.objects.select_related('reviewer', 'reviewed_user')
        
        # Фильтрация по пользователю, о котором отзыв
        reviewed_user = self.request.query_params.get('reviewed_user')
        if reviewed_user:
            queryset = queryset.filter(reviewed_user_id=reviewed_user)
        
        # Фильтрация по автору отзыва
        reviewer = self.request.query_params.get('reviewer')
        if reviewer:
            queryset = queryset.filter(reviewer_id=reviewer)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """Создание отзыва с привязкой к автору"""
        serializer.save(reviewer=self.request.user)
    
    def perform_update(self, serializer):
        """Обновление отзыва с проверкой прав"""
        review = self.get_object()
        if review.reviewer != self.request.user:
            raise ValidationError("Нет прав на редактирование отзыва")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Удаление отзыва с проверкой прав"""
        if instance.reviewer != self.request.user and not self.request.user.role.name in ['moderator', 'admin']:
            raise ValidationError("Нет прав на удаление отзыва")
        instance.delete()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """API для пользователей (только чтение)"""
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Получение пользователей с фильтрацией"""
        queryset = User.objects.select_related('role').prefetch_related(
            'userprofile', 'userreputation', 'userstatistics'
        )
        
        # Фильтрация по роли
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role__name=role)
        
        return queryset.order_by('-date_joined')
    
    @action(detail=True, methods=['get'])
    def listings(self, request, pk=None):
        """Получение объявлений пользователя"""
        user = self.get_object()
        listings = Listing.objects.filter(user=user, status='active')
        
        # Пагинация
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        paginator = Paginator(listings, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = ListingSerializer(page_obj, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'next': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous': page_obj.previous_page_number() if page_obj.has_previous() else None
        })
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Получение отзывов о пользователе"""
        user = self.get_object()
        reviews = Review.objects.filter(reviewed_user=user)
        
        # Пагинация
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        paginator = Paginator(reviews, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = ReviewSerializer(page_obj, many=True)
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'next': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous': page_obj.previous_page_number() if page_obj.has_previous() else None
        })


class UserFavoriteViewSet(viewsets.ModelViewSet):
    """API для избранных объявлений"""
    queryset = UserFavorite.objects.all()
    serializer_class = UserFavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Получение избранных объявлений текущего пользователя"""
        return UserFavorite.objects.filter(user=self.request.user).select_related('listing')
    
    def perform_create(self, serializer):
        """Создание записи избранного с привязкой к пользователю"""
        serializer.save(user=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API для уведомлений (только чтение)"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Получение уведомлений текущего пользователя"""
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


class ModerationViewSet(viewsets.ModelViewSet):
    """API для модерации (только для модераторов и админов)"""
    queryset = Listing.objects.filter(status='pending')
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Получение объявлений на модерации"""
        if not self.request.user.role.name in ['moderator', 'admin']:
            return Listing.objects.none()
        return super().get_queryset()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Одобрение объявления"""
        listing = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            success = ModerationTransactionService.moderate_listing_with_notification(
                listing.id, request.user.id, 'approve', reason
            )
            
            if success:
                return Response({'status': 'approved'})
            else:
                return Response({'error': 'Failed to approve'}, status=status.HTTP_400_BAD_REQUEST)
                
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Отклонение объявления"""
        listing = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            success = ModerationTransactionService.moderate_listing_with_notification(
                listing.id, request.user.id, 'reject', reason
            )
            
            if success:
                return Response({'status': 'rejected'})
            else:
                return Response({'error': 'Failed to reject'}, status=status.HTTP_400_BAD_REQUEST)
                
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SearchAPIView(APIView):
    """API для поиска объявлений"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Поиск объявлений"""
        serializer = SearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Использование сервиса поиска
        results = SearchService.search_listings(
            search_query=data.get('query'),
            category_id=data.get('category'),
            min_price=data.get('min_price'),
            max_price=data.get('max_price'),
            location=data.get('location'),
            sort_by=data.get('sort_by', 'newest'),
            limit=data.get('page_size', 20),
            offset=(data.get('page', 1) - 1) * data.get('page_size', 20)
        )
        
        # Сериализация результатов
        listings_serializer = ListingSerializer(
            results['listings'], 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'results': listings_serializer.data,
            'count': results['total_count'],
            'next': results['has_next'],
            'previous': results['has_previous']
        })


class SearchSuggestionsAPIView(APIView):
    """API для поисковых предложений"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Получение поисковых предложений"""
        query = request.query_params.get('q', '').strip()
        
        if len(query) < 2:
            return Response({'suggestions': []})
        
        # Поиск по заголовкам объявлений
        listings = Listing.objects.filter(
            title__icontains=query,
            status='active'
        ).values_list('title', flat=True)[:5]
        
        # Поиск по категориям
        categories = Category.objects.filter(
            name__icontains=query,
            is_active=True
        ).values_list('name', flat=True)[:3]
        
        # Поиск по местоположению
        locations = Listing.objects.filter(
            location__icontains=query,
            status='active'
        ).values_list('location', flat=True).distinct()[:3]
        
        suggestions = list(listings) + list(categories) + list(locations)
        
        return Response({'suggestions': suggestions[:10]})


class StatisticsAPIView(APIView):
    """API для статистики"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Получение статистики"""
        if not request.user.role.name in ['admin', 'moderator']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        # Общая статистика
        total_users = User.objects.filter(is_active=True).count()
        total_listings = Listing.objects.count()
        active_listings = Listing.objects.filter(status='active').count()
        pending_listings = Listing.objects.filter(status='pending').count()
        total_reviews = Review.objects.count()
        
        # Статистика за последние 30 дней
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        new_listings_30d = Listing.objects.filter(created_at__gte=thirty_days_ago).count()
        new_reviews_30d = Review.objects.filter(created_at__gte=thirty_days_ago).count()
        
        return Response({
            'total_users': total_users,
            'total_listings': total_listings,
            'active_listings': active_listings,
            'pending_listings': pending_listings,
            'total_reviews': total_reviews,
            'new_users_30d': new_users_30d,
            'new_listings_30d': new_listings_30d,
            'new_reviews_30d': new_reviews_30d
        })


class ExportAPIView(APIView):
    """API для экспорта данных в CSV"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Экспорт данных"""
        export_type = request.query_params.get('type', 'listings')
        
        from .import_export import CSVExporter
        
        if export_type == 'listings':
            queryset = Listing.objects.all()
            if not request.user.role.name in ['admin', 'moderator']:
                queryset = queryset.filter(user=request.user)
            return CSVExporter.export_listings(queryset)
        
        elif export_type == 'users':
            if not request.user.role.name in ['admin']:
                return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
            queryset = User.objects.all()
            return CSVExporter.export_users(queryset)
        
        elif export_type == 'reviews':
            queryset = Review.objects.all()
            if not request.user.role.name in ['admin', 'moderator']:
                queryset = queryset.filter(reviewer=request.user)
            return CSVExporter.export_reviews(queryset)
        
        return Response({'error': 'Invalid export type'}, status=status.HTTP_400_BAD_REQUEST)


class ImportAPIView(APIView):
    """API для импорта данных из CSV"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Импорт данных"""
        import_type = request.data.get('type', 'listings')
        csv_file = request.FILES.get('file')
        
        if not csv_file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        from .import_export import CSVImporter
        
        if import_type == 'listings':
            if not request.user.role.name in ['admin', 'moderator', 'user']:
                return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
            
            result = CSVImporter.import_listings(csv_file, request.user)
            return Response(result)
        
        return Response({'error': 'Invalid import type'}, status=status.HTTP_400_BAD_REQUEST)


class AnalyticsAPIView(APIView):
    """API для аналитики с данными для визуализации"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Получение данных для аналитики"""
        if not request.user.role.name in ['admin', 'moderator']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        from datetime import timedelta
        from django.db.models import Count, Sum, Avg, Min, Max
        from django.db.models.functions import TruncDate
        
        # Период для анализа (по умолчанию 30 дней)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # 1. График объявлений по дням
        listings_by_date = Listing.objects.filter(
            created_at__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id'),
            active=Count('id', filter=Q(status='active')),
            sold=Count('id', filter=Q(status='sold'))
        ).order_by('date')
        
        # 2. График объявлений по категориям
        listings_by_category = Category.objects.annotate(
            total=Count('listing'),
            active=Count('listing', filter=Q(listing__status='active')),
            avg_price=Avg('listing__price')
        ).values('name', 'total', 'active', 'avg_price')
        
        # 3. График пользователей по дням
        users_by_date = User.objects.filter(
            date_joined__gte=start_date
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # 4. Топ пользователей по объявлениям
        top_users = User.objects.annotate(
            listings_count=Count('listing')
        ).order_by('-listings_count')[:10].values(
            'username', 'listings_count'
        )
        
        # 5. Статистика по статусам объявлений
        status_stats = Listing.objects.values('status').annotate(
            count=Count('id')
        )
        
        # 6. Средняя цена по категориям
        category_prices = Category.objects.annotate(
            avg_price=Avg('listing__price'),
            min_price=Min('listing__price'),
            max_price=Max('listing__price')
        ).filter(avg_price__isnull=False).values('name', 'avg_price', 'min_price', 'max_price')
        
        return Response({
            'listings_by_date': list(listings_by_date),
            'listings_by_category': list(listings_by_category),
            'users_by_date': list(users_by_date),
            'top_users': list(top_users),
            'status_stats': list(status_stats),
            'category_prices': list(category_prices),
        })
