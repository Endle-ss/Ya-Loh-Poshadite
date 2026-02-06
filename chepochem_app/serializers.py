from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Role, UserProfile, UserReputation, Category, Listing, 
    ListingImage, Review, UserFavorite, Report, 
    ListingModeration, Notification, UserStatistics
)

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['bio', 'location', 'birth_date', 'gender', 'website', 'created_at', 'updated_at']


class UserReputationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserReputation
        fields = ['total_score', 'positive_reviews', 'negative_reviews', 
                 'neutral_reviews', 'reputation_level', 'created_at', 'updated_at']


class UserStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStatistics
        fields = ['listings_count', 'sold_count', 'purchased_count', 
                 'total_earnings', 'total_spent', 'response_rate', 
                 'average_response_time', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    reputation = UserReputationSerializer(read_only=True)
    statistics = UserStatisticsSerializer(read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'phone', 'avatar', 'is_verified', 'is_active', 'role_name',
                 'created_at', 'updated_at', 'last_login', 'profile', 
                 'reputation', 'statistics']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'parent', 
                 'is_active', 'sort_order', 'created_at']


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'thumbnail', 'alt_text', 'sort_order', 
                 'is_primary', 'created_at']


class ListingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Listing
        fields = ['id', 'user', 'user_username', 'category', 'category_name', 
                 'title', 'description', 'price', 'currency', 'condition', 
                 'status', 'location', 'latitude', 'longitude', 'is_negotiable', 
                 'is_urgent', 'views_count', 'favorites_count', 'created_at', 
                 'updated_at', 'published_at', 'expires_at', 'images', 'is_favorited']
        read_only_fields = ['id', 'user', 'views_count', 'favorites_count', 
                           'created_at', 'updated_at', 'published_at']
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserFavorite.objects.filter(user=request.user, listing=obj).exists()
        return False


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = UserSerializer(read_only=True)
    reviewed_user = UserSerializer(read_only=True)
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True)
    reviewed_user_username = serializers.CharField(source='reviewed_user.username', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'reviewer', 'reviewer_username', 'reviewed_user', 
                 'reviewed_user_username', 'rating', 'comment', 'is_positive', 
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'reviewer', 'is_positive', 'created_at', 'updated_at']


class UserFavoriteSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    
    class Meta:
        model = UserFavorite
        fields = ['id', 'listing', 'created_at']
        read_only_fields = ['id', 'created_at']


class ReportSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    reported_user = UserSerializer(read_only=True)
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    reported_user_username = serializers.CharField(source='reported_user.username', read_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'reporter', 'reporter_username', 'reported_user', 
                 'reported_user_username', 'reported_listing', 'report_type', 
                 'description', 'status', 'moderator', 'resolution', 
                 'created_at', 'resolved_at']
        read_only_fields = ['id', 'reporter', 'status', 'moderator', 
                           'resolution', 'created_at', 'resolved_at']


class ListingModerationSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    moderator = UserSerializer(read_only=True)
    moderator_username = serializers.CharField(source='moderator.username', read_only=True)
    
    class Meta:
        model = ListingModeration
        fields = ['id', 'listing', 'moderator', 'moderator_username', 
                 'action', 'reason', 'created_at']
        read_only_fields = ['id', 'moderator', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'content', 'is_read', 
                 'related_entity_type', 'related_entity_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class ListingCreateSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, required=False)
    
    class Meta:
        model = Listing
        fields = ['category', 'title', 'description', 'price', 'currency', 
                 'condition', 'location', 'latitude', 'longitude', 
                 'is_negotiable', 'is_urgent', 'images']
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        listing = Listing.objects.create(**validated_data)
        
        for image_data in images_data:
            ListingImage.objects.create(listing=listing, **image_data)
        
        return listing


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['reviewed_user', 'rating', 'comment']
    
    def validate(self, data):
        if data['rating'] < 1 or data['rating'] > 5:
            raise serializers.ValidationError("Рейтинг должен быть от 1 до 5")
        
        request = self.context.get('request')
        if request and request.user == data['reviewed_user']:
            raise serializers.ValidationError("Нельзя оставить отзыв самому себе")
        
        if Review.objects.filter(reviewer=request.user, reviewed_user=data['reviewed_user']).exists():
            raise serializers.ValidationError("Отзыв уже существует")
        
        return data


class SearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=255, required=False)
    category = serializers.IntegerField(required=False)
    min_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    max_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    location = serializers.CharField(max_length=255, required=False)
    sort_by = serializers.ChoiceField(
        choices=['newest', 'oldest', 'price_low', 'price_high', 'popular'],
        default='newest'
    )
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)
