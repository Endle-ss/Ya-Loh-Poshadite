// Основной JavaScript для ЧёПочём

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация всех компонентов
    initFavoriteButtons();
    initImageModals();
    initFormValidation();
    initTooltips();
    initNotifications();
    initDropdownPositioning();
});

// Функция для добавления/удаления из избранного
function initFavoriteButtons() {
    const favoriteButtons = document.querySelectorAll('.favorite-btn, #favorite-btn');
    
    favoriteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            // Если кнопка находится внутри кликабельной карточки - не даём всплывать
            e.stopPropagation();
            
            const listingId = this.dataset.listingId;
            
            // Показываем загрузку
            const originalContent = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
            this.disabled = true;
            
            const csrfToken = getCSRFToken();
            if (!csrfToken) {
                showNotification('Ошибка безопасности. Пожалуйста, обновите страницу.', 'error');
                this.innerHTML = originalContent;
                this.disabled = false;
                return;
            }
            
            fetch(`/toggle-favorite/${listingId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        console.error('Favorite error response:', text);
                        throw new Error(`HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success === false) {
                    throw new Error(data.error || 'Неизвестная ошибка');
                }
                
                // Обновляем внешний вид кнопки
                if (data.is_favorited) {
                    // Полное красное сердце
                    this.innerHTML = this.id === 'favorite-btn'
                        ? '<i class="fas fa-heart me-1"></i><span>В избранном</span>'
                        : '<i class="fas fa-heart"></i>';
                    this.classList.add('btn-danger');
                    this.classList.remove('btn-outline-danger', 'btn-outline-light');
                    showNotification('Товар добавлен в избранное', 'success');
                } else {
                    // Пустое красное сердце по контуру
                    this.innerHTML = this.id === 'favorite-btn'
                        ? '<i class="far fa-heart me-1"></i><span>Добавить в избранное</span>'
                        : '<i class="far fa-heart"></i>';
                    this.classList.add('btn-outline-danger');
                    this.classList.remove('btn-danger');
                    showNotification('Товар удалён из избранного', 'info');
                }
                
                // Обновляем счётчик избранных рядом с подробной информацией
                const favoritesCount = document.querySelector('.favorites-count');
                if (favoritesCount && typeof data.favorites_count !== 'undefined') {
                    favoritesCount.textContent = data.favorites_count;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Произошла ошибка при работе с избранным: ' + error.message, 'error');
                this.innerHTML = originalContent;
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
    
    // Валидация обязательных полей
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'Это поле обязательно для заполнения');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    // Валидация имени пользователя
    const usernameFields = form.querySelectorAll('input[name="username"]');
    usernameFields.forEach(field => {
        if (field.value) {
            const username = field.value.trim();
            if (username.length < 3) {
                showFieldError(field, 'Имя пользователя должно содержать минимум 3 символа');
                isValid = false;
            } else if (username.length > 30) {
                showFieldError(field, 'Имя пользователя не должно превышать 30 символов');
                isValid = false;
            } else if (!/^[\w@.+-]+$/.test(username)) {
                showFieldError(field, 'Имя пользователя может содержать только буквы, цифры и символы @/./+/-/_');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    // Валидация email
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value) {
            if (!isValidEmail(field.value)) {
                showFieldError(field, 'Введите корректный email адрес');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    // Валидация пароля
    const passwordFields = form.querySelectorAll('input[type="password"]');
    passwordFields.forEach(field => {
        if (field.value) {
            if (field.value.length < 4) {
                showFieldError(field, 'Пароль должен содержать минимум 4 символа');
                isValid = false;
            } else if (field.value.length > 128) {
                showFieldError(field, 'Пароль не должен превышать 128 символов');
                isValid = false;
            } else if (field.value.toLowerCase() === 'password' || field.value.toLowerCase() === '1234') {
                showFieldError(field, 'Пароль слишком простой');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    // Валидация имени и фамилии
    const firstNameFields = form.querySelectorAll('input[name="first_name"]');
    firstNameFields.forEach(field => {
        if (field.value) {
            const firstName = field.value.trim();
            if (firstName.length < 2) {
                showFieldError(field, 'Имя должно содержать минимум 2 символа');
                isValid = false;
            } else if (/\d/.test(firstName)) {
                showFieldError(field, 'Имя не должно содержать цифры');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    const lastNameFields = form.querySelectorAll('input[name="last_name"]');
    lastNameFields.forEach(field => {
        if (field.value) {
            const lastName = field.value.trim();
            if (lastName.length < 2) {
                showFieldError(field, 'Фамилия должна содержать минимум 2 символа');
                isValid = false;
            } else if (/\d/.test(lastName)) {
                showFieldError(field, 'Фамилия не должна содержать цифры');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    // Валидация телефона
    const phoneFields = form.querySelectorAll('input[name="phone"], input[type="tel"]');
    phoneFields.forEach(field => {
        if (field.value) {
            const phone = field.value.replace(/\D/g, '');
            if (phone.length < 10) {
                showFieldError(field, 'Телефон должен содержать минимум 10 цифр');
                isValid = false;
            } else if (phone.length > 20) {
                showFieldError(field, 'Телефон не должен превышать 20 символов');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    // Валидация цены
    const priceFields = form.querySelectorAll('input[name="price"]');
    priceFields.forEach(field => {
        if (field.value) {
            const price = parseFloat(field.value);
            if (isNaN(price) || price <= 0) {
                showFieldError(field, 'Цена должна быть положительным числом');
                isValid = false;
            } else if (price > 999999999.99) {
                showFieldError(field, 'Цена не должна превышать 999 999 999.99');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    // Валидация заголовка объявления
    const titleFields = form.querySelectorAll('input[name="title"]');
    titleFields.forEach(field => {
        if (field.value) {
            const title = field.value.trim();
            if (title.length < 10) {
                showFieldError(field, 'Заголовок должен содержать минимум 10 символов');
                isValid = false;
            } else if (title.length > 255) {
                showFieldError(field, 'Заголовок не должен превышать 255 символов');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    // Валидация описания
    const descriptionFields = form.querySelectorAll('textarea[name="description"]');
    descriptionFields.forEach(field => {
        if (field.value) {
            const description = field.value.trim();
            if (description.length < 20) {
                showFieldError(field, 'Описание должно содержать минимум 20 символов');
                isValid = false;
            } else if (description.length > 5000) {
                showFieldError(field, 'Описание не должно превышать 5000 символов');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        }
    });
    
    // Валидация комментария отзыва
    const commentFields = form.querySelectorAll('textarea[name="comment"]');
    commentFields.forEach(field => {
        if (field.value) {
            const comment = field.value.trim();
            if (comment.length < 10) {
                showFieldError(field, 'Комментарий должен содержать минимум 10 символов');
                isValid = false;
            } else if (comment.length > 2000) {
                showFieldError(field, 'Комментарий не должен превышать 2000 символов');
                isValid = false;
            } else {
                clearFieldError(field);
            }
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
    // Паттерн: имя@домен.домен_верхнего_уровня
    // Гарантирует наличие хотя бы одной точки после символа @ перед TLD
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$/;
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
    
    // Создаём (или находим) контейнер для тостов поверх вёрстки
    let container = document.getElementById('toast-notifications-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-notifications-container';
        container.style.position = 'fixed';
        container.style.top = '1rem';
        container.style.right = '1rem';
        container.style.zIndex = '1080';
        container.style.maxWidth = '400px';
        container.style.width = '100%';
        container.style.pointerEvents = 'none';
        document.body.appendChild(container);
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    alertDiv.style.pointerEvents = 'auto';
    alertDiv.style.boxShadow = '0 0.5rem 1rem rgba(0,0,0,.15)';
    alertDiv.style.marginBottom = '0.5rem';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.prepend(alertDiv);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}

// Получение CSRF токена
function getCSRFToken() {
    // Пробуем найти токен в скрытом поле формы
    let token = document.querySelector('[name=csrfmiddlewaretoken]');
    if (token) {
        return token.value;
    }
    // Пробуем найти токен в cookie (Django использует csrftoken)
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const parts = cookie.trim().split('=');
        if (parts.length === 2) {
            const name = parts[0].trim();
            const value = parts[1].trim();
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
    }
    console.warn('CSRF token not found');
    return '';
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

// Позиционирование выпадающего меню, чтобы не выходило за границы
function initDropdownPositioning() {
    const dropdownMenus = document.querySelectorAll('.dropdown-menu');
    
    dropdownMenus.forEach(menu => {
        const dropdown = menu.closest('.dropdown');
        if (!dropdown) return;
        
        // При открытии меню проверяем позицию
        const toggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
        if (toggle) {
            toggle.addEventListener('show.bs.dropdown', function() {
                setTimeout(() => {
                    adjustDropdownPosition(menu);
                }, 10);
            });
            
            // Также проверяем при изменении размера окна
            window.addEventListener('resize', function() {
                if (menu.classList.contains('show')) {
                    adjustDropdownPosition(menu);
                }
            });
        }
    });
}

function adjustDropdownPosition(menu) {
    const rect = menu.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Проверяем, выходит ли меню за правый край
    if (rect.right > viewportWidth) {
        menu.style.left = 'auto';
        menu.style.right = '0';
        menu.style.transform = 'translateX(0)';
    }
    
    // Проверяем, выходит ли меню за левый край
    if (rect.left < 0) {
        menu.style.left = '0';
        menu.style.right = 'auto';
        menu.style.transform = 'translateX(0)';
    }
    
    // Проверяем, выходит ли меню за нижний край (опционально - можно открывать вверх)
    if (rect.bottom > viewportHeight) {
        menu.style.top = 'auto';
        menu.style.bottom = '100%';
        menu.style.marginBottom = '0.5rem';
        menu.style.marginTop = '0';
    }
}

// Горячие клавиши (минимум 8)
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K - Поиск
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[type="search"], input[name="search"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Ctrl/Cmd + N - Новое объявление
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            const createLink = document.querySelector('a[href*="create"], a[href*="new"]');
            if (createLink) {
                window.location.href = createLink.href;
            }
        }
        
        // Esc - Закрыть модальное окно или выйти из поиска
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal.show');
            if (modal) {
                const closeBtn = modal.querySelector('[data-bs-dismiss="modal"]');
                if (closeBtn) closeBtn.click();
            }
            hideSearchSuggestions();
        }
        
        // / - Фокус на поиск (если не в input)
        if (e.key === '/' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            const searchInput = document.querySelector('input[type="search"], input[name="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Ctrl/Cmd + F - Избранное
        if ((e.ctrlKey || e.metaKey) && e.key === 'f' && !e.shiftKey) {
            e.preventDefault();
            const favoritesLink = document.querySelector('a[href*="favorite"]');
            if (favoritesLink) {
                window.location.href = favoritesLink.href;
            }
        }
        
        // Ctrl/Cmd + P - Профиль
        if ((e.ctrlKey || e.metaKey) && e.key === 'p' && !e.shiftKey) {
            e.preventDefault();
            const profileLink = document.querySelector('a[href*="profile"]');
            if (profileLink) {
                window.location.href = profileLink.href;
            }
        }
        
        // Ctrl/Cmd + H - Главная
        if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
            e.preventDefault();
            window.location.href = '/';
        }
        
        // Ctrl/Cmd + S - Сохранить (в формах)
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            const form = document.querySelector('form');
            if (form && e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                e.preventDefault();
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    submitBtn.click();
                }
            }
        }
        
        // Стрелки вверх/вниз для навигации по предложениям поиска
        const suggestions = document.querySelector('.search-suggestions');
        if (suggestions && suggestions.style.display !== 'none') {
            const items = suggestions.querySelectorAll('.suggestion-item');
            let currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                currentIndex = (currentIndex + 1) % items.length;
                items.forEach((item, idx) => {
                    item.classList.toggle('active', idx === currentIndex);
                });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                currentIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
                items.forEach((item, idx) => {
                    item.classList.toggle('active', idx === currentIndex);
                });
            } else if (e.key === 'Enter' && currentIndex >= 0) {
                e.preventDefault();
                items[currentIndex].click();
            }
        }
    });
    
    // Показываем подсказки по горячим клавишам
    showKeyboardShortcutsHelp();
}

function showKeyboardShortcutsHelp() {
    // Создаем элемент с подсказками (можно показать по Ctrl+?)
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            const helpModal = document.getElementById('keyboard-shortcuts-help');
            if (helpModal) {
                const modal = new bootstrap.Modal(helpModal);
                modal.show();
            }
        }
    });
}

// Инициализация всех функций при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initImagePreview();
    initSearchAutocomplete();
    initLazyLoading();
    initKeyboardShortcuts();
});



