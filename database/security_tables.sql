-- Дополнительные таблицы для логирования и аудита
-- Неделя 5-6: Безопасность и администрирование

-- Таблица для логирования активности пользователей
CREATE TABLE user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX idx_user_activity_log_user_id ON user_activity_log(user_id);
CREATE INDEX idx_user_activity_log_action ON user_activity_log(action);
CREATE INDEX idx_user_activity_log_created_at ON user_activity_log(created_at);
CREATE INDEX idx_user_activity_log_entity ON user_activity_log(entity_type, entity_id);

-- Таблица для аудита изменений
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для аудита
CREATE INDEX idx_audit_log_table_name ON audit_log(table_name);
CREATE INDEX idx_audit_log_operation ON audit_log(operation);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Таблица для сессий пользователей
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_key VARCHAR(40) NOT NULL UNIQUE,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Индексы для сессий
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_session_key ON user_sessions(session_key);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Таблица для неудачных попыток входа
CREATE TABLE failed_login_attempts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(255),
    ip_address INET NOT NULL,
    user_agent TEXT,
    attempt_count INTEGER DEFAULT 1,
    last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_until TIMESTAMP
);

-- Индексы для неудачных попыток
CREATE INDEX idx_failed_login_ip ON failed_login_attempts(ip_address);
CREATE INDEX idx_failed_login_username ON failed_login_attempts(username);
CREATE INDEX idx_failed_login_email ON failed_login_attempts(email);
CREATE INDEX idx_failed_login_blocked ON failed_login_attempts(is_blocked, blocked_until);

-- Таблица для резервных копий
CREATE TABLE backup_log (
    id SERIAL PRIMARY KEY,
    backup_type VARCHAR(50) NOT NULL, -- 'full', 'incremental', 'differential'
    file_path TEXT NOT NULL,
    file_size BIGINT,
    status VARCHAR(20) NOT NULL, -- 'success', 'failed', 'in_progress'
    error_message TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Индексы для резервных копий
CREATE INDEX idx_backup_log_type ON backup_log(backup_type);
CREATE INDEX idx_backup_log_status ON backup_log(status);
CREATE INDEX idx_backup_log_created_at ON backup_log(created_at);

-- Таблица для системных настроек
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string', -- 'string', 'integer', 'boolean', 'json'
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Вставка базовых настроек
INSERT INTO system_settings (setting_key, setting_value, setting_type, description) VALUES
('site_name', 'ЧёПочём', 'string', 'Название сайта'),
('site_description', 'Платформа вторичного рынка товаров', 'string', 'Описание сайта'),
('max_listing_images', '10', 'integer', 'Максимальное количество изображений в объявлении'),
('listing_expiry_days', '30', 'integer', 'Количество дней до истечения объявления'),
('max_failed_login_attempts', '5', 'integer', 'Максимальное количество неудачных попыток входа'),
('login_block_duration_minutes', '15', 'integer', 'Длительность блокировки входа в минутах'),
('enable_registration', 'true', 'boolean', 'Разрешить регистрацию новых пользователей'),
('require_email_verification', 'false', 'boolean', 'Требовать подтверждение email'),
('backup_retention_days', '30', 'integer', 'Количество дней хранения резервных копий');

-- Таблица для разрешений ролей
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission VARCHAR(100) NOT NULL,
    granted BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission)
);

-- Вставка базовых разрешений
INSERT INTO role_permissions (role_id, permission) 
SELECT r.id, p.permission
FROM roles r
CROSS JOIN (
    VALUES 
        ('create_listing'),
        ('edit_own_listing'),
        ('delete_own_listing'),
        ('leave_review'),
        ('report_content'),
        ('manage_favorites'),
        ('view_profile')
) AS p(permission)
WHERE r.name = 'user';

INSERT INTO role_permissions (role_id, permission) 
SELECT r.id, p.permission
FROM roles r
CROSS JOIN (
    VALUES 
        ('create_listing'),
        ('edit_own_listing'),
        ('delete_own_listing'),
        ('leave_review'),
        ('report_content'),
        ('manage_favorites'),
        ('view_profile'),
        ('moderate_listings'),
        ('view_reports'),
        ('ban_users'),
        ('view_moderation_log')
) AS p(permission)
WHERE r.name = 'moderator';

INSERT INTO role_permissions (role_id, permission) 
SELECT r.id, p.permission
FROM roles r
CROSS JOIN (
    VALUES 
        ('create_listing'),
        ('edit_own_listing'),
        ('delete_own_listing'),
        ('leave_review'),
        ('report_content'),
        ('manage_favorites'),
        ('view_profile'),
        ('moderate_listings'),
        ('view_reports'),
        ('ban_users'),
        ('view_moderation_log'),
        ('manage_users'),
        ('manage_categories'),
        ('manage_roles'),
        ('view_statistics'),
        ('system_settings'),
        ('backup_management'),
        ('view_audit_log')
) AS p(permission)
WHERE r.name = 'admin';

