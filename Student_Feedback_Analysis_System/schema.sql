CREATE DATABASE IF NOT EXISTS student_feedback_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_feedback_db;
CREATE TABLE IF NOT EXISTS colleges(id INT AUTO_INCREMENT PRIMARY KEY,name VARCHAR(160) NOT NULL,active BOOLEAN DEFAULT TRUE);
CREATE TABLE IF NOT EXISTS campuses(id INT AUTO_INCREMENT PRIMARY KEY,college_id INT NOT NULL,name VARCHAR(160) NOT NULL,active BOOLEAN DEFAULT TRUE,FOREIGN KEY(college_id) REFERENCES colleges(id));
CREATE TABLE IF NOT EXISTS users(
 id INT AUTO_INCREMENT PRIMARY KEY,full_name VARCHAR(160) NOT NULL,email VARCHAR(190) NOT NULL UNIQUE,
 username VARCHAR(80) NOT NULL UNIQUE,department VARCHAR(120),password_hash VARCHAR(255) NOT NULL,
 role ENUM('student','faculty') NOT NULL DEFAULT 'student',college_id INT,campus_id INT,
 roll_no VARCHAR(60) UNIQUE,branch VARCHAR(80),year_level INT,section VARCHAR(30),created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(college_id) REFERENCES colleges(id),FOREIGN KEY(campus_id) REFERENCES campuses(id));
CREATE TABLE IF NOT EXISTS student_roster(
 id INT AUTO_INCREMENT PRIMARY KEY,roll_no VARCHAR(60) NOT NULL UNIQUE,college_id INT NOT NULL,campus_id INT NOT NULL,
 branch VARCHAR(80) NOT NULL,year_level INT NOT NULL,section VARCHAR(30) NOT NULL,active BOOLEAN DEFAULT TRUE,
 FOREIGN KEY(college_id) REFERENCES colleges(id),FOREIGN KEY(campus_id) REFERENCES campuses(id));
CREATE TABLE IF NOT EXISTS courses(
 id INT AUTO_INCREMENT PRIMARY KEY,name VARCHAR(160) NOT NULL,college_id INT NOT NULL,campus_id INT NOT NULL,
 faculty_id INT NULL,department VARCHAR(120),active BOOLEAN DEFAULT TRUE,
 FOREIGN KEY(college_id) REFERENCES colleges(id),FOREIGN KEY(campus_id) REFERENCES campuses(id),
 FOREIGN KEY(faculty_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS feedback(
 id INT AUTO_INCREMENT PRIMARY KEY,user_id INT,student_name VARCHAR(160),department VARCHAR(120),subject VARCHAR(160),
 course_id INT,faculty_id INT,college_id INT,campus_id INT,feedback_question VARCHAR(255),rating TINYINT NOT NULL,
 comments TEXT,sentiment ENUM('Positive','Neutral','Negative') NOT NULL,branch VARCHAR(80),year_level INT,section VARCHAR(30),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id),FOREIGN KEY(course_id) REFERENCES courses(id),
 FOREIGN KEY(faculty_id) REFERENCES users(id),FOREIGN KEY(college_id) REFERENCES colleges(id),
 FOREIGN KEY(campus_id) REFERENCES campuses(id),CHECK(rating BETWEEN 1 AND 5));
