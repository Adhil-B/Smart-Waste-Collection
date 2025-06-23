from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from datetime import datetime
from config import DB_CONFIG, SECRET_KEY
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database connection function
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, is_worker=False):
        self.id = id
        self.username = username
        self.is_worker = is_worker

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check if user is a worker
    cursor.execute("SELECT * FROM workers WHERE id = %s", (user_id,))
    worker = cursor.fetchone()
    if worker:
        cursor.close()
        conn.close()
        return User(worker['id'], worker['username'], True)
    
    # Check if user is a regular user
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user:
        return User(user['id'], user['username'], False)
    return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        house_no = request.form['house_no']
        location_id = request.form['location_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password, full_name, house_no, location_id) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_password, full_name, house_no, location_id)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash('Username already exists!', 'error')
        finally:
            cursor.close()
            conn.close()
    
    # Get locations for the form
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM locations")
    locations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('register.html', locations=locations)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check users table first
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            # This is definitely a regular user
            user_obj = User(user['id'], user['username'], False)
            login_user(user_obj)
            flash('Login successful!', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        
        # If not found in users table or password doesn't match, check workers table
        cursor.execute("SELECT * FROM workers WHERE username = %s", (username,))
        worker = cursor.fetchone()
        
        if worker and check_password_hash(worker['password'], password):
            # This is definitely a worker
            user_obj = User(worker['id'], worker['username'], True)
            login_user(user_obj)
            flash('Login successful!', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        
        cursor.close()
        conn.close()
        flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if current_user.is_worker:
        # Worker dashboard
        cursor.execute("""
            SELECT pr.*, u.house_no, l.name as location_name
            FROM pickup_requests pr
            JOIN users u ON pr.user_id = u.id
            JOIN locations l ON u.location_id = l.id
            WHERE pr.status = 'pending'
            ORDER BY l.name, pr.priority DESC
        """)
        pending_requests = cursor.fetchall()
        
        cursor.execute("""
            SELECT pr.*, u.house_no, l.name as location_name
            FROM pickup_requests pr
            JOIN users u ON pr.user_id = u.id
            JOIN locations l ON u.location_id = l.id
            WHERE pr.worker_id = %s AND pr.status = 'completed'
            ORDER BY pr.completed_at DESC
        """, (current_user.id,))
        completed_requests = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return render_template('worker_dashboard.html', 
                             pending_requests=pending_requests,
                             completed_requests=completed_requests)
    else:
        # User dashboard
        cursor.execute("""
            SELECT u.*, l.name as location_name 
            FROM users u 
            JOIN locations l ON u.location_id = l.id 
            WHERE u.id = %s
        """, (current_user.id,))
        user = cursor.fetchone()
        
        cursor.execute("""
            SELECT * FROM pickup_requests 
            WHERE user_id = %s 
            ORDER BY requested_at DESC 
            LIMIT 5
        """, (current_user.id,))
        recent_requests = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return render_template('user_dashboard.html', 
                             user=user,
                             recent_requests=recent_requests)

@app.route('/request_pickup', methods=['GET', 'POST'])
@login_required
def request_pickup():
    if current_user.is_worker:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        priority = request.form['priority']
        time_str = request.form['preferred_time']
        instructions = request.form['instructions']
        
        # Combine today's date with the selected time
        today = datetime.now().date()
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        preferred_time = datetime.combine(today, time_obj)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pickup_requests (user_id, priority, preferred_time, instructions)
            VALUES (%s, %s, %s, %s)
        """, (current_user.id, priority, preferred_time, instructions))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Pickup request submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('request_pickup.html')

@app.route('/complete_pickup/<int:request_id>', methods=['POST'])
@login_required
def complete_pickup(request_id):
    if not current_user.is_worker:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE pickup_requests 
        SET status = 'completed', worker_id = %s, completed_at = NOW()
        WHERE id = %s AND status = 'pending'
    """, (current_user.id, request_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Pickup marked as completed!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if current_user.is_worker:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        house_no = request.form['house_no']
        location_id = request.form['location_id']
        
        cursor.execute("""
            UPDATE users 
            SET full_name = %s, house_no = %s, location_id = %s
            WHERE id = %s
        """, (full_name, house_no, location_id, current_user.id))
        
        conn.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    cursor.execute("SELECT * FROM users WHERE id = %s", (current_user.id,))
    user = cursor.fetchone()
    
    cursor.execute("SELECT * FROM locations")
    locations = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('edit_profile.html', user=user, locations=locations)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 