-- Функция для очистки старых логов
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS VOID AS $$
DECLARE
    retention_days INTEGER;
BEGIN
    -- Получаем настройку из system_settings
    SELECT setting_value::INTEGER INTO retention_days
    FROM system_settings 
    WHERE setting_key = 'log_retention_days';
    
    -- Если настройка не найдена, используем значение по умолчанию
    IF retention_days IS NULL THEN
        retention_days := 90;
    END IF;
    
    -- Удаляем старые записи активности
    DELETE FROM user_activity_log 
    WHERE created_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;
    
    -- Удаляем старые записи аудита
    DELETE FROM audit_log 
    WHERE created_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;
    
    -- Удаляем истекшие сессии
    DELETE FROM user_sessions 
    WHERE expires_at < CURRENT_TIMESTAMP;
    
    -- Удаляем старые неудачные попытки входа
    DELETE FROM failed_login_attempts 
    WHERE last_attempt < CURRENT_TIMESTAMP - INTERVAL '7 days';
    
    -- Логируем выполнение очистки
    INSERT INTO user_activity_log (user_id, action, details, created_at)
    VALUES (NULL, 'cleanup_old_logs', 
            jsonb_build_object('retention_days', retention_days), 
            CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- Функция для проверки блокировки IP
CREATE OR REPLACE FUNCTION check_ip_blocked(p_ip_address INET)
RETURNS BOOLEAN AS $$
DECLARE
    attempt_record RECORD;
    max_attempts INTEGER;
    block_duration INTEGER;
BEGIN
    -- Получаем настройки
    SELECT setting_value::INTEGER INTO max_attempts
    FROM system_settings 
    WHERE setting_key = 'max_failed_login_attempts';
    
    SELECT setting_value::INTEGER INTO block_duration
    FROM system_settings 
    WHERE setting_key = 'login_block_duration_minutes';
    
    -- Если настройки не найдены, используем значения по умолчанию
    IF max_attempts IS NULL THEN max_attempts := 5; END IF;
    IF block_duration IS NULL THEN block_duration := 15; END IF;
    
    -- Проверяем блокировку
    SELECT * INTO attempt_record
    FROM failed_login_attempts 
    WHERE ip_address = p_ip_address 
        AND is_blocked = TRUE 
        AND blocked_until > CURRENT_TIMESTAMP;
    
    RETURN attempt_record IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Функция для регистрации неудачной попытки входа
CREATE OR REPLACE FUNCTION record_failed_login(
    p_username VARCHAR(50),
    p_email VARCHAR(255),
    p_ip_address INET,
    p_user_agent TEXT
) RETURNS VOID AS $$
DECLARE
    attempt_record RECORD;
    max_attempts INTEGER;
    block_duration INTEGER;
BEGIN
    -- Получаем настройки
    SELECT setting_value::INTEGER INTO max_attempts
    FROM system_settings 
    WHERE setting_key = 'max_failed_login_attempts';
    
    SELECT setting_value::INTEGER INTO block_duration
    FROM system_settings 
    WHERE setting_key = 'login_block_duration_minutes';
    
    -- Если настройки не найдены, используем значения по умолчанию
    IF max_attempts IS NULL THEN max_attempts := 5; END IF;
    IF block_duration IS NULL THEN block_duration := 15; END IF;
    
    -- Ищем существующую запись
    SELECT * INTO attempt_record
    FROM failed_login_attempts 
    WHERE ip_address = p_ip_address;
    
    IF attempt_record IS NOT NULL THEN
        -- Обновляем существующую запись
        UPDATE failed_login_attempts 
        SET 
            attempt_count = attempt_count + 1,
            last_attempt = CURRENT_TIMESTAMP,
            is_blocked = (attempt_count + 1 >= max_attempts),
            blocked_until = CASE 
                WHEN attempt_count + 1 >= max_attempts THEN 
                    CURRENT_TIMESTAMP + (block_duration || ' minutes')::INTERVAL
                ELSE blocked_until 
            END
        WHERE ip_address = p_ip_address;
    ELSE
        -- Создаем новую запись
        INSERT INTO failed_login_attempts (
            username, email, ip_address, user_agent, 
            attempt_count, is_blocked, blocked_until
        ) VALUES (
            p_username, p_email, p_ip_address, p_user_agent,
            1, (1 >= max_attempts), 
            CASE 
                WHEN 1 >= max_attempts THEN 
                    CURRENT_TIMESTAMP + (block_duration || ' minutes')::INTERVAL
                ELSE NULL 
            END
        );
    END IF;
END;
$$ LANGUAGE plpgsql;
