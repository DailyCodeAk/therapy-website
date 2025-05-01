from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_from_directory
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime, timedelta
import uuid
import re
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from user_backend import user_bp
from admin_backend import init_admin
from flask_pymongo import PyMongo

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'holycow_therapy_secret_key')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/therapy_app")

# Initialize MongoDB
mongo = PyMongo(app)

# Setup bcrypt for password hashing
bcrypt = Bcrypt(app)

# Enable CORS
CORS(app)

# MongoDB connection
db = mongo.db

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Register blueprints
app.register_blueprint(user_bp)
init_admin(app, mongo)

@app.route('/')
def home():
    return render_template('website.html')

# Input validation functions
def validate_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_regex, email))

def validate_phone(phone):
    phone_regex = r'^\+?1?\d{9,15}$'
    return bool(re.match(phone_regex, phone))

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

def sanitize_input(data):
    # Remove any potential HTML/JavaScript
    if isinstance(data, str):
        return re.sub(r'<[^>]+>', '', data)
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    return data

# Security middleware
@app.before_request
def before_request():
    # Check for session timeout
    if 'user_id' in session:
        last_activity = session.get('last_activity')
        if last_activity:
            try:
                # Try to parse the ISO format string
                last_activity = datetime.strptime(last_activity, '%Y-%m-%dT%H:%M:%S.%f')
                if datetime.utcnow() - last_activity > timedelta(hours=1):
                    session.clear()
                    return redirect(url_for('login_page'))
            except ValueError:
                # If parsing fails, clear the session
                session.clear()
                return redirect(url_for('login_page'))
        session['last_activity'] = datetime.utcnow().isoformat()

# Authentication middleware
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Initialize database with default data
def init_db():
    # Only initialize if database is empty
    if db.therapists.count_documents({}) == 0:
        # Insert default therapists
        therapists = [
            {
                'name': 'Dr. Sarah Johnson',
                'title': 'Clinical Psychologist',
                'bio': 'Specializing in anxiety, depression, and trauma recovery with 15 years of experience.',
                'image_url': 'https://photos.psychologytoday.com/4fec5a21-46cd-11ea-a6ad-06142c356176/1/320x400.jpeg',
                'social_links': {
                    'psychology_today': 'https://www.psychologytoday.com/us/therapists/sarah-e-johnson-towson-md/81110'
                },
                'created_at': datetime.utcnow()
            },
            {
                'name': 'Michael Rodriguez, LMFT',
                'title': 'Marriage & Family Therapist',
                'bio': 'Expert in couples therapy, family dynamics, and relationship counseling.',
                'image_url': 'https://photos.psychologytoday.com/1a30b3ba-881b-4a8c-941e-211ebf31b30b/1/320x400.png',
                'social_links': {
                    'linkedin': 'https://www.linkedin.com/in/michael-rodriguez-42b866171',
                    'website': 'https://www.lifetocomecounseling.com/'
                },
                'created_at': datetime.utcnow()
            }
        ]
        db.therapists.insert_many(therapists)
        
        # Create admin user
        if db.users.count_documents({'role': 'admin'}) == 0:
            admin_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin_user = {
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@holycowtherapy.com',
                'password': admin_password,
                'role': 'admin',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            db.users.insert_one(admin_user)

# Initialize the database
init_db()

# User routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.form if request.form else request.json
    
    # Validate required fields
    required_fields = ['firstName', 'lastName', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400
    
    # Check if email already exists
    if db.users.find_one({'email': data['email']}):
        return jsonify({'status': 'error', 'message': 'Email already registered'}), 400
    
    # Validate email format
    if not validate_email(data['email']):
        return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400
    
    # Validate password strength
    is_valid, message = validate_password(data['password'])
    if not is_valid:
        return jsonify({'status': 'error', 'message': message}), 400
    
    # Hash the password
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    # Create user document
    user = {
        'first_name': data['firstName'],
        'last_name': data['lastName'],
        'email': data['email'],
        'password': hashed_password,
        'role': 'client',  # Default role
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'onboarding_completed': False
    }
    
    # Insert user into database
    result = db.users.insert_one(user)
    
    # Set session
    session['user_id'] = str(result.inserted_id)
    session['email'] = data['email']
    session['first_name'] = data['firstName']
    session['last_name'] = data['lastName']
    session['role'] = 'client'
    
    return jsonify({
        'status': 'success',
        'message': 'Registration successful',
        'user': {
            'id': str(result.inserted_id),
            'first_name': data['firstName'],
            'last_name': data['lastName'],
            'email': data['email'],
            'role': 'client'
        }
    })

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.form if request.form else request.json
        
        # Validate required fields
        if 'email' not in data or 'password' not in data:
            return render_template('login.html', error='Email and password are required')
        
        # Find user by email
        user = db.users.find_one({'email': data['email']})
        if not user:
            return render_template('login.html', error='Invalid email or password')
        
        # Check password
        if not bcrypt.check_password_hash(user['password'], data['password']):
            return render_template('login.html', error='Invalid email or password')
        
        # Set session
        session.clear()  # Clear any existing session
        session['user_id'] = str(user['_id'])
        session['email'] = user['email']
        session['first_name'] = user['first_name']
        session['last_name'] = user['last_name']
        session['role'] = user['role']
        
        # Ensure session is saved
        session.permanent = True
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Login error: {str(e)}")
        return render_template('login.html', error='An error occurred during login')

@app.route('/api/logout', methods=['GET', 'POST'])
def logout():
    # Store the previous page before clearing session
    previous_page = request.referrer
    session.clear()
    
    # Check if we're coming from userpage
    if previous_page and ('userpage' in previous_page or 'dashboard' in previous_page):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route('/logout', methods=['GET', 'POST'])
def logout_route():
    return redirect(url_for('logout'))

@app.route('/api/current_user', methods=['GET'])
@login_required
def current_user():
    user_id = session.get('user_id')
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        session.clear()
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    return jsonify({
        'status': 'success',
        'user': {
            'id': str(user['_id']),
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'email': user['email'],
            'role': user['role'],
            'onboarding_completed': user.get('onboarding_completed', False)
        }
    })

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's appointments
    user_id = session.get('user_id')
    appointments = list(db.appointments.find({
        'user_id': ObjectId(user_id),
        'date': {'$gte': datetime.utcnow()}
    }).sort('date', 1))

    # Get recent activity (appointments, messages, etc.)
    recent_activity = []
    
    # Add recent appointments to activity
    recent_appointments = list(db.appointments.find({
        'user_id': ObjectId(user_id)
    }).sort('created_at', -1).limit(5))
    
    for appointment in recent_appointments:
        recent_activity.append({
            'type': 'Appointment',
            'description': f"{appointment['service']} with {appointment['therapist']}",
            'date': appointment['created_at'].strftime('%Y-%m-%d %H:%M')
        })
    
    # Add recent messages to activity
    recent_messages = list(db.contact_messages.find({
        'email': session.get('email')
    }).sort('created_at', -1).limit(5))
    
    for message in recent_messages:
        recent_activity.append({
            'type': 'Message',
            'description': message['subject'],
            'date': message['created_at'].strftime('%Y-%m-%d %H:%M')
        })
    
    # Sort activities by date
    recent_activity.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('dashboard.html', 
                         appointments=appointments,
                         recent_activity=recent_activity)

@app.route('/userpage')
def userpage():
    return render_template('userpage.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# Start the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)