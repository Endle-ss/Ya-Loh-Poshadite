CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    avatar_url TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    role_id INTEGER REFERENCES roles(id) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    location VARCHAR(255),
    birth_date DATE,
    gender VARCHAR(20),
    website TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_reputation (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    total_score INTEGER DEFAULT 0,
    positive_reviews INTEGER DEFAULT 0,
    negative_reviews INTEGER DEFAULT 0,
    neutral_reviews INTEGER DEFAULT 0,
    reputation_level VARCHAR(20) DEFAULT 'newbie',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    reviewer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    reviewed_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    is_positive BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),
    parent_id INTEGER REFERENCES categories(id),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    condition VARCHAR(20) DEFAULT 'used',
    status VARCHAR(20) DEFAULT 'active',
    location VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_negotiable BOOLEAN DEFAULT TRUE,
    is_urgent BOOLEAN DEFAULT FALSE,
    views_count INTEGER DEFAULT 0,
    favorites_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE listing_images (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    alt_text VARCHAR(255),
    sort_order INTEGER DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, listing_id)
);

CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    reporter_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    reported_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reported_listing_id INTEGER REFERENCES listings(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    moderator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE listing_moderation (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    moderator_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    related_entity_type VARCHAR(50),
    related_entity_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_statistics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    listings_count INTEGER DEFAULT 0,
    sold_count INTEGER DEFAULT 0,
    purchased_count INTEGER DEFAULT 0,
    total_earnings DECIMAL(12,2) DEFAULT 0,
    total_spent DECIMAL(12,2) DEFAULT 0,
    response_rate DECIMAL(5,2) DEFAULT 0,
    average_response_time INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
('admin', 'admin@chepochem.ru', 'admin123', 'Админ', 'Админов', '+7-900-000-0001', 6),
('moderator', 'moderator@chepochem.ru', 'mod123', 'Модератор', 'Модераторов', '+7-900-000-0002', 5),
('ivan_petrov', 'ivan@example.com', 'user123', 'Иван', 'Петров', '+7-900-123-4567', 4),
('maria_sidorova', 'maria@example.com', 'user123', 'Мария', 'Сидорова', '+7-900-234-5678', 4);

INSERT INTO user_reputation (user_id) VALUES
(3), (4);

INSERT INTO listings (user_id, category_id, title, description, price, condition, location) VALUES
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
WHERE user_id = 5;

UPDATE user_reputation SET 
    total_score = 4,
    positive_reviews = 1,
    reputation_level = 'trusted'
WHERE user_id = 6;
