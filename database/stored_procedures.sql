-- 1. Процедура создания нового объявления
CREATE OR REPLACE FUNCTION create_listing(
    p_user_id INTEGER,
    p_category_id INTEGER,
    p_title VARCHAR(255),
    p_description TEXT,
    p_price DECIMAL(12,2),
    p_currency VARCHAR(3),
    p_condition VARCHAR(20),
    p_location VARCHAR(255),
    p_latitude DECIMAL(10,8),
    p_longitude DECIMAL(11,8),
    p_is_negotiable BOOLEAN,
    p_is_urgent BOOLEAN
) RETURNS INTEGER AS $$
DECLARE
    listing_id INTEGER;
BEGIN
    IF p_title IS NULL OR LENGTH(TRIM(p_title)) = 0 THEN
        RAISE EXCEPTION 'Заголовок не может быть пустым';
    END IF;
    
    IF p_price <= 0 THEN
        RAISE EXCEPTION 'Цена должна быть больше нуля';
    END IF;
    
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'ID пользователя обязателен';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id AND is_active = TRUE) THEN
        RAISE EXCEPTION 'Пользователь не найден или неактивен';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM categories WHERE id = p_category_id AND is_active = TRUE) THEN
        RAISE EXCEPTION 'Категория не найдена или неактивна';
    END IF;
    
    INSERT INTO listings (
        user_id, category_id, title, description, price, currency,
        condition, location, latitude, longitude, is_negotiable, is_urgent,
        status, created_at, updated_at
    ) VALUES (
        p_user_id, p_category_id, p_title, p_description, p_price, p_currency,
        p_condition, p_location, p_latitude, p_longitude, p_is_negotiable, p_is_urgent,
        'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ) RETURNING id INTO listing_id;
    
    UPDATE user_statistics 
    SET listings_count = listings_count + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id;
    
    INSERT INTO user_activity_log (user_id, action, entity_type, entity_id, created_at)
    VALUES (p_user_id, 'create_listing', 'listing', listing_id, CURRENT_TIMESTAMP);
    
    RETURN listing_id;
END;
$$ LANGUAGE plpgsql;

-- 2. Процедура обновления объявления
CREATE OR REPLACE FUNCTION update_listing(
    p_listing_id INTEGER,
    p_user_id INTEGER,
    p_title VARCHAR(255),
    p_description TEXT,
    p_price DECIMAL(12,2),
    p_location VARCHAR(255),
    p_is_negotiable BOOLEAN,
    p_is_urgent BOOLEAN
) RETURNS BOOLEAN AS $$
DECLARE
    listing_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM listings 
        WHERE id = p_listing_id AND user_id = p_user_id
    ) INTO listing_exists;
    
    IF NOT listing_exists THEN
        RAISE EXCEPTION 'Объявление не найдено или нет прав на редактирование';
    END IF;
    
    IF p_title IS NULL OR LENGTH(TRIM(p_title)) = 0 THEN
        RAISE EXCEPTION 'Заголовок не может быть пустым';
    END IF;
    
    IF p_price <= 0 THEN
        RAISE EXCEPTION 'Цена должна быть больше нуля';
    END IF;
    
    UPDATE listings SET
        title = p_title,
        description = p_description,
        price = p_price,
        location = p_location,
        is_negotiable = p_is_negotiable,
        is_urgent = p_is_urgent,
        status = 'pending',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_listing_id AND user_id = p_user_id;
    
    INSERT INTO user_activity_log (user_id, action, entity_type, entity_id, created_at)
    VALUES (p_user_id, 'update_listing', 'listing', p_listing_id, CURRENT_TIMESTAMP);
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 3. Процедура удаления объявления
CREATE OR REPLACE FUNCTION delete_listing(
    p_listing_id INTEGER,
    p_user_id INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    listing_exists BOOLEAN;
    user_role VARCHAR(50);
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM listings l
        JOIN users u ON l.user_id = u.id
        WHERE l.id = p_listing_id 
        AND (l.user_id = p_user_id OR u.role_id IN (
            SELECT id FROM roles WHERE name IN ('moderator', 'admin')
        ))
    ) INTO listing_exists;
    
    IF NOT listing_exists THEN
        RAISE EXCEPTION 'Нет прав на удаление объявления';
    END IF;
    
    SELECT r.name INTO user_role
    FROM users u
    JOIN roles r ON u.role_id = r.id
    WHERE u.id = p_user_id;
    
    INSERT INTO user_activity_log (user_id, action, entity_type, entity_id, created_at)
    VALUES (p_user_id, 'delete_listing', 'listing', p_listing_id, CURRENT_TIMESTAMP);
    
    DELETE FROM listings WHERE id = p_listing_id;
    
    UPDATE user_statistics 
    SET listings_count = GREATEST(listings_count - 1, 0),
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = (
        SELECT user_id FROM listings WHERE id = p_listing_id
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 4. Процедура создания отзыва
CREATE OR REPLACE FUNCTION create_review(
    p_reviewer_id INTEGER,
    p_reviewed_user_id INTEGER,
    p_rating INTEGER,
    p_comment TEXT
) RETURNS INTEGER AS $$
DECLARE
    review_id INTEGER;
    existing_review INTEGER;
BEGIN
    IF p_rating < 1 OR p_rating > 5 THEN
        RAISE EXCEPTION 'Рейтинг должен быть от 1 до 5';
    END IF;
    
    IF p_reviewer_id = p_reviewed_user_id THEN
        RAISE EXCEPTION 'Нельзя оставить отзыв самому себе';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_reviewer_id AND is_active = TRUE) THEN
        RAISE EXCEPTION 'Автор отзыва не найден или неактивен';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_reviewed_user_id AND is_active = TRUE) THEN
        RAISE EXCEPTION 'Получатель отзыва не найден или неактивен';
    END IF;
    
    SELECT id INTO existing_review
    FROM reviews 
    WHERE reviewer_id = p_reviewer_id AND reviewed_user_id = p_reviewed_user_id;
    
    IF existing_review IS NOT NULL THEN
        RAISE EXCEPTION 'Отзыв уже существует';
    END IF;
    
    INSERT INTO reviews (
        reviewer_id, reviewed_user_id, rating, comment, is_positive,
        created_at, updated_at
    ) VALUES (
        p_reviewer_id, p_reviewed_user_id, p_rating, p_comment, 
        CASE WHEN p_rating >= 4 THEN TRUE ELSE FALSE END,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ) RETURNING id INTO review_id;
    
    PERFORM update_user_reputation(p_reviewed_user_id);
    
    INSERT INTO user_activity_log (user_id, action, entity_type, entity_id, created_at)
    VALUES (p_reviewer_id, 'create_review', 'review', review_id, CURRENT_TIMESTAMP);
    
    RETURN review_id;
