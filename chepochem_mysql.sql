-- База данных для платформы "ЧёПочём" - MySQL версия
-- Создание базы данных
CREATE DATABASE IF NOT EXISTS chepochem_platform;
USE chepochem_platform;

-- Таблица ролей
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица пользователей
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    avatar_url TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    role_id INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Таблица профилей пользователей
CREATE TABLE user_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    bio TEXT,
    location VARCHAR(255),
    birth_date DATE,
    gender VARCHAR(20),
    website TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Таблица репутации пользователей
CREATE TABLE user_reputation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_score INT DEFAULT 0,
    positive_reviews INT DEFAULT 0,
    negative_reviews INT DEFAULT 0,
    neutral_reviews INT DEFAULT 0,
    reputation_level VARCHAR(20) DEFAULT 'newbie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Таблица отзывов
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reviewer_id INT NOT NULL,
    reviewed_user_id INT NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    is_positive BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Таблица категорий
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),
    parent_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- Таблица объявлений
CREATE TABLE listings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    `condition` VARCHAR(20) DEFAULT 'used',
    status VARCHAR(20) DEFAULT 'active',
    location VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_negotiable BOOLEAN DEFAULT TRUE,
    is_urgent BOOLEAN DEFAULT FALSE,
    views_count INT DEFAULT 0,
    favorites_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Таблица изображений объявлений
CREATE TABLE listing_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    alt_text VARCHAR(255),
    sort_order INT DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

-- Таблица избранных объявлений
CREATE TABLE user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    listing_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_listing (user_id, listing_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

-- Таблица жалоб
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reporter_id INT NOT NULL,
    reported_user_id INT,
    reported_listing_id INT,
    report_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    moderator_id INT,
    resolution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reported_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (reported_listing_id) REFERENCES listings(id) ON DELETE SET NULL,
    FOREIGN KEY (moderator_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Таблица модерации объявлений
CREATE TABLE listing_moderation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    moderator_id INT NOT NULL,
    action VARCHAR(20) NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (moderator_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Таблица уведомлений
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    related_entity_type VARCHAR(50),
    related_entity_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Таблица статистики пользователей
CREATE TABLE user_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    listings_count INT DEFAULT 0,
    sold_count INT DEFAULT 0,
    purchased_count INT DEFAULT 0,
    total_earnings DECIMAL(12,2) DEFAULT 0,
    total_spent DECIMAL(12,2) DEFAULT 0,
    response_rate DECIMAL(5,2) DEFAULT 0,
    average_response_time INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Вставка базовых данных
INSERT INTO roles (name, description) VALUES
('user', 'Обычный пользователь'),
('moderator', 'Модератор'),
('admin', 'Администратор');

INSERT INTO categories (name, slug, description, icon) VALUES
('Транспорт', 'transport', 'Автомобили, мотоциклы, велосипеды и запчасти', 'car'),
('Недвижимость', 'real-estate', 'Квартиры, дома, участки', 'home'),
('Работа', 'jobs', 'Вакансии и резюме', 'briefcase'),
('Услуги', 'services', 'Бытовые, профессиональные услуги', 'tools'),
('Личные вещи', 'personal', 'Одежда, обувь, аксессуары', 'user'),
('Для дома и дачи', 'home-garden', 'Мебель, техника, сад', 'home'),
('Хобби и отдых', 'hobby', 'Спорт, туризм, коллекционирование', 'heart'),
('Животные', 'animals', 'Питомцы, корм, аксессуары', 'paw'),
('Бизнес и оборудование', 'business', 'Оборудование, сырье, готовая продукция', 'briefcase'),
('Электроника', 'electronics', 'Телефоны, компьютеры, бытовая техника', 'smartphone');

INSERT INTO users (username, email, password_hash, first_name, last_name, phone, role_id) VALUES
('admin', 'admin@chepochem.ru', 'admin123', 'Админ', 'Админов', '+7-900-000-0001', 3),
('moderator', 'moderator@chepochem.ru', 'mod123', 'Модератор', 'Модераторов', '+7-900-000-0002', 2),
('ivan_petrov', 'ivan@example.com', 'user123', 'Иван', 'Петров', '+7-900-123-4567', 1),
('maria_sidorova', 'maria@example.com', 'user123', 'Мария', 'Сидорова', '+7-900-234-5678', 1);

INSERT INTO user_reputation (user_id) VALUES
(3), (4);

INSERT INTO listings (user_id, category_id, title, description, price, `condition`, location) VALUES
(3, 1, 'Toyota Camry 2018 года', 'Продаю Toyota Camry 2018 года. Машина в отличном состоянии, один владелец. Пробег 45 000 км.', 1800000.00, 'used', 'Москва'),
(4, 10, 'iPhone 13 Pro 128GB', 'Продаю iPhone 13 Pro 128GB в отличном состоянии. Батарея 100%, никаких царапин.', 65000.00, 'used', 'Санкт-Петербург');

INSERT INTO reviews (reviewer_id, reviewed_user_id, rating, comment, is_positive) VALUES
(4, 3, 5, 'Отличный продавец! Машина в идеальном состоянии.', true),
(3, 4, 4, 'Хороший покупатель, быстро договорились.', true);

UPDATE listings SET status = 'active', published_at = CURRENT_TIMESTAMP WHERE id IN (1, 2);

UPDATE user_reputation SET 
    total_score = 5,
    positive_reviews = 1,
    reputation_level = 'trusted'
WHERE user_id = 3;

UPDATE user_reputation SET 
    total_score = 4,
    positive_reviews = 1,
    reputation_level = 'trusted'
WHERE user_id = 4;
