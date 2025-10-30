-- Office Management System - MySQL Setup Script

-- Create database
CREATE DATABASE IF NOT EXISTS office_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE office_management;

-- Users table
CREATE TABLE IF NOT EXISTS user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    designation VARCHAR(100),
    probation_completed BOOLEAN DEFAULT FALSE,
    emp_number VARCHAR(20) UNIQUE,
    doj DATE,
    perm_address TEXT,
    curr_address TEXT,
    emerg_contact_name VARCHAR(100),
    emerg_contact_num VARCHAR(20),
    birth_date DATE,
    pan VARCHAR(20),
    aadhar VARCHAR(20),
    role ENUM('employee', 'supervisor', 'admin') DEFAULT 'employee',
    manager_id INT,
    department VARCHAR(100),
    team ENUM('corporate', 'production'),
    profile_picture VARCHAR(200),
    last_working_day DATE,
    salary FLOAT,
    comment TEXT,
    FOREIGN KEY (manager_id) REFERENCES user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    in_time TIME,
    out_time TIME,
    overtime FLOAT DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    INDEX idx_user_date (user_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Leave table
CREATE TABLE IF NOT EXISTS `leave` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    leave_type ENUM('casual', 'sick', 'earned', 'maternity', 'lop') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    reason TEXT,
    doctor_cert VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    INDEX idx_user_status (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Holiday table
CREATE TABLE IF NOT EXISTS holiday (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    name VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Document table
CREATE TABLE IF NOT EXISTS document (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    file_path VARCHAR(200) NOT NULL,
    name VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Salary Slip table
CREATE TABLE IF NOT EXISTS salary_slip (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    month INT NOT NULL,
    year INT NOT NULL,
    file_path VARCHAR(200) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    INDEX idx_user_month_year (user_id, month, year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Log table
CREATE TABLE IF NOT EXISTS log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL,
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Task table
CREATE TABLE IF NOT EXISTS task (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    assigned_to INT NOT NULL,
    assigned_by INT NOT NULL,
    status ENUM('pending', 'in_progress', 'completed', 'overdue') DEFAULT 'pending',
    progress INT DEFAULT 0,
    due_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES user(id) ON DELETE CASCADE,
    INDEX idx_assigned_to (assigned_to),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create default admin user (password: admin123)
INSERT INTO user (username, password_hash, full_name, role, designation)
VALUES ('admin', 'scrypt:32768:8:1$LJzmWl1zEUNYyG3j$0c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f3c8c8f1f', 'Administrator', 'admin', 'System Administrator')
ON DUPLICATE KEY UPDATE id=id;

SELECT 'Database setup complete!' AS message;
