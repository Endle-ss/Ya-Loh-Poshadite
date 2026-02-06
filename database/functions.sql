-- 1. Функция обновления репутации пользователя
CREATE OR REPLACE FUNCTION update_user_reputation(p_user_id INTEGER)
RETURNS VOID AS $$
DECLARE
    total_reviews INTEGER;
    positive_count INTEGER;
    negative_count INTEGER;
    neutral_count INTEGER;
    total_score INTEGER;
    reputation_level VARCHAR(20);
BEGIN
    SELECT 
        COUNT(*),
        COUNT(CASE WHEN is_positive = TRUE THEN 1 END),
        COUNT(CASE WHEN is_positive = FALSE AND rating <= 2 THEN 1 END),
        COUNT(CASE WHEN is_positive = FALSE AND rating > 2 THEN 1 END),
        COALESCE(SUM(rating), 0)
    INTO total_reviews, positive_count, negative_count, neutral_count, total_score
    FROM reviews 
    WHERE reviewed_user_id = p_user_id;
    
    IF total_reviews = 0 THEN
        reputation_level := 'newbie';
    ELSIF positive_count >= total_reviews * 0.8 THEN
        reputation_level := 'master';
    ELSIF positive_count >= total_reviews * 0.6 THEN
        reputation_level := 'expert';
    ELSE
        reputation_level := 'trusted';
    END IF;
    
    INSERT INTO user_reputation (
        user_id, total_score, positive_reviews, negative_reviews, 
        neutral_reviews, reputation_level, created_at, updated_at
    ) VALUES (
        p_user_id, total_score, positive_count, negative_count,
        neutral_count, reputation_level, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ) ON CONFLICT (user_id) DO UPDATE SET
        total_score = EXCLUDED.total_score,
        positive_reviews = EXCLUDED.positive_reviews,
        negative_reviews = EXCLUDED.negative_reviews,
        neutral_reviews = EXCLUDED.neutral_reviews,
        reputation_level = EXCLUDED.reputation_level,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- 2. Функция расчета статистики пользователя
