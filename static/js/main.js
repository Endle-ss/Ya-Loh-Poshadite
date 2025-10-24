// Основной JavaScript для ЧёПочём

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация всех компонентов
    initFavoriteButtons();
    initImageModals();
    initFormValidation();
    initTooltips();
    initNotifications();
});

// Функция для добавления/удаления из избранного
function initFavoriteButtons() {
    const favoriteButtons = document.querySelectorAll('.favorite-btn, #favorite-btn');
    
    favoriteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const listingId = this.dataset.listingId;
            const icon = this.querySelector('i');
            const text = this.querySelector('span') || this;
            
            // Показываем загрузку
            const originalContent = this.innerHTML;
            this.innerHTML = '<span class="loading"></span>';
            this.disabled = true;
            
            fetch(`/toggle-favorite/${listingId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.is_favorited) {
                    icon.classList.add('fas');
                    icon.classList.remove('far');
                    this.classList.add('btn-danger');
                    this.classList.remove('btn-outline-danger', 'btn-outline-light');
                    if (text.textContent) {
                        text.textContent = 'В избранном';
                    }
                } else {
                    icon.classList.add('far');
                    icon.classList.remove('fas');
                    this.classList.add('btn-outline-danger');
                    this.classList.remove('btn-danger');
                    if (text.textContent) {
                        text.textContent = 'Добавить в избранное';
                    }
                }
                
                // Обновляем счетчик избранных
                const favoritesCount = document.querySelector('.favorites-count');
                if (favoritesCount) {
                    favoritesCount.textContent = data.favorites_count;
                }
                
                showNotification(data.is_favorited ? 'Добавлено в избранное' : 'Удалено из избранного', 'success');
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Произошла ошибка', 'error');
            })
            .finally(() => {
                this.disabled = false;
            });
        });
    });
}

// Инициализация модальных окон для изображений
function initImageModals() {
    const imageElements = document.querySelectorAll('.listing-detail-image, .image-gallery img');
    
    imageElements.forEach(img => {
        img.addEventListener('click', function() {
            const modalId = this.dataset.bsTarget;
            if (modalId) {
                const modal = document.querySelector(modalId);
                if (modal) {
                    const modalInstance = new bootstrap.Modal(modal);
                    modalInstance.show();
                }
            }
        });
    });
}

// Валидация форм
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'Это поле обязательно для заполнения');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    // Валидация email
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            showFieldError(field, 'Введите корректный email адрес');
            isValid = false;
        }
    });
    
    // Валидация пароля
    const passwordFields = form.querySelectorAll('input[type="password"]');
    passwordFields.forEach(field => {
        if (field.value && field.value.length < 8) {
            showFieldError(field, 'Пароль должен содержать минимум 8 символов');
            isValid = false;
        }
    });
    
    return isValid;
}

function showFieldError(field, message) {
    clearFieldError(field);
    
    field.classList.add('is-invalid');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Инициализация tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Система уведомлений
function initNotifications() {
    // Автоматически скрываем уведомления через 5 секунд
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });
}

function showNotification(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
}

// Получение CSRF токена
function getCSRFToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
}

// Предварительный просмотр изображений
function initImagePreview() {
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.createElement('img');
                    preview.src = e.target.result;
                    preview.style.maxWidth = '200px';
                    preview.style.maxHeight = '200px';
                    preview.style.marginTop = '10px';
                    preview.style.borderRadius = '0.5rem';
                    preview.style.border = '1px solid #dee2e6';
                    
                    const container = input.closest('.mb-3');
                    const existingPreview = container.querySelector('.image-preview');
                    if (existingPreview) {
                        existingPreview.remove();
                    }
                    
                    preview.className = 'image-preview';
                    container.appendChild(preview);
                };
                reader.readAsDataURL(file);
            }
        });
    });
}

// Поиск с автодополнением
function initSearchAutocomplete() {
    const searchInput = document.querySelector('input[name="search"]');
    if (!searchInput) return;
    
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            hideSearchSuggestions();
            return;
        }
        
        searchTimeout = setTimeout(() => {
            fetchSearchSuggestions(query);
        }, 300);
    });
    
    // Скрываем подсказки при клике вне поля поиска
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-container')) {
            hideSearchSuggestions();
        }
    });
}

function fetchSearchSuggestions(query) {
    fetch(`/api/search-suggestions/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            showSearchSuggestions(data.suggestions);
        })
        .catch(error => {
            console.error('Search suggestions error:', error);
        });
}

function showSearchSuggestions(suggestions) {
    hideSearchSuggestions();
    
    if (suggestions.length === 0) return;
    
    const searchContainer = document.querySelector('.search-container');
    if (!searchContainer) return;
    
    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'search-suggestions';
    suggestionsDiv.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #dee2e6;
        border-top: none;
        border-radius: 0 0 0.5rem 0.5rem;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        z-index: 1000;
        max-height: 300px;
        overflow-y: auto;
    `;
    
    suggestions.forEach(suggestion => {
        const item = document.createElement('div');
        item.className = 'search-suggestion-item';
        item.style.cssText = `
            padding: 0.75rem;
            cursor: pointer;
            border-bottom: 1px solid #f8f9fa;
        `;
        item.innerHTML = `
            <div class="fw-bold">${suggestion.title}</div>
            <small class="text-muted">${suggestion.category}</small>
        `;
        
        item.addEventListener('click', function() {
            window.location.href = `/listing/${suggestion.id}/`;
        });
        
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8f9fa';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
        });
        
        suggestionsDiv.appendChild(item);
    });
    
    searchContainer.style.position = 'relative';
    searchContainer.appendChild(suggestionsDiv);
}

function hideSearchSuggestions() {
    const suggestions = document.querySelector('.search-suggestions');
    if (suggestions) {
        suggestions.remove();
    }
}

// Ленивая загрузка изображений
function initLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// Копирование ссылки
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Ссылка скопирована в буфер обмена', 'success');
    }).catch(() => {
        showNotification('Не удалось скопировать ссылку', 'error');
    });
}

// Поделиться в социальных сетях
function shareOnSocial(platform, url, title) {
    const encodedUrl = encodeURIComponent(url);
    const encodedTitle = encodeURIComponent(title);
    
    const shareUrls = {
        'vk': `https://vk.com/share.php?url=${encodedUrl}&title=${encodedTitle}`,
        'telegram': `https://t.me/share/url?url=${encodedUrl}&text=${encodedTitle}`,
        'whatsapp': `https://wa.me/?text=${encodedTitle} ${encodedUrl}`,
        'facebook': `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
        'twitter': `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`
    };
    
    if (shareUrls[platform]) {
        window.open(shareUrls[platform], '_blank', 'width=600,height=400');
    }
}

// Инициализация всех функций при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initImagePreview();
    initSearchAutocomplete();
    initLazyLoading();
});