END;
$$ LANGUAGE plpgsql;

-- 5. Процедура модерации объявления
CREATE OR REPLACE FUNCTION moderate_listing(
    p_listing_id INTEGER,
    p_moderator_id INTEGER,
    p_action VARCHAR(20),
    p_reason TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    moderator_role VARCHAR(50);
    listing_exists BOOLEAN;
BEGIN
    SELECT r.name INTO moderator_role
    FROM users u
    JOIN roles r ON u.role_id = r.id
    WHERE u.id = p_moderator_id;
    
    IF moderator_role NOT IN ('moderator', 'admin') THEN
        RAISE EXCEPTION 'Недостаточно прав для модерации';
    END IF;
    
    SELECT EXISTS(
        SELECT 1 FROM listings WHERE id = p_listing_id AND status = 'pending'
    ) INTO listing_exists;
    
    IF NOT listing_exists THEN
        RAISE EXCEPTION 'Объявление не найдено или не требует модерации';
    END IF;
    
    IF p_action = 'approve' THEN
        UPDATE listings SET
            status = 'active',
            published_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = p_listing_id;
        
        INSERT INTO notifications (user_id, type, title, content, related_entity_type, related_entity_id, created_at)
        SELECT user_id, 'listing_approved', 'Объявление одобрено', 
               'Ваше объявление "' || title || '" было одобрено и опубликовано.',
               'listing', p_listing_id, CURRENT_TIMESTAMP
        FROM listings WHERE id = p_listing_id;
        
    ELSIF p_action = 'reject' THEN
        UPDATE listings SET
            status = 'rejected',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = p_listing_id;
        
        INSERT INTO notifications (user_id, type, title, content, related_entity_type, related_entity_id, created_at)
        SELECT user_id, 'listing_rejected', 'Объявление отклонено', 
               'Ваше объявление "' || title || '" было отклонено. Причина: ' || COALESCE(p_reason, 'Не указана'),
               'listing', p_listing_id, CURRENT_TIMESTAMP
        FROM listings WHERE id = p_listing_id;
        
    ELSE
        RAISE EXCEPTION 'Неверное действие модерации';
    END IF;
    
    INSERT INTO listing_moderation (listing_id, moderator_id, action, reason, created_at)
    VALUES (p_listing_id, p_moderator_id, p_action, p_reason, CURRENT_TIMESTAMP);
    
    INSERT INTO user_activity_log (user_id, action, entity_type, entity_id, created_at)
    VALUES (p_moderator_id, 'moderate_listing', 'listing', p_listing_id, CURRENT_TIMESTAMP);
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;



