# Smart Waste Management System

A simple Flask-based web application for managing waste pickup requests.

## Setup Instructions

1. Create a MySQL database named `smart_waste_db`
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your database credentials:
   ```
   DB_HOST=localhost
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_NAME=smart_waste_db
   SECRET_KEY=your_secret_key
   ```
4. Run the application:
   ```
   python app.py
   ```

## Features

- User registration and login
- Worker login
- Request waste pickup
- Track pickup status
- Worker dashboard for managing pickups 