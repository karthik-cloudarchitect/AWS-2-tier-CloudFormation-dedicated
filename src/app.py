from flask import Flask, jsonify, request
import pymysql
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'admin')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'webappdb')
INSTANCE_ID = os.environ.get('INSTANCE_ID', 'unknown')

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        return connection
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise e

def init_database():
    """Initialize database tables if they don't exist"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Create logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    level VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    instance_id VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise e

def log_event(level: str, message: str):
    """Log event to database"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO logs (level, message, instance_id) VALUES (%s, %s, %s)",
                (level, message, INSTANCE_ID)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Logging error: {str(e)}")

@app.route('/')
def home():
    """Home endpoint"""
    log_event('INFO', 'Home endpoint accessed')
    return jsonify({
        'message': 'Welcome to Two-Tier Web Application',
        'status': 'healthy',
        'instance_id': INSTANCE_ID,
        'timestamp': datetime.utcnow().isoformat(),
        'database_host': DB_HOST
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        conn.close()
        log_event('INFO', 'Health check passed')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'instance_id': INSTANCE_ID,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        log_event('ERROR', f'Health check failed: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'database': str(e),
            'instance_id': INSTANCE_ID,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            users = cursor.fetchall()
        conn.close()
        
        log_event('INFO', f'Retrieved {len(users)} users')
        return jsonify({
            'users': users,
            'count': len(users),
            'instance_id': INSTANCE_ID
        })
    except Exception as e:
        log_event('ERROR', f'Error retrieving users: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name')
        email = data.get('email')
        
        if not name or not email:
            return jsonify({'error': 'Name and email are required'}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                (name, email)
            )
            user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_event('INFO', f'Created user: {name} ({email})')
        return jsonify({
            'message': 'User created successfully',
            'user_id': user_id,
            'instance_id': INSTANCE_ID
        }), 201
    except pymysql.err.IntegrityError as e:
        if "Duplicate entry" in str(e):
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        log_event('ERROR', f'Error creating user: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    """Get a specific user"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        log_event('INFO', f'Retrieved user: {user_id}')
        return jsonify({
            'user': user,
            'instance_id': INSTANCE_ID
        })
    except Exception as e:
        log_event('ERROR', f'Error retrieving user {user_id}: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id: int):
    """Update a user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name')
        email = data.get('email')
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET name = %s, email = %s WHERE id = %s",
                (name, email, user_id)
            )
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'error': 'User not found'}), 404
        conn.commit()
        conn.close()
        
        log_event('INFO', f'Updated user: {user_id}')
        return jsonify({
            'message': 'User updated successfully',
            'instance_id': INSTANCE_ID
        })
    except pymysql.err.IntegrityError as e:
        if "Duplicate entry" in str(e):
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        log_event('ERROR', f'Error updating user {user_id}: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id: int):
    """Delete a user"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'error': 'User not found'}), 404
        conn.commit()
        conn.close()
        
        log_event('INFO', f'Deleted user: {user_id}')
        return jsonify({
            'message': 'User deleted successfully',
            'instance_id': INSTANCE_ID
        })
    except Exception as e:
        log_event('ERROR', f'Error deleting user {user_id}: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """Get application logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        level = request.args.get('level')
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if level:
                cursor.execute(
                    "SELECT * FROM logs WHERE level = %s ORDER BY created_at DESC LIMIT %s",
                    (level, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM logs ORDER BY created_at DESC LIMIT %s",
                    (limit,)
                )
            logs = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'logs': logs,
            'count': len(logs),
            'instance_id': INSTANCE_ID
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/info')
def info():
    """Application information"""
    return jsonify({
        'application': 'Two-Tier Web Application',
        'version': '1.0.0',
        'instance_id': INSTANCE_ID,
        'database_host': DB_HOST,
        'database_name': DB_NAME,
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    # Initialize database on startup
    try:
        init_database()
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
    
    app.run(host='0.0.0.0', port=80, debug=False) 