CREATE OR REPLACE FUNCTION calculate_user_statistics(p_user_id INTEGER)
RETURNS TABLE(
    listings_count INTEGER,
    sold_count INTEGER,
    purchased_count INTEGER,
    total_earnings DECIMAL(12,2),
    total_spent DECIMAL(12,2),
    response_rate DECIMAL(5,2),
    average_response_time INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(COUNT(l.id), 0)::INTEGER as listings_count,
        COALESCE(COUNT(CASE WHEN l.status = 'sold' THEN 1 END), 0)::INTEGER as sold_count,
        0::INTEGER as purchased_count,
        COALESCE(SUM(CASE WHEN l.status = 'sold' THEN l.price ELSE 0 END), 0) as total_earnings,
        0::DECIMAL(12,2) as total_spent,
        CASE 
            WHEN COUNT(l.id) > 0 THEN 
                (COUNT(CASE WHEN l.status = 'sold' THEN 1 END)::DECIMAL / COUNT(l.id) * 100)
            ELSE 0 
        END as response_rate,
        0::INTEGER as average_response_time
    FROM listings l
    WHERE l.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- 3. Функция поиска объявлений с фильтрацией
CREATE OR REPLACE FUNCTION search_listings(
    p_search_query TEXT DEFAULT NULL,
    p_category_id INTEGER DEFAULT NULL,
    p_min_price DECIMAL(12,2) DEFAULT NULL,
    p_max_price DECIMAL(12,2) DEFAULT NULL,
    p_location TEXT DEFAULT NULL,
    p_sort_by VARCHAR(20) DEFAULT 'newest',
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
) RETURNS TABLE(
    id INTEGER,
    title VARCHAR(255),
    description TEXT,
    price DECIMAL(12,2),
    currency VARCHAR(3),
    location VARCHAR(255),
    created_at TIMESTAMP,
    views_count INTEGER,
    favorites_count INTEGER,
    user_username VARCHAR(50),
    category_name VARCHAR(100),
    image_url TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.id,
        l.title,
        l.description,
        l.price,
        l.currency,
        l.location,
        l.created_at,
        l.views_count,
        l.favorites_count,
        u.username,
        c.name as category_name,
        li.image_url
    FROM listings l
    JOIN users u ON l.user_id = u.id
    JOIN categories c ON l.category_id = c.id
    LEFT JOIN listing_images li ON l.id = li.listing_id AND li.is_primary = TRUE
    WHERE l.status = 'active'
        AND (p_search_query IS NULL OR 
             l.title ILIKE '%' || p_search_query || '%' OR 
             l.description ILIKE '%' || p_search_query || '%')
        AND (p_category_id IS NULL OR l.category_id = p_category_id)
        AND (p_min_price IS NULL OR l.price >= p_min_price)
        AND (p_max_price IS NULL OR l.price <= p_max_price)
        AND (p_location IS NULL OR l.location ILIKE '%' || p_location || '%')
    ORDER BY 
        CASE WHEN p_sort_by = 'price_low' THEN l.price END ASC,
        CASE WHEN p_sort_by = 'price_high' THEN l.price END DESC,
        CASE WHEN p_sort_by = 'popular' THEN l.views_count END DESC,
        CASE WHEN p_sort_by = 'newest' OR p_sort_by IS NULL THEN l.created_at END DESC
    LIMIT p_limit OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- 4. Функция проверки прав доступа пользователя
CREATE OR REPLACE FUNCTION check_user_permission(
    p_user_id INTEGER,
    p_permission VARCHAR(50),
    p_entity_type VARCHAR(50) DEFAULT NULL,
    p_entity_id INTEGER DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    user_role VARCHAR(50);
    is_owner BOOLEAN := FALSE;
BEGIN
    SELECT r.name INTO user_role
    FROM users u
    JOIN roles r ON u.role_id = r.id
    WHERE u.id = p_user_id AND u.is_active = TRUE;
    
    IF user_role IS NULL THEN
        RETURN FALSE;
    END IF;
    
    IF user_role = 'admin' THEN
        RETURN TRUE;
    END IF;
    
    IF user_role = 'moderator' AND p_permission IN ('moderate_listings', 'view_reports', 'ban_users') THEN
        RETURN TRUE;
    END IF;
    
    IF p_entity_type = 'listing' AND p_entity_id IS NOT NULL THEN
        SELECT EXISTS(
            SELECT 1 FROM listings WHERE id = p_entity_id AND user_id = p_user_id
        ) INTO is_owner;
    ELSIF p_entity_type = 'user' AND p_entity_id IS NOT NULL THEN
        is_owner := (p_user_id = p_entity_id);
    END IF;
    
    CASE p_permission
        WHEN 'create_listing' THEN
            RETURN user_role IN ('user', 'moderator', 'admin');
        WHEN 'edit_own_listing' THEN
            RETURN is_owner;
        WHEN 'delete_own_listing' THEN
            RETURN is_owner;
        WHEN 'leave_review' THEN
            RETURN user_role IN ('user', 'moderator', 'admin');
        WHEN 'report_content' THEN
            RETURN user_role IN ('user', 'moderator', 'admin');
        WHEN 'manage_favorites' THEN
            RETURN user_role IN ('user', 'moderator', 'admin');
        ELSE
            RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- 5. Функция генерации отчета по активности
CREATE OR REPLACE FUNCTION generate_activity_report(
    p_start_date DATE,
    p_end_date DATE,
    p_user_id INTEGER DEFAULT NULL
) RETURNS TABLE(
    date DATE,
    new_listings INTEGER,
    approved_listings INTEGER,
    rejected_listings INTEGER,
    new_reviews INTEGER,
    new_users INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.date,
        COALESCE(l.new_count, 0)::INTEGER as new_listings,
        COALESCE(l.approved_count, 0)::INTEGER as approved_listings,
        COALESCE(l.rejected_count, 0)::INTEGER as rejected_listings,
        COALESCE(r.count, 0)::INTEGER as new_reviews,
        COALESCE(u.count, 0)::INTEGER as new_users
    FROM generate_series(p_start_date, p_end_date, '1 day'::interval)::DATE as d
    LEFT JOIN (
        SELECT 
            DATE(created_at) as date,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as new_count,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as approved_count,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count
        FROM listings 
        WHERE (p_user_id IS NULL OR user_id = p_user_id)
        GROUP BY DATE(created_at)
    ) l ON d = l.date
    LEFT JOIN (
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM reviews 
        WHERE (p_user_id IS NULL OR reviewer_id = p_user_id)
        GROUP BY DATE(created_at)
    ) r ON d = r.date
    LEFT JOIN (
        SELECT DATE(date_joined) as date, COUNT(*) as count
        FROM users 
        WHERE (p_user_id IS NULL OR id = p_user_id)
        GROUP BY DATE(date_joined)
    ) u ON d = u.date
    ORDER BY d;
END;
$$ LANGUAGE plpgsql;

-- 6. Функция шифрования пароля
CREATE OR REPLACE FUNCTION hash_password(p_password TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN crypt(p_password, gen_salt('bf', 12));
END;
$$ LANGUAGE plpgsql;

-- 7. Функция проверки пароля
CREATE OR REPLACE FUNCTION verify_password(p_password TEXT, p_hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN p_hash = crypt(p_password, p_hash);
END;
$$ LANGUAGE plpgsql;



