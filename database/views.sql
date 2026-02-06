-- SQL VIEW для отчетности и аналитики
-- Совместимо с SQLite (используется в проекте)

-- 1. VIEW: Сводная информация по объявлениям
CREATE VIEW IF NOT EXISTS v_listings_summary AS
SELECT 
    l.id,
    l.title,
    l.price,
    l.currency,
    l.status,
    l.condition,
    l.location,
    l.views_count,
    l.favorites_count,
    l.created_at,
    l.published_at,
    u.username as user_username,
    u.email as user_email,
    c.name as category_name,
    c.slug as category_slug,
    CASE 
        WHEN l.status = 'active' THEN 'Активно'
        WHEN l.status = 'pending' THEN 'На модерации'
        WHEN l.status = 'sold' THEN 'Продано'
        WHEN l.status = 'expired' THEN 'Истекло'
        ELSE 'Неизвестно'
    END as status_label
FROM listings l
JOIN users u ON l.user_id = u.id
JOIN categories c ON l.category_id = c.id;

-- 2. VIEW: Статистика по пользователям
CREATE VIEW IF NOT EXISTS v_users_statistics AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.is_active,
    u.created_at,
    r.name as role_name,
    COALESCE(us.listings_count, 0) as listings_count,
    COALESCE(us.sold_count, 0) as sold_count,
    COALESCE(us.total_earnings, 0) as total_earnings,
    COALESCE(ur.total_score, 0) as reputation_score,
    ur.reputation_level,
    ur.positive_reviews,
    ur.negative_reviews,
    ur.neutral_reviews,
    COUNT(DISTINCT rev.id) as reviews_received_count,
    COUNT(DISTINCT fav.id) as favorites_count
FROM users u
LEFT JOIN roles r ON u.role_id = r.id
LEFT JOIN user_statistics us ON u.id = us.user_id
LEFT JOIN user_reputation ur ON u.id = ur.user_id
LEFT JOIN reviews rev ON u.id = rev.reviewed_user_id
LEFT JOIN user_favorites fav ON u.id = fav.user_id
GROUP BY u.id, u.username, u.email, u.is_active, u.created_at, r.name, 
         us.listings_count, us.sold_count, us.total_earnings,
         ur.total_score, ur.reputation_level, ur.positive_reviews, 
         ur.negative_reviews, ur.neutral_reviews;

-- 3. VIEW: Отчет по категориям
CREATE VIEW IF NOT EXISTS v_categories_report AS
SELECT 
    c.id,
    c.name,
    c.slug,
    c.is_active,
    COUNT(DISTINCT l.id) as total_listings,
    COUNT(DISTINCT CASE WHEN l.status = 'active' THEN l.id END) as active_listings,
    COUNT(DISTINCT CASE WHEN l.status = 'pending' THEN l.id END) as pending_listings,
    COUNT(DISTINCT CASE WHEN l.status = 'sold' THEN l.id END) as sold_listings,
    COALESCE(AVG(l.price), 0) as avg_price,
    COALESCE(MIN(l.price), 0) as min_price,
    COALESCE(MAX(l.price), 0) as max_price,
    COALESCE(SUM(CASE WHEN l.status = 'sold' THEN l.price ELSE 0 END), 0) as total_revenue,
    SUM(l.views_count) as total_views,
    SUM(l.favorites_count) as total_favorites
FROM categories c
LEFT JOIN listings l ON c.id = l.category_id
GROUP BY c.id, c.name, c.slug, c.is_active;

-- 4. VIEW: Ежедневная активность
CREATE VIEW IF NOT EXISTS v_daily_activity AS
SELECT 
    DATE(created_at) as activity_date,
    'listing' as activity_type,
    COUNT(*) as count,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count
FROM listings
GROUP BY DATE(created_at)

UNION ALL

SELECT 
    DATE(created_at) as activity_date,
    'review' as activity_type,
    COUNT(*) as count,
    COUNT(CASE WHEN is_positive = 1 THEN 1 END) as active_count,
    COUNT(CASE WHEN is_positive = 0 THEN 1 END) as pending_count
FROM reviews
GROUP BY DATE(created_at)

UNION ALL

SELECT 
    DATE(date_joined) as activity_date,
    'user' as activity_type,
    COUNT(*) as count,
    COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count,
    0 as pending_count
FROM users
GROUP BY DATE(date_joined);

-- 5. VIEW: Модерация объявлений
CREATE VIEW IF NOT EXISTS v_moderation_report AS
SELECT 
    lm.id,
    lm.action,
    lm.reason,
    lm.created_at as moderation_date,
    l.id as listing_id,
    l.title as listing_title,
    l.status as listing_status,
    u.username as moderator_username,
    lu.username as listing_owner_username,
    lu.email as listing_owner_email
FROM listing_moderation lm
JOIN listings l ON lm.listing_id = l.id
JOIN users u ON lm.moderator_id = u.id
JOIN users lu ON l.user_id = lu.id;

-- 6. VIEW: Отчет по отзывам
CREATE VIEW IF NOT EXISTS v_reviews_report AS
SELECT 
    r.id,
    r.rating,
    r.comment,
    r.is_positive,
    r.created_at,
    ru.username as reviewer_username,
    reu.username as reviewed_user_username,
    reu.email as reviewed_user_email,
    ur.reputation_level as reviewed_user_reputation
FROM reviews r
JOIN users ru ON r.reviewer_id = ru.id
JOIN users reu ON r.reviewed_user_id = reu.id
LEFT JOIN user_reputation ur ON r.reviewed_user_id = ur.user_id;


