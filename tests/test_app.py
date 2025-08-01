import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from src.app import app, get_db_connection, init_database, log_event

@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    with patch('src.app.get_db_connection') as mock_conn:
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.return_value = mock_connection
        yield mock_conn, mock_connection, mock_cursor

class TestFlaskApp:
    
    def test_home_endpoint(self, client):
        """Test the home endpoint"""
        with patch('src.app.log_event') as mock_log:
            response = client.get('/')
            data = json.loads(response.data)
            
            assert response.status_code == 200
            assert data['message'] == 'Welcome to Two-Tier Web Application'
            assert data['status'] == 'healthy'
            assert 'instance_id' in data
            assert 'timestamp' in data
            assert 'database_host' in data
            mock_log.assert_called_once_with('INFO', 'Home endpoint accessed')
    
    def test_health_endpoint_success(self, client, mock_db_connection):
        """Test health endpoint with successful database connection"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        
        with patch('src.app.log_event') as mock_log:
            response = client.get('/health')
            data = json.loads(response.data)
            
            assert response.status_code == 200
            assert data['status'] == 'healthy'
            assert data['database'] == 'connected'
            assert 'instance_id' in data
            assert 'timestamp' in data
            mock_log.assert_called_once_with('INFO', 'Health check passed')
    
    def test_health_endpoint_failure(self, client, mock_db_connection):
        """Test health endpoint with database connection failure"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_conn.side_effect = Exception("Database connection failed")
        
        with patch('src.app.log_event') as mock_log:
            response = client.get('/health')
            data = json.loads(response.data)
            
            assert response.status_code == 500
            assert data['status'] == 'unhealthy'
            assert 'Database connection failed' in data['database']
            mock_log.assert_called_once_with('ERROR', 'Health check failed: Database connection failed')
    
    def test_get_users_success(self, client, mock_db_connection):
        """Test getting users successfully"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_users = [
            {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
            {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com'}
        ]
        mock_cursor.fetchall.return_value = mock_users
        
        with patch('src.app.log_event') as mock_log:
            response = client.get('/users')
            data = json.loads(response.data)
            
            assert response.status_code == 200
            assert data['users'] == mock_users
            assert data['count'] == 2
            assert 'instance_id' in data
            mock_log.assert_called_once_with('INFO', 'Retrieved 2 users')
    
    def test_get_users_failure(self, client, mock_db_connection):
        """Test getting users with database error"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_conn.side_effect = Exception("Database error")
        
        with patch('src.app.log_event') as mock_log:
            response = client.get('/users')
            data = json.loads(response.data)
            
            assert response.status_code == 500
            assert 'error' in data
            mock_log.assert_called_once_with('ERROR', 'Error retrieving users: Database error')
    
    def test_create_user_success(self, client, mock_db_connection):
        """Test creating a user successfully"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_cursor.lastrowid = 1
        
        user_data = {'name': 'John Doe', 'email': 'john@example.com'}
        
        with patch('src.app.log_event') as mock_log:
            response = client.post('/users', 
                                data=json.dumps(user_data),
                                content_type='application/json')
            data = json.loads(response.data)
            
            assert response.status_code == 201
            assert data['message'] == 'User created successfully'
            assert data['user_id'] == 1
            assert 'instance_id' in data
            mock_log.assert_called_once_with('INFO', 'Created user: John Doe (john@example.com)')
    
    def test_create_user_missing_data(self, client):
        """Test creating user with missing data"""
        response = client.post('/users', 
                             data=json.dumps({'name': 'John Doe'}),
                             content_type='application/json')
        data = json.loads(response.data)
        
        assert response.status_code == 400
        assert 'error' in data
        assert 'Name and email are required' in data['error']
    
    def test_create_user_duplicate_email(self, client, mock_db_connection):
        """Test creating user with duplicate email"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_conn.side_effect = Exception("Duplicate entry")
        
        user_data = {'name': 'John Doe', 'email': 'john@example.com'}
        
        response = client.post('/users', 
                             data=json.dumps(user_data),
                             content_type='application/json')
        data = json.loads(response.data)
        
        assert response.status_code == 409
        assert 'error' in data
        assert 'Email already exists' in data['error']
    
    def test_get_user_success(self, client, mock_db_connection):
        """Test getting a specific user successfully"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_user = {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'}
        mock_cursor.fetchone.return_value = mock_user
        
        with patch('src.app.log_event') as mock_log:
            response = client.get('/users/1')
            data = json.loads(response.data)
            
            assert response.status_code == 200
            assert data['user'] == mock_user
            assert 'instance_id' in data
            mock_log.assert_called_once_with('INFO', 'Retrieved user: 1')
    
    def test_get_user_not_found(self, client, mock_db_connection):
        """Test getting a user that doesn't exist"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None
        
        response = client.get('/users/999')
        data = json.loads(response.data)
        
        assert response.status_code == 404
        assert 'error' in data
        assert 'User not found' in data['error']
    
    def test_update_user_success(self, client, mock_db_connection):
        """Test updating a user successfully"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_cursor.rowcount = 1
        
        user_data = {'name': 'John Updated', 'email': 'john.updated@example.com'}
        
        with patch('src.app.log_event') as mock_log:
            response = client.put('/users/1', 
                               data=json.dumps(user_data),
                               content_type='application/json')
            data = json.loads(response.data)
            
            assert response.status_code == 200
            assert data['message'] == 'User updated successfully'
            assert 'instance_id' in data
            mock_log.assert_called_once_with('INFO', 'Updated user: 1')
    
    def test_update_user_not_found(self, client, mock_db_connection):
        """Test updating a user that doesn't exist"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_cursor.rowcount = 0
        
        user_data = {'name': 'John Updated', 'email': 'john.updated@example.com'}
        
        response = client.put('/users/999', 
                           data=json.dumps(user_data),
                           content_type='application/json')
        data = json.loads(response.data)
        
        assert response.status_code == 404
        assert 'error' in data
        assert 'User not found' in data['error']
    
    def test_delete_user_success(self, client, mock_db_connection):
        """Test deleting a user successfully"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_cursor.rowcount = 1
        
        with patch('src.app.log_event') as mock_log:
            response = client.delete('/users/1')
            data = json.loads(response.data)
            
            assert response.status_code == 200
            assert data['message'] == 'User deleted successfully'
            assert 'instance_id' in data
            mock_log.assert_called_once_with('INFO', 'Deleted user: 1')
    
    def test_delete_user_not_found(self, client, mock_db_connection):
        """Test deleting a user that doesn't exist"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_cursor.rowcount = 0
        
        response = client.delete('/users/999')
        data = json.loads(response.data)
        
        assert response.status_code == 404
        assert 'error' in data
        assert 'User not found' in data['error']
    
    def test_get_logs_success(self, client, mock_db_connection):
        """Test getting logs successfully"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_logs = [
            {'id': 1, 'level': 'INFO', 'message': 'Test log', 'instance_id': 'test-instance'},
            {'id': 2, 'level': 'ERROR', 'message': 'Error log', 'instance_id': 'test-instance'}
        ]
        mock_cursor.fetchall.return_value = mock_logs
        
        response = client.get('/logs')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['logs'] == mock_logs
        assert data['count'] == 2
        assert 'instance_id' in data
    
    def test_get_logs_with_level_filter(self, client, mock_db_connection):
        """Test getting logs with level filter"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_logs = [
            {'id': 1, 'level': 'INFO', 'message': 'Test log', 'instance_id': 'test-instance'}
        ]
        mock_cursor.fetchall.return_value = mock_logs
        
        response = client.get('/logs?level=INFO')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['logs'] == mock_logs
        assert data['count'] == 1
    
    def test_info_endpoint(self, client):
        """Test the info endpoint"""
        response = client.get('/info')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['application'] == 'Two-Tier Web Application'
        assert data['version'] == '1.0.0'
        assert 'instance_id' in data
        assert 'database_host' in data
        assert 'database_name' in data
        assert 'timestamp' in data

