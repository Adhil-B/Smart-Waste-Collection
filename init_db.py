import mysql.connector
from config import DB_CONFIG
from werkzeug.security import generate_password_hash

def init_database():
    # Connect to MySQL server
    conn = mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )
    cursor = conn.cursor()

    # Create database if it doesn't exist
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    cursor.execute(f"USE {DB_CONFIG['database']}")

    # Create tables
    tables = [
        """
        CREATE TABLE IF NOT EXISTS locations (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            house_no VARCHAR(50) NOT NULL,
            location_id INT,
            FOREIGN KEY (location_id) REFERENCES locations(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS workers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS pickup_requests (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            worker_id INT,
            status ENUM('pending', 'completed') DEFAULT 'pending',
            priority ENUM('urgent', 'soon') NOT NULL,
            preferred_time DATETIME NOT NULL,
            instructions TEXT,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (worker_id) REFERENCES workers(id)
        )
        """
    ]

    for table in tables:
        cursor.execute(table)

    locations = ['Downtown', 'Westside', 'Eastside', 'Northside', 'Southside']
    for location in locations:
        cursor.execute("INSERT IGNORE INTO locations (name) VALUES (%s)", (location,))

    # Insert a sample worker with hashed password
    worker_password = generate_password_hash('4321')
    cursor.execute("""
        INSERT IGNORE INTO workers (username, password, full_name)
        VALUES (%s, %s, %s)
    """, ('worker1', worker_password, 'John Worker'))

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    init_database()
    print("Database initialized successfully!") 