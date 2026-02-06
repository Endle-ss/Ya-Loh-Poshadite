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
from django.db import transaction

from .models import (
    Role, UserProfile, UserReputation, Category, Listing, 
    ListingImage, Review, UserFavorite, Report, 
    ListingModeration, Notification, UserStatistics
)
from .serializers import (
    ListingSerializer, ReviewSerializer, UserSerializer,
    ListingCreateSerializer, ReviewCreateSerializer
)
from .django_orm_services import (
    ListingTransactionService, ReviewTransactionService, 
    ModerationTransactionService, DataValidator, SearchService,
    UserActivityLogger
)
from .django_rbac_security import require_permission, require_role

User = get_user_model()


class ServerLogicListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ListingCreateSerializer
        return ListingSerializer
    
    def get_queryset(self):
        queryset = Listing.objects.select_related('user', 'category').prefetch_related('listingimage_set')
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.filter(status='active')
        
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        search_query = self.request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(location__icontains=search_query)
            )
        
        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        sort_by = self.request.query_params.get('sort', 'newest')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-views_count')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Создание объявления с транзакциями и валидацией
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        listing_data = serializer.validated_data
        
        # Серверная валидация данных
        validation_errors = DataValidator.validate_listing_data({
            'title': listing_data.get('title'),
            'description': listing_data.get('description'),
            'price': listing_data.get('price'),
            'category_id': listing_data.get('category').id,
            'location': listing_data.get('location')
        })
        
        if validation_errors:
            return Response({'errors': validation_errors}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Создание через транзакционный сервис с откатом при ошибке
            images_data = []
            for image_data in listing_data.get('images', []):
                images_data.append({
                    'image_url': str(image_data.get('image')),
                    'alt_text': image_data.get('alt_text', ''),
                    'sort_order': image_data.get('sort_order', 0),
                    'is_primary': image_data.get('is_primary', False)
                })
            
            listing_id = ListingTransactionService.create_listing_with_images(
                request.user.id, 
                {
                    'title': listing_data['title'],
                    'description': listing_data['description'],
                    'price': listing_data['price'],
                    'category_id': listing_data['category'].id,
                    'location': listing_data['location'],
                    'latitude': listing_data.get('latitude'),
                    'longitude': listing_data.get('longitude'),
                    'is_negotiable': listing_data.get('is_negotiable', True),
                    'is_urgent': listing_data.get('is_urgent', False)
                },
                images_data
            )
            
            listing = Listing.objects.get(id=listing_id)
            response_serializer = ListingSerializer(listing, context={'request': request})
            
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Ошибка создания объявления'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Обновление объявления с проверкой прав и валидацией
        listing = self.get_object()
        
        # Проверка прав доступа (RBAC)
        if listing.user != request.user and not request.user.role.name in ['moderator', 'admin']:
            return Response({'error': 'Нет прав на редактирование'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(listing, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Серверная валидация данных
        update_data = serializer.validated_data
        validation_errors = DataValidator.validate_listing_data({
            'title': update_data.get('title', listing.title),
            'description': update_data.get('description', listing.description),
            'price': update_data.get('price', listing.price),
            'category_id': update_data.get('category', listing.category).id,
            'location': update_data.get('location', listing.location)
        })
        
        if validation_errors:
            return Response({'errors': validation_errors}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Обновление через транзакционный сервис с откатом при ошибке
            success = ListingTransactionService.update_listing_with_rollback(
                listing.id,
                request.user.id,
                {
                    'title': update_data.get('title'),
                    'description': update_data.get('description'),
                    'price': update_data.get('price'),
                    'location': update_data.get('location'),
                    'is_negotiable': update_data.get('is_negotiable'),
                    'is_urgent': update_data.get('is_urgent')
                }
            )
            
            if success:
                listing.refresh_from_db()
                response_serializer = ListingSerializer(listing, context={'request': request})
                return Response(response_serializer.data)
            else:
                return Response({'error': 'Не удалось обновить объявление'}, status=status.HTTP_400_BAD_REQUEST)
                
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Ошибка обновления объявления'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        # Удаление объявления с проверкой прав и транзакциями
        listing = self.get_object()
        
        try:
            # Удаление через транзакционный сервис с откатом при ошибке
            success = ListingTransactionService.delete_listing_with_rollback(
                listing.id,
                request.user.id
            )
            
            if success:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'error': 'Не удалось удалить объявление'}, status=status.HTTP_400_BAD_REQUEST)
                
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Ошибка удаления объявления'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        # Добавление/удаление из избранного с логированием
        listing = self.get_object()
        
        try:
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
            
            # Логирование действия пользователя
            UserActivityLogger.log_activity(
                user_id=request.user.id,
                action='toggle_favorite',
                entity_type='listing',
                entity_id=listing.id,
                details={'is_favorited': is_favorited},
                request=request
            )
            
            return Response({
                'is_favorited': is_favorited,
                'favorites_count': listing.favorites_count
            })
            
        except Exception as e:
            return Response({'error': 'Ошибка изменения избранного'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        # Увеличение счетчика просмотров с логированием
        listing = self.get_object()
        
        if request.user != listing.user:
            listing.views_count += 1
            listing.save()
            
            # Логирование просмотра объявления
            UserActivityLogger.log_activity(
                user_id=request.user.id if request.user.is_authenticated else None,
                action='view_listing',
                entity_type='listing',
                entity_id=listing.id,
                request=request
            )
        
        return Response({'views_count': listing.views_count})


class ServerLogicReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def get_queryset(self):
        queryset = Review.objects.select_related('reviewer', 'reviewed_user')
        
        reviewed_user = self.request.query_params.get('reviewed_user')
        if reviewed_user:
            queryset = queryset.filter(reviewed_user_id=reviewed_user)
        
        reviewer = self.request.query_params.get('reviewer')
        if reviewer:
            queryset = queryset.filter(reviewer_id=reviewer)
        
        return queryset.order_by('-created_at')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Создание отзыва с серверной валидацией и транзакциями
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # Серверная валидация данных отзыва
        validation_errors = DataValidator.validate_review_data({
            'rating': validated_data.get('rating'),
            'comment': validated_data.get('comment')
        })
        
        if validation_errors:
            return Response({'errors': validation_errors}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Создание через транзакционный сервис с обновлением репутации
            review_id = ReviewTransactionService.create_review_with_reputation_update(
                request.user.id,
                validated_data['reviewed_user'].id,
                validated_data['rating'],
                validated_data['comment']
            )
            
            review = Review.objects.get(id=review_id)
            response_serializer = ReviewSerializer(review)
            
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Ошибка создания отзыва'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Обновление отзыва с проверкой прав и валидацией
        review = self.get_object()
        
        if review.reviewer != request.user:
            return Response({'error': 'Нет прав на редактирование отзыва'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(review, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Серверная валидация данных отзыва
        validated_data = serializer.validated_data
        validation_errors = DataValidator.validate_review_data({
            'rating': validated_data.get('rating', review.rating),
            'comment': validated_data.get('comment', review.comment)
        })
        
        if validation_errors:
            return Response({'errors': validation_errors}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer.save()
            
            # Логирование обновления отзыва
            UserActivityLogger.log_activity(
                user_id=request.user.id,
                action='update_review',
                entity_type='review',
                entity_id=review.id,
                request=request
            )
            
            return Response(serializer.data)
            
        except Exception as e:
            return Response({'error': 'Ошибка обновления отзыва'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        # Удаление отзыва с проверкой прав (RBAC)
        review = self.get_object()
        
        if review.reviewer != request.user and not request.user.role.name in ['moderator', 'admin']:
            return Response({'error': 'Нет прав на удаление отзыва'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Логирование удаления отзыва
            UserActivityLogger.log_activity(
                user_id=request.user.id,
                action='delete_review',
                entity_type='review',
                entity_id=review.id,
                request=request
            )
            
            review.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response({'error': 'Ошибка удаления отзыва'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServerLogicModerationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Listing.objects.filter(status='pending')
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Получение объявлений на модерации (только для модераторов и админов)
        if not self.request.user.role.name in ['moderator', 'admin']:
            return Listing.objects.none()
        return Listing.objects.filter(status='pending').order_by('created_at')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        # Одобрение объявления
        listing = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            success = ModerationTransactionService.moderate_listing_with_notification(
                listing.id,
                request.user.id,
                'approve',
                reason
            )
            
            if success:
                return Response({'status': 'Объявление одобрено'})
            else:
                return Response({'error': 'Не удалось одобрить объявление'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': 'Ошибка одобрения'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        # Отклонение объявления
        listing = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            success = ModerationTransactionService.moderate_listing_with_notification(
                listing.id,
                request.user.id,
                'reject',
                reason
            )
            
            if success:
                return Response({'status': 'Объявление отклонено'})
            else:
                return Response({'error': 'Не удалось отклонить объявление'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': 'Ошибка отклонения'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServerLogicSearchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Listing.objects.filter(status='active')
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Поиск объявлений с серверной валидацией параметров
        queryset = Listing.objects.filter(status='active')
        
        query = self.request.query_params.get('query', '').strip()
        category_id = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        location = self.request.query_params.get('location', '').strip()
        sort_by = self.request.query_params.get('sort_by', 'newest')
        
        # Фильтрация по запросу
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query) |
                Q(location__icontains=query)
            )
        
        # Фильтрация по категории
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Фильтрация по цене
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Фильтрация по местоположению
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        # Сортировка
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
    
    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        # Поисковые подсказки
        query = request.query_params.get('query', '').strip()
        if len(query) < 2:
            return Response({'suggestions': []})
        
        # Поиск похожих заголовков
        suggestions = Listing.objects.filter(
            title__icontains=query,
            status='active'
        ).values_list('title', flat=True).distinct()[:5]
        
        return Response({'suggestions': list(suggestions)})
