-- Триггеры для ЧёПочём
-- Неделя 4-5: Расширенная серверная логика

-- 1. Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Применение триггера к таблицам
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_reputation_updated_at 
    BEFORE UPDATE ON user_reputation 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reviews_updated_at 
    BEFORE UPDATE ON reviews 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_listings_updated_at 
    BEFORE UPDATE ON listings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_statistics_updated_at 
    BEFORE UPDATE ON user_statistics 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2. Триггер для автоматического создания профиля пользователя
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_profiles (user_id, created_at, updated_at)
    VALUES (NEW.id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    
    INSERT INTO user_reputation (user_id, created_at, updated_at)
    VALUES (NEW.id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    
    INSERT INTO user_statistics (user_id, created_at, updated_at)
    VALUES (NEW.id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_user_profile_trigger
    AFTER INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION create_user_profile();

-- 3. Триггер для автоматического обновления репутации при создании отзыва
CREATE OR REPLACE FUNCTION update_reputation_on_review()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM update_user_reputation(NEW.reviewed_user_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_reputation_on_review_trigger
    AFTER INSERT OR UPDATE OR DELETE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_reputation_on_review();

-- 4. Триггер для автоматического обновления счетчика избранных
CREATE OR REPLACE FUNCTION update_favorites_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE listings 
        SET favorites_count = favorites_count + 1
        WHERE id = NEW.listing_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE listings 
        SET favorites_count = GREATEST(favorites_count - 1, 0)
        WHERE id = OLD.listing_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_favorites_count_trigger
    AFTER INSERT OR DELETE ON user_favorites
    FOR EACH ROW EXECUTE FUNCTION update_favorites_count();

-- 5. Триггер для автоматического обновления счетчика просмотров
CREATE OR REPLACE FUNCTION update_views_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Обновляем счетчик просмотров при каждом обращении к объявлению
    -- Это будет вызываться из приложения
    UPDATE listings 
    SET views_count = views_count + 1
    WHERE id = NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. Триггер для логирования изменений в критических таблицах
CREATE OR REPLACE FUNCTION log_critical_changes()
RETURNS TRIGGER AS $$
DECLARE
    operation_type VARCHAR(10);
    old_data JSONB;
    new_data JSONB;
BEGIN
    -- Определение типа операции
    IF TG_OP = 'INSERT' THEN
        operation_type := 'INSERT';
        new_data := to_jsonb(NEW);
        old_data := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        operation_type := 'UPDATE';
        old_data := to_jsonb(OLD);
        new_data := to_jsonb(NEW);
    ELSIF TG_OP = 'DELETE' THEN
        operation_type := 'DELETE';
        old_data := to_jsonb(OLD);
        new_data := NULL;
    END IF;
    
    -- Логирование в таблицу аудита
    INSERT INTO audit_log (
        table_name, operation, old_data, new_data, 
        user_id, created_at
    ) VALUES (
        TG_TABLE_NAME, operation_type, old_data, new_data,
        COALESCE(NEW.user_id, OLD.user_id), CURRENT_TIMESTAMP
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Применение триггера аудита к критическим таблицам
CREATE TRIGGER audit_users_trigger
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION log_critical_changes();

CREATE TRIGGER audit_listings_trigger
    AFTER INSERT OR UPDATE OR DELETE ON listings
    FOR EACH ROW EXECUTE FUNCTION log_critical_changes();

CREATE TRIGGER audit_reviews_trigger
    AFTER INSERT OR UPDATE OR DELETE ON reviews
    FOR EACH ROW EXECUTE FUNCTION log_critical_changes();

-- 7. Триггер для автоматического создания уведомлений
CREATE OR REPLACE FUNCTION create_notification_on_action()
RETURNS TRIGGER AS $$
BEGIN
    -- Уведомление при одобрении объявления
    IF TG_TABLE_NAME = 'listing_moderation' AND NEW.action = 'approve' THEN
        INSERT INTO notifications (user_id, type, title, content, related_entity_type, related_entity_id, created_at)
        SELECT 
            l.user_id, 
            'listing_approved', 
            'Объявление одобрено',
            'Ваше объявление "' || l.title || '" было одобрено и опубликовано.',
            'listing', 
            NEW.listing_id, 
            CURRENT_TIMESTAMP
        FROM listings l WHERE l.id = NEW.listing_id;
    END IF;
    
    -- Уведомление при отклонении объявления
    IF TG_TABLE_NAME = 'listing_moderation' AND NEW.action = 'reject' THEN
        INSERT INTO notifications (user_id, type, title, content, related_entity_type, related_entity_id, created_at)
        SELECT 
            l.user_id, 
            'listing_rejected', 
            'Объявление отклонено',
            'Ваше объявление "' || l.title || '" было отклонено. Причина: ' || COALESCE(NEW.reason, 'Не указана'),
            'listing', 
            NEW.listing_id, 
            CURRENT_TIMESTAMP
        FROM listings l WHERE l.id = NEW.listing_id;
    END IF;
    
    -- Уведомление при новом отзыве
    IF TG_TABLE_NAME = 'reviews' AND TG_OP = 'INSERT' THEN
        INSERT INTO notifications (user_id, type, title, content, related_entity_type, related_entity_id, created_at)
        VALUES (
            NEW.reviewed_user_id,
            'new_review',
            'Новый отзыв',
            'Пользователь ' || (SELECT username FROM users WHERE id = NEW.reviewer_id) || ' оставил вам отзыв.',
            'review',
            NEW.id,
            CURRENT_TIMESTAMP
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_notification_on_moderation_trigger
    AFTER INSERT ON listing_moderation
    FOR EACH ROW EXECUTE FUNCTION create_notification_on_action();

CREATE TRIGGER create_notification_on_review_trigger
    AFTER INSERT ON reviews
    FOR EACH ROW EXECUTE FUNCTION create_notification_on_action();

-- 8. Триггер для автоматического обновления статистики
CREATE OR REPLACE FUNCTION update_user_statistics_auto()
RETURNS TRIGGER AS $$
DECLARE
    target_user_id INTEGER;
BEGIN
    -- Определение пользователя для обновления статистики
    IF TG_TABLE_NAME = 'listings' THEN
        target_user_id := COALESCE(NEW.user_id, OLD.user_id);
    ELSIF TG_TABLE_NAME = 'reviews' THEN
        target_user_id := COALESCE(NEW.reviewed_user_id, OLD.reviewed_user_id);
    END IF;
    
    -- Обновление статистики
    UPDATE user_statistics 
    SET 
        listings_count = (
            SELECT COUNT(*) FROM listings 
            WHERE user_id = target_user_id AND status IN ('active', 'pending')
        ),
        sold_count = (
            SELECT COUNT(*) FROM listings 
            WHERE user_id = target_user_id AND status = 'sold'
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = target_user_id;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_statistics_on_listing_trigger
    AFTER INSERT OR UPDATE OR DELETE ON listings
    FOR EACH ROW EXECUTE FUNCTION update_user_statistics_auto();

-- 9. Триггер для проверки целостности данных
CREATE OR REPLACE FUNCTION validate_listing_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Проверка цены
    IF NEW.price <= 0 THEN
        RAISE EXCEPTION 'Цена должна быть больше нуля';
    END IF;
    
    -- Проверка заголовка
    IF NEW.title IS NULL OR LENGTH(TRIM(NEW.title)) = 0 THEN
        RAISE EXCEPTION 'Заголовок не может быть пустым';
    END IF;
    
    -- Проверка описания
    IF NEW.description IS NULL OR LENGTH(TRIM(NEW.description)) = 0 THEN
        RAISE EXCEPTION 'Описание не может быть пустым';
    END IF;
    
    -- Проверка существования пользователя
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = NEW.user_id AND is_active = TRUE) THEN
        RAISE EXCEPTION 'Пользователь не найден или неактивен';
    END IF;
    
    -- Проверка существования категории
    IF NOT EXISTS (SELECT 1 FROM categories WHERE id = NEW.category_id AND is_active = TRUE) THEN
        RAISE EXCEPTION 'Категория не найдена или неактивна';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_listing_data_trigger
    BEFORE INSERT OR UPDATE ON listings
    FOR EACH ROW EXECUTE FUNCTION validate_listing_data();

-- 10. Триггер для автоматического истечения объявлений
CREATE OR REPLACE FUNCTION expire_old_listings()
RETURNS TRIGGER AS $$
BEGIN
    -- Помечаем как истекшие объявления старше 30 дней
    UPDATE listings 
    SET status = 'expired'
    WHERE status = 'active' 
        AND created_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
        AND expires_at IS NULL;
    
    -- Помечаем как истекшие объявления с истекшим сроком
    UPDATE listings 
    SET status = 'expired'
    WHERE status = 'active' 
        AND expires_at IS NOT NULL 
        AND expires_at < CURRENT_TIMESTAMP;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Этот триггер будет вызываться периодически через cron или из приложения
-- CREATE TRIGGER expire_old_listings_trigger
--     AFTER INSERT ON listings
--     FOR EACH STATEMENT EXECUTE FUNCTION expire_old_listings();
