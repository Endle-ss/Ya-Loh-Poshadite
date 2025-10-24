from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Role, User, UserProfile, UserReputation, Category, Listing, 
    ListingImage, Review, UserFavorite, Report, ListingModeration, 
    Notification, UserStatistics
)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'


class UserReputationInline(admin.StackedInline):
    model = UserReputation
    can_delete = False
    verbose_name_plural = 'Репутация'


class UserStatisticsInline(admin.StackedInline):
    model = UserStatistics
    can_delete = False
    verbose_name_plural = 'Статистика'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, UserReputationInline, UserStatisticsInline)
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_verified']
    list_filter = ['role', 'is_active', 'is_verified', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone', 'avatar', 'is_verified', 'role')
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'sort_order']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    inlines = [ListingImageInline]
    list_display = ['title', 'user', 'category', 'price', 'status', 'created_at']
    list_filter = ['status', 'category', 'condition', 'is_urgent', 'created_at']
    search_fields = ['title', 'description', 'location']
    list_editable = ['status']
    date_hierarchy = 'created_at'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['reviewer', 'reviewed_user', 'rating', 'is_positive', 'created_at']
    list_filter = ['rating', 'is_positive', 'created_at']
    search_fields = ['reviewer__username', 'reviewed_user__username', 'comment']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['reporter', 'reported_user', 'report_type', 'status', 'created_at']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['reporter__username', 'reported_user__username', 'description']
    list_editable = ['status']


@admin.register(ListingModeration)
class ListingModerationAdmin(admin.ModelAdmin):
    list_display = ['listing', 'moderator', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['listing__title', 'moderator__username']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'content']
    list_editable = ['is_read']


@admin.register(UserStatistics)
class UserStatisticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'listings_count', 'sold_count', 'total_earnings', 'total_spent']
    search_fields = ['user__username']


@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'listing', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'listing__title']


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ['listing', 'is_primary', 'sort_order', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['listing__title']
