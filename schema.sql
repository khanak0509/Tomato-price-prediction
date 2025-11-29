
CREATE DATABASE IF NOT EXISTS tomato_db;
USE tomato_db;


CREATE TABLE markets_master (
    id INT PRIMARY KEY AUTO_INCREMENT,
    market_name VARCHAR(200) UNIQUE NOT NULL,
    district VARCHAR(100),
    state VARCHAR(50),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    market_type ENUM('APMC', 'Private', 'Mandi') DEFAULT 'APMC',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_location (state, district),
    INDEX idx_active (active)
);



CREATE TABLE tomato_prices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    market_name VARCHAR(200) NOT NULL,
    district VARCHAR(100),
    state VARCHAR(50) DEFAULT 'Uttar Pradesh',
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    price_per_quintal DECIMAL(10,2) ,
    volume_traded DECIMAL(10,2),
    year INT NOT NULL,
    month INT NOT NULL,
    week_number INT NOT NULL,
    data_source VARCHAR(50) DEFAULT 'Agmarknet',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_market_date (market_name, week_start_date),
    INDEX idx_date (week_start_date),
    INDEX idx_market (market_name),
    UNIQUE KEY unique_market_week (market_name, week_start_date)
);


CREATE TABLE price_predictions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    market_name VARCHAR(200) NOT NULL,
    crop_type VARCHAR(50) DEFAULT 'tomato',
    prediction_date DATE NOT NULL,
    target_date DATE NOT NULL,
    predicted_price DECIMAL(10,2) NOT NULL,
    confidence_score DECIMAL(5,4),
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20),
    horizon_days INT NOT NULL,
    actual_price DECIMAL(10,2),
    prediction_error DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_market_target (market_name, target_date),
    INDEX idx_prediction_date (prediction_date),
    INDEX idx_model (model_name, model_version)
);



CREATE TABLE model_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    evaluation_date DATE NOT NULL,
    test_samples INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_model_date (model_name, evaluation_date),
    UNIQUE KEY unique_model_metric (model_name, model_version, metric_type, evaluation_date)
);


