-- HH Jaba Juice - MySQL Schema
-- Run this in phpMyAdmin or MySQL console before starting the server
-- Connection: localhost, user: root, no password, database: hhjaba

-- CREATE DATABASE IF NOT EXISTS hhjaba CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE hhjaba;

-- 1. Users
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(191) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    credit_balance DECIMAL(10,2) DEFAULT 30000.00,
    role ENUM('user','admin','super_admin') DEFAULT 'user',
    accepted_terms TINYINT(1) DEFAULT 0,
    accepted_terms_at DATETIME,
    picture TEXT,
    active_role VARCHAR(20),
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_credit (credit_balance)
);

-- 2. User Sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    session_token TEXT NOT NULL,
    token_prefix VARCHAR(191) GENERATED ALWAYS AS (LEFT(session_token, 191)) STORED,
    impersonated_role VARCHAR(20),
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    UNIQUE INDEX idx_token_prefix (token_prefix),
    INDEX idx_user (user_id)
);

-- 3. Approved Email Domains
CREATE TABLE IF NOT EXISTS approved_domains (
    domain VARCHAR(191) PRIMARY KEY,
    is_active TINYINT(1) DEFAULT 1,
    added_by VARCHAR(255),
    disabled_by VARCHAR(255),
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    disabled_at DATETIME,
    INDEX idx_active (is_active)
);

-- 4. Admin Audit Log
CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id VARCHAR(50) PRIMARY KEY,
    actor_user_id VARCHAR(50) NOT NULL,
    actor_email VARCHAR(191),
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(191) NOT NULL,
    details JSON,
    created_at DATETIME NOT NULL,
    INDEX idx_actor (actor_user_id),
    INDEX idx_action (action),
    INDEX idx_target (target_type, target_id),
    INDEX idx_created (created_at)
);

-- 5. Products
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL DEFAULT 500.00,
    stock INT NOT NULL DEFAULT 0,
    active TINYINT(1) DEFAULT 1,
    color VARCHAR(20),
    image_url TEXT,
    last_manufacturing_date VARCHAR(50),
    last_batch_id VARCHAR(100),
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    INDEX idx_active (active)
);

-- 6. Orders  (items = JSON array of {product_name, quantity, price})
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(255),
    user_email VARCHAR(255),
    user_phone VARCHAR(20),
    items JSON NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_method ENUM('credit','mpesa') NOT NULL,
    mpesa_code VARCHAR(100),
    status ENUM('pending','fulfilled','cancelled','rejected') DEFAULT 'pending',
    verification_status ENUM('pending','verified','rejected') DEFAULT 'pending',
    receipt_url TEXT,
    cancellation_reason TEXT,
    cancelled_by VARCHAR(255),
    cancelled_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_payment (payment_method),
    INDEX idx_created (created_at)
);

-- 7. Credit Invoices  (line_items = JSON array)
CREATE TABLE IF NOT EXISTS credit_invoices (
    invoice_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(20),
    billing_period_start VARCHAR(30),
    billing_period_end VARCHAR(30),
    line_items JSON NOT NULL DEFAULT (JSON_ARRAY()),
    subtotal DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) DEFAULT 0,
    total_paid DECIMAL(10,2) DEFAULT 0,
    status ENUM('paid','partial','unpaid') DEFAULT 'unpaid',
    payment_type VARCHAR(20) DEFAULT 'credit',
    notes TEXT,
    created_at DATETIME NOT NULL,
    created_by VARCHAR(255),
    company_email VARCHAR(255),
    company_location VARCHAR(100),
    payment_method VARCHAR(50),
    payment_number VARCHAR(50),
    auto_generated TINYINT(1) DEFAULT 0,
    is_backlog TINYINT(1) DEFAULT 0,
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
);

-- 8. Manual Invoices
CREATE TABLE IF NOT EXISTS manual_invoices (
    invoice_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    customer_name VARCHAR(255),
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    payment_method VARCHAR(50),
    mpesa_code VARCHAR(100),
    product_name VARCHAR(255),
    quantity INT,
    status ENUM('pending','verified','rejected') DEFAULT 'pending',
    created_at DATETIME NOT NULL,
    INDEX idx_created (created_at)
);

-- 9. Payment Submissions / POP  (audit_trail = JSON array)
CREATE TABLE IF NOT EXISTS payment_submissions (
    pop_id VARCHAR(50) PRIMARY KEY,
    invoice_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(255),
    user_email VARCHAR(255),
    transaction_code VARCHAR(100),
    amount_paid DECIMAL(10,2),
    payment_method VARCHAR(50),
    payment_type VARCHAR(20),
    notes TEXT,
    status ENUM('pending','approved','verification_failed','rejected') DEFAULT 'pending',
    submitted_at DATETIME NOT NULL,
    verified_at DATETIME,
    verified_by VARCHAR(255),
    verified_amount DECIMAL(10,2),
    rejection_reason TEXT,
    admin_transaction_code VARCHAR(100),
    admin_amount DECIMAL(10,2),
    match_method VARCHAR(50),
    decline_reason TEXT,
    declined_at DATETIME,
    declined_by VARCHAR(255),
    force_approve_reason TEXT,
    audit_trail JSON,
    INDEX idx_user (user_id),
    INDEX idx_invoice (invoice_id),
    INDEX idx_status (status),
    INDEX idx_submitted (submitted_at)
);

-- 10. Dispute Messages
CREATE TABLE IF NOT EXISTS dispute_messages (
    message_id VARCHAR(50) PRIMARY KEY,
    pop_id VARCHAR(50) NOT NULL,
    invoice_id VARCHAR(50),
    sender_id VARCHAR(50) NOT NULL,
    sender_name VARCHAR(255),
    sender_role VARCHAR(20),
    message TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_pop (pop_id),
    INDEX idx_created (created_at)
);

-- 11. Feedback
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(255),
    user_email VARCHAR(255),
    subject VARCHAR(255),
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'new',
    created_at DATETIME NOT NULL,
    INDEX idx_created (created_at)
);

-- 12. Notifications  (metadata = JSON object)
CREATE TABLE IF NOT EXISTS notifications (
    notification_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    message TEXT,
    notification_type VARCHAR(50) DEFAULT 'general',
    `read` TINYINT(1) DEFAULT 0,
    created_at DATETIME NOT NULL,
    created_by VARCHAR(255),
    pop_id VARCHAR(50),
    metadata JSON,
    PRIMARY KEY (notification_id, user_id),
    INDEX idx_user (user_id),
    INDEX idx_read (`read`),
    INDEX idx_created (created_at)
);

-- 13. Stock Entries
CREATE TABLE IF NOT EXISTS stock_entries (
    entry_id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255),
    quantity_added INT,
    manufacturing_date VARCHAR(50),
    batch_id VARCHAR(100),
    created_at DATETIME NOT NULL,
    INDEX idx_product (product_id)
);
