-- ============================================================
-- TNEB Email Support Portal — MySQL Schema
-- Run this in MySQL before seeding:
--   mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS tneb_portal
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE tneb_portal;

-- ── employees ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employees (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    employee_id      VARCHAR(20)  NOT NULL UNIQUE,
    name             VARCHAR(120) NOT NULL,
    designation      VARCHAR(100) NOT NULL,
    department       VARCHAR(100) NOT NULL,
    office_location  VARCHAR(100) NOT NULL,
    district         VARCHAR(60)  NOT NULL,
    phone            VARCHAR(15),
    personal_email   VARCHAR(120),
    joined_date      DATE,
    is_active        TINYINT(1) DEFAULT 1,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee_id (employee_id),
    INDEX idx_district    (district),
    INDEX idx_designation (designation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── official_emails ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS official_emails (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    employee_id_fk   INT NOT NULL,
    email_address    VARCHAR(150) NOT NULL UNIQUE,
    designation      VARCHAR(100) NOT NULL,
    office           VARCHAR(100) NOT NULL,
    department       VARCHAR(100) NOT NULL,
    district         VARCHAR(60)  NOT NULL,
    is_active        TINYINT(1) DEFAULT 1,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id_fk) REFERENCES employees(id) ON DELETE CASCADE,
    INDEX idx_email_addr   (email_address),
    INDEX idx_designation  (designation),
    INDEX idx_district     (district)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── users ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    username         VARCHAR(80)  NOT NULL UNIQUE,
    email            VARCHAR(120) NOT NULL UNIQUE,
    password_hash    VARCHAR(256) NOT NULL,
    role             VARCHAR(20)  NOT NULL DEFAULT 'employee',
    employee_id_fk   INT,
    is_active        TINYINT(1) DEFAULT 1,
    last_login       DATETIME,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id_fk) REFERENCES employees(id) ON DELETE SET NULL,
    INDEX idx_username (username),
    INDEX idx_role     (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── support_tickets ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS support_tickets (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id        VARCHAR(20)  NOT NULL UNIQUE,
    employee_id_fk   INT NOT NULL,
    category         VARCHAR(60)  NOT NULL,
    subject          VARCHAR(200) NOT NULL,
    description      TEXT         NOT NULL,
    status           VARCHAR(30)  NOT NULL DEFAULT 'Pending',
    priority         VARCHAR(20)           DEFAULT 'Medium',
    assigned_to      INT,
    resolution_notes TEXT,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at      DATETIME,
    FOREIGN KEY (employee_id_fk) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to)    REFERENCES users(id)     ON DELETE SET NULL,
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_status    (status),
    INDEX idx_category  (category),
    INDEX idx_created   (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── password_reset_requests ────────────────────────────────
CREATE TABLE IF NOT EXISTS password_reset_requests (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    request_id       VARCHAR(20)  NOT NULL UNIQUE,
    employee_id_fk   INT NOT NULL,
    employee_name    VARCHAR(120) NOT NULL,
    designation      VARCHAR(100) NOT NULL,
    office_location  VARCHAR(100) NOT NULL,
    phone            VARCHAR(15)  NOT NULL,
    status           VARCHAR(30)           DEFAULT 'Pending',
    approved_by      INT,
    notes            TEXT,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at      DATETIME,
    FOREIGN KEY (employee_id_fk) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by)    REFERENCES users(id)     ON DELETE SET NULL,
    INDEX idx_request_id (request_id),
    INDEX idx_status     (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── chatbot_logs ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chatbot_logs (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    session_id       VARCHAR(60)  NOT NULL,
    user_id          INT,
    message_type     VARCHAR(10)  NOT NULL,
    message          TEXT         NOT NULL,
    intent           VARCHAR(60),
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_session  (session_id),
    INDEX idx_created  (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
