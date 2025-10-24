from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import (
    User, UserProfile, Listing, ListingImage, Review, Report, Category
)

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя (упрощенная для демонстрации)"""
    email = forms.EmailField(required=True, label="Электронная почта")
    first_name = forms.CharField(max_length=100, required=True, label="Имя")
    last_name = forms.CharField(max_length=100, required=True, label="Фамилия")
    phone = forms.CharField(max_length=20, required=False, label="Телефон")

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убираем строгие валидаторы паролей для демонстрации
        self.fields['password1'].help_text = "Минимум 4 символа"
        self.fields['password2'].help_text = "Повторите пароль"
        # Убираем валидаторы паролей
        self.fields['password1'].validators = []
        self.fields['password2'].validators = []

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        # Только базовая проверка длины
        if len(password1) < 4:
            raise ValidationError('Пароль должен содержать минимум 4 символа')
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Форма редактирования профиля"""
    class Meta:
        model = UserProfile
        fields = ['bio', 'location', 'birth_date', 'gender', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


class ListingForm(forms.ModelForm):
    """Форма создания/редактирования объявления"""
    class Meta:
        model = Listing
        fields = [
            'category', 'title', 'description', 'price', 'currency', 
            'condition', 'location', 'latitude', 'longitude', 
            'is_negotiable', 'is_urgent'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'is_negotiable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_urgent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)


class ListingImageForm(forms.ModelForm):
    """Форма для изображений объявления"""
    class Meta:
        model = ListingImage
        fields = ['image', 'alt_text', 'sort_order', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


ListingImageFormSet = forms.inlineformset_factory(
    Listing, ListingImage, form=ListingImageForm,
    extra=3, can_delete=True, max_num=10
)


class ReviewForm(forms.ModelForm):
    """Форма создания отзыва"""
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].widget = forms.Select(
            choices=[(i, f'{i} звезд') for i in range(1, 6)],
            attrs={'class': 'form-control'}
        )


class ReportForm(forms.ModelForm):
    """Форма создания жалобы"""
    class Meta:
        model = Report
        fields = ['reported_user', 'reported_listing', 'report_type', 'description']
        widgets = {
            'reported_user': forms.Select(attrs={'class': 'form-control'}),
            'reported_listing': forms.Select(attrs={'class': 'form-control'}),
            'report_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reported_user'].queryset = User.objects.filter(is_active=True)
        self.fields['reported_listing'].queryset = Listing.objects.filter(status='active')
        self.fields['reported_user'].required = False
        self.fields['reported_listing'].required = False

    def clean(self):
        cleaned_data = super().clean()
        reported_user = cleaned_data.get('reported_user')
        reported_listing = cleaned_data.get('reported_listing')
        
        if not reported_user and not reported_listing:
            raise forms.ValidationError('Необходимо указать либо пользователя, либо объявление для жалобы.')
        
        return cleaned_data