class TestDatabaseFunctions:
    
    def test_get_db_connection_success(self):
        """Test successful database connection"""
        with patch('pymysql.connect') as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection
            
            connection = get_db_connection()
            
            assert connection == mock_connection
            mock_connect.assert_called_once()
    
    def test_get_db_connection_failure(self):
        """Test database connection failure"""
        with patch('pymysql.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception, match="Connection failed"):
                get_db_connection()
    
    def test_init_database_success(self, mock_db_connection):
        """Test successful database initialization"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        
        with patch('src.app.logger') as mock_logger:
            init_database()
            
            # Verify tables were created
            assert mock_cursor.execute.call_count == 2
            mock_connection.commit.assert_called_once()
            mock_connection.close.assert_called_once()
            mock_logger.info.assert_called_once_with("Database initialized successfully")
    
    def test_log_event_success(self, mock_db_connection):
        """Test successful event logging"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        
        log_event('INFO', 'Test message')
        
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()
        mock_connection.close.assert_called_once()
    
    def test_log_event_failure(self, mock_db_connection):
        """Test event logging failure"""
        mock_conn, mock_connection, mock_cursor = mock_db_connection
        mock_conn.side_effect = Exception("Logging failed")
        
        with patch('src.app.logger') as mock_logger:
            log_event('INFO', 'Test message')
            
            mock_logger.error.assert_called_once_with("Logging error: Logging failed") 