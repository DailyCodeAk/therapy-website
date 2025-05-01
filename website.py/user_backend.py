import json
import datetime
import bcrypt
import os
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, send_file
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson.objectid import ObjectId
from bson.json_util import dumps
from functools import wraps
import secrets
import string
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# Create Blueprint for user routes
user_bp = Blueprint('user', __name__)

# MongoDB connection
mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/therapy_app")
mongo = PyMongo()

# Custom JSON encoder for ObjectId and datetime
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, os.environ.get("JWT_SECRET_KEY", "YourJWTSecretKey456!"), algorithms=['HS256'])
            current_user = mongo.db.users.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except (jwt.InvalidTokenError, Exception) as e:
            return jsonify({'message': 'Invalid token!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# Authentication Routes
@user_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Check if required fields are provided
    required_fields = ['email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'{field} is required!'}), 400
    
    # Check if user already exists
    if mongo.db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'User already exists!'}), 400
    
    # Hash password
    hashed_password = generate_password_hash(data['password'])
    
    # Create new user
    new_user = {
        'email': data['email'],
        'password': hashed_password,
        'first_name': data['first_name'],
        'last_name': data['last_name'],
        'role': 'patient',  # Default role
        'created_at': datetime.utcnow(),
        'profile': {
            'phone': data.get('phone', ''),
            'dob': data.get('dob', ''),
            'gender': data.get('gender', ''),
            'address': data.get('address', ''),
            'city': data.get('city', ''),
            'state': data.get('state', ''),
            'zip': data.get('zip', ''),
            'emergency_contact': {
                'name': data.get('emergency_contact_name', ''),
                'phone': data.get('emergency_contact_phone', ''),
            },
        },
        'insurance': {
            'provider': '',
            'policy_number': '',
            'group_number': '',
            'plan_type': '',
            'policyholder': '',
            'relationship': '',
            'copay': 0,
            'deductible': 0,
            'deductible_met': 0,
            'out_of_pocket_max': 0,
            'out_of_pocket_met': 0,
        }
    }
    
    try:
        # Insert user to database
        result = mongo.db.users.insert_one(new_user)
        
        # Generate token
        token = jwt.encode({
            'user_id': str(result.inserted_id),
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, os.environ.get("JWT_SECRET_KEY", "YourJWTSecretKey456!"))
        
        return jsonify({
            'message': 'User registered successfully!',
            'token': token,
            'user': {
                'id': str(result.inserted_id),
                'email': data['email'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'role': 'patient'
            }
        }), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Check if email and password are provided
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Email and password are required!'}), 400
    
    # Find user by email
    user = mongo.db.users.find_one({'email': data['email']})
    
    # Check if user exists and password is correct
    if not user or not check_password_hash(user['password'], data['password']):
        return jsonify({'message': 'Invalid email or password!'}), 401
    
    # Generate token
    token = jwt.encode({
        'user_id': str(user['_id']),
        'exp': datetime.utcnow() + timedelta(hours=1)
    }, os.environ.get("JWT_SECRET_KEY", "YourJWTSecretKey456!"))
    
    return jsonify({
        'message': 'Login successful!',
        'token': token,
        'user': {
            'id': str(user['_id']),
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'role': user['role']
        }
    }), 200

@user_bp.route('/api/auth/reset-password', methods=['POST'])
@token_required
def reset_password(current_user):
    data = request.get_json()
    
    # Check if required fields are provided
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'message': 'Current password and new password are required!'}), 400
    
    # Check if current password is correct
    if not check_password_hash(current_user['password'], data['current_password']):
        return jsonify({'message': 'Current password is incorrect!'}), 401
    
    # Hash new password
    hashed_password = generate_password_hash(data['new_password'])
    
    # Update password in database
    mongo.db.users.update_one(
        {'_id': current_user['_id']},
        {'$set': {'password': hashed_password}}
    )
    
    return jsonify({'message': 'Password reset successfully!'}), 200

@user_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    
    # Check if email is provided
    if not data or not data.get('email'):
        return jsonify({'message': 'Email is required!'}), 400
    
    # Find user by email
    user = mongo.db.users.find_one({'email': data['email']})
    
    if not user:
        # For security reasons, don't reveal that the user doesn't exist
        return jsonify({'message': 'If your email is registered, you will receive a password reset link.'}), 200
    
    # Generate reset token
    reset_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    expiry = datetime.utcnow() + timedelta(hours=1)
    
    # Save reset token in database
    mongo.db.users.update_one(
        {'_id': user['_id']},
        {'$set': {
            'reset_token': reset_token,
            'reset_token_expires': expiry
        }}
    )
    
    # In a real application, send an email with the reset link
    # For this example, we'll just return the token
    reset_url = f"/reset-password?token={reset_token}"
    
    # In production, you would use a proper email service
    # send_reset_email(user['email'], reset_url)
    
    return jsonify({
        'message': 'Password reset link has been sent to your email.',
        'reset_url': reset_url  # Only for development, remove in production
    }), 200

@user_bp.route('/api/auth/verify-reset-token', methods=['POST'])
def verify_reset_token():
    data = request.get_json()
    
    # Check if token is provided
    if not data or not data.get('token'):
        return jsonify({'message': 'Reset token is required!'}), 400
    
    # Find user by reset token
    user = mongo.db.users.find_one({
        'reset_token': data['token'],
        'reset_token_expires': {'$gt': datetime.utcnow()}
    })
    
    if not user:
        return jsonify({'message': 'Invalid or expired reset token!'}), 400
    
    return jsonify({'message': 'Reset token is valid!'}), 200

@user_bp.route('/api/auth/reset-password-with-token', methods=['POST'])
def reset_password_with_token():
    data = request.get_json()
    
    # Check if required fields are provided
    if not data or not data.get('token') or not data.get('new_password'):
        return jsonify({'message': 'Reset token and new password are required!'}), 400
    
    # Find user by reset token
    user = mongo.db.users.find_one({
        'reset_token': data['token'],
        'reset_token_expires': {'$gt': datetime.utcnow()}
    })
    
    if not user:
        return jsonify({'message': 'Invalid or expired reset token!'}), 400
    
    # Hash new password
    hashed_password = generate_password_hash(data['new_password'])
    
    # Update password in database and remove reset token
    mongo.db.users.update_one(
        {'_id': user['_id']},
        {
            '$set': {'password': hashed_password},
            '$unset': {'reset_token': "", 'reset_token_expires': ""}
        }
    )
    
    return jsonify({'message': 'Password has been reset successfully!'}), 200

# User Profile Routes
@user_bp.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    # Remove sensitive information
    user_profile = {
        'id': str(current_user['_id']),
        'email': current_user['email'],
        'first_name': current_user['first_name'],
        'last_name': current_user['last_name'],
        'role': current_user['role'],
        'profile': current_user['profile'],
        'insurance': current_user['insurance'],
        'created_at': current_user['created_at']
    }
    
    return jsonify(user_profile), 200

@user_bp.route('/api/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    data = request.get_json()
    
    # Fields that can be updated
    allowed_fields = [
        'first_name', 'last_name', 'email',
        'profile.phone', 'profile.dob', 'profile.gender',
        'profile.address', 'profile.city', 'profile.state', 'profile.zip',
        'profile.emergency_contact.name', 'profile.emergency_contact.phone'
    ]
    
    update_data = {}
    
    # Build update data from allowed fields
    for field in allowed_fields:
        parts = field.split('.')
        
        if len(parts) == 1 and parts[0] in data:
            update_data[parts[0]] = data[parts[0]]
        elif len(parts) == 2 and parts[0] in data and parts[1] in data[parts[0]]:
            if parts[0] not in update_data:
                update_data[parts[0]] = {}
            update_data[parts[0]][parts[1]] = data[parts[0]][parts[1]]
        elif len(parts) == 3 and parts[0] in data and parts[1] in data[parts[0]] and parts[2] in data[parts[0]][parts[1]]:
            if parts[0] not in update_data:
                update_data[parts[0]] = {}
            if parts[1] not in update_data[parts[0]]:
                update_data[parts[0]][parts[1]] = {}
            update_data[parts[0]][parts[1]][parts[2]] = data[parts[0]][parts[1]][parts[2]]
    
    # Convert nested dict to dot notation for MongoDB update
    flat_update = {}
    for key, value in update_data.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, dict):
                    for subsubkey, subsubvalue in subvalue.items():
                        flat_update[f"{key}.{subkey}.{subsubkey}"] = subsubvalue
                else:
                    flat_update[f"{key}.{subkey}"] = subvalue
        else:
            flat_update[key] = value
    
    try:
        # Update user profile
        mongo.db.users.update_one(
            {'_id': current_user['_id']},
            {'$set': flat_update}
        )
        
        return jsonify({'message': 'Profile updated successfully!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/profile/insurance', methods=['PUT'])
@token_required
def update_insurance(current_user):
    data = request.get_json()
    
    # Fields that can be updated
    allowed_fields = [
        'provider', 'policy_number', 'group_number', 'plan_type',
        'policyholder', 'relationship', 'copay', 'deductible',
        'deductible_met', 'out_of_pocket_max', 'out_of_pocket_met'
    ]
    
    update_data = {}
    
    # Build update data from allowed fields
    for field in allowed_fields:
        if field in data:
            update_data[f"insurance.{field}"] = data[field]
    
    try:
        # Update insurance information
        mongo.db.users.update_one(
            {'_id': current_user['_id']},
            {'$set': update_data}
        )
        
        return jsonify({'message': 'Insurance information updated successfully!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Therapist Search Routes
@user_bp.route('/api/therapists', methods=['GET'])
@token_required
def get_therapists(current_user):
    # Parse query parameters
    query = {}
    
    # Search by name
    name = request.args.get('name')
    if name:
        query['$or'] = [
            {'first_name': {'$regex': name, '$options': 'i'}},
            {'last_name': {'$regex': name, '$options': 'i'}}
        ]
    
    # Filter by specialty
    specialty = request.args.get('specialty')
    if specialty:
        query['therapist_profile.specialties'] = specialty
    
    # Only get users with role 'therapist'
    query['role'] = 'therapist'
    
    # Pagination
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    skip = (page - 1) * per_page
    
    try:
        # Get therapists
        therapists_cursor = mongo.db.users.find(
            query,
            {
                'password': 0,
                'reset_token': 0,
                'reset_token_expires': 0
            }
        ).skip(skip).limit(per_page)
        
        # Convert cursor to list
        therapists = list(therapists_cursor)
        
        # Count total therapists
        total = mongo.db.users.count_documents(query)
        
        # Format response
        formatted_therapists = []
        for therapist in therapists:
            therapist_data = {
                'id': str(therapist['_id']),
                'first_name': therapist['first_name'],
                'last_name': therapist['last_name'],
                'profile': therapist.get('therapist_profile', {}),
                'rating': therapist.get('rating', {
                    'average': 0,
                    'count': 0
                })
            }
            formatted_therapists.append(therapist_data)
        
        return jsonify({
            'therapists': formatted_therapists,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/therapists/<therapist_id>', methods=['GET'])
@token_required
def get_therapist(current_user, therapist_id):
    try:
        # Find therapist by ID
        therapist = mongo.db.users.find_one(
            {'_id': ObjectId(therapist_id), 'role': 'therapist'},
            {
                'password': 0,
                'reset_token': 0,
                'reset_token_expires': 0
            }
        )
        
        if not therapist:
            return jsonify({'message': 'Therapist not found!'}), 404
        
        # Format response
        therapist_data = {
            'id': str(therapist['_id']),
            'first_name': therapist['first_name'],
            'last_name': therapist['last_name'],
            'email': therapist['email'],
            'profile': therapist.get('therapist_profile', {}),
            'rating': therapist.get('rating', {
                'average': 0,
                'count': 0
            }),
            'schedule': therapist.get('schedule', {})
        }
        
        return jsonify(therapist_data), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Goals Management Routes
@user_bp.route('/api/goals', methods=['GET'])
@token_required
def get_goals(current_user):
    try:
        # Get all goals for the current user
        goals_cursor = mongo.db.goals.find({'user_id': str(current_user['_id'])})
        goals = list(goals_cursor)
        
        # Format goals
        formatted_goals = []
        for goal in goals:
            goal['id'] = str(goal.pop('_id'))
            formatted_goals.append(goal)
        
        return jsonify(formatted_goals), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/goals', methods=['POST'])
@token_required
def create_goal(current_user):
    data = request.get_json()
    
    # Check if required fields are provided
    required_fields = ['title', 'description', 'type', 'target_date']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'{field} is required!'}), 400
    
    # Create new goal
    new_goal = {
        'user_id': str(current_user['_id']),
        'title': data['title'],
        'description': data['description'],
        'type': data['type'],
        'target_date': data['target_date'],
        'created_at': datetime.utcnow(),
        'status': 'active',
        'progress': 0,
        'progress_history': [],
        'reminders': data.get('reminders', False)
    }
    
    try:
        # Insert goal to database
        result = mongo.db.goals.insert_one(new_goal)
        
        # Return the created goal
        new_goal['id'] = str(result.inserted_id)
        del new_goal['_id']
        
        return jsonify(new_goal), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/goals/<goal_id>', methods=['GET'])
@token_required
def get_goal(current_user, goal_id):
    try:
        # Find goal by ID and user ID
        goal = mongo.db.goals.find_one({
            '_id': ObjectId(goal_id),
            'user_id': str(current_user['_id'])
        })
        
        if not goal:
            return jsonify({'message': 'Goal not found!'}), 404
        
        # Format goal
        goal['id'] = str(goal.pop('_id'))
        
        return jsonify(goal), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/goals/<goal_id>', methods=['PUT'])
@token_required
def update_goal(current_user, goal_id):
    data = request.get_json()
    
    # Fields that can be updated
    allowed_fields = ['title', 'description', 'type', 'target_date', 'status', 'reminders']
    
    update_data = {}
    
    # Build update data from allowed fields
    for field in allowed_fields:
        if field in data:
            update_data[field] = data[field]
    
    try:
        # Update goal
        result = mongo.db.goals.update_one(
            {'_id': ObjectId(goal_id), 'user_id': str(current_user['_id'])},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'message': 'Goal not found!'}), 404
        
        # Get updated goal
        updated_goal = mongo.db.goals.find_one({
            '_id': ObjectId(goal_id),
            'user_id': str(current_user['_id'])
        })
        
        # Format goal
        updated_goal['id'] = str(updated_goal.pop('_id'))
        
        return jsonify(updated_goal), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/goals/<goal_id>/progress', methods=['POST'])
@token_required
def update_goal_progress(current_user, goal_id):
    data = request.get_json()
    
    # Check if progress is provided
    if 'progress' not in data:
        return jsonify({'message': 'Progress is required!'}), 400
    
    progress = data['progress']
    
    # Validate progress
    if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
        return jsonify({'message': 'Progress must be a number between 0 and 100!'}), 400
    
    try:
        # Update goal progress
        result = mongo.db.goals.update_one(
            {'_id': ObjectId(goal_id), 'user_id': str(current_user['_id'])},
            {
                '$set': {'progress': progress},
                '$push': {
                    'progress_history': {
                        'progress': progress,
                        'date': datetime.utcnow(),
                        'note': data.get('note', '')
                    }
                }
            }
        )
        
        if result.matched_count == 0:
            return jsonify({'message': 'Goal not found!'}), 404
        
        # Check if goal is completed
        if progress == 100:
            mongo.db.goals.update_one(
                {'_id': ObjectId(goal_id), 'user_id': str(current_user['_id'])},
                {'$set': {'status': 'completed'}}
            )
        
        return jsonify({'message': 'Goal progress updated successfully!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/goals/<goal_id>', methods=['DELETE'])
@token_required
def delete_goal(current_user, goal_id):
    try:
        # Delete goal
        result = mongo.db.goals.delete_one({
            '_id': ObjectId(goal_id),
            'user_id': str(current_user['_id'])
        })
        
        if result.deleted_count == 0:
            return jsonify({'message': 'Goal not found!'}), 404
        
        return jsonify({'message': 'Goal deleted successfully!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Appointment Management Routes
@user_bp.route('/api/appointments', methods=['GET'])
@token_required
def get_appointments(current_user):
    try:
        # Get all appointments for the current user
        appointments_cursor = mongo.db.appointments.find({'patient_id': str(current_user['_id'])})
        appointments = list(appointments_cursor)
        
        # Format appointments
        formatted_appointments = []
        for appointment in appointments:
            appointment['id'] = str(appointment.pop('_id'))
            
            # Get therapist details
            therapist = mongo.db.users.find_one(
                {'_id': ObjectId(appointment['therapist_id'])},
                {'first_name': 1, 'last_name': 1}
            )
            
            if therapist:
                appointment['therapist'] = {
                    'id': str(therapist['_id']),
                    'first_name': therapist['first_name'],
                    'last_name': therapist['last_name']
                }
            
            formatted_appointments.append(appointment)
        
        return jsonify(formatted_appointments), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/appointments', methods=['POST'])
@token_required
def create_appointment(current_user):
    data = request.get_json()
    
    # Check if required fields are provided
    required_fields = ['therapist_id', 'date', 'start_time', 'end_time', 'type']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'{field} is required!'}), 400
    
    # Create new appointment
    new_appointment = {
        'patient_id': str(current_user['_id']),
        'therapist_id': data['therapist_id'],
        'date': data['date'],
        'start_time': data['start_time'],
        'end_time': data['end_time'],
        'type': data['type'],  # 'video', 'in-person', etc.
        'location': data.get('location', ''),
        'notes': data.get('notes', ''),
        'created_at': datetime.utcnow(),
        'status': 'scheduled'
    }
    
    try:
        # Check if therapist exists
        therapist = mongo.db.users.find_one({
            '_id': ObjectId(data['therapist_id']),
            'role': 'therapist'
        })
        
        if not therapist:
            return jsonify({'message': 'Therapist not found!'}), 404
        
        # Check if therapist is available at the requested time
        # This would be a more complex check in a real application
        
        # Insert appointment to database
        result = mongo.db.appointments.insert_one(new_appointment)
        
        # Return the created appointment
        new_appointment['id'] = str(result.inserted_id)
        del new_appointment['_id']
        
        # Add therapist details
        new_appointment['therapist'] = {
            'id': data['therapist_id'],
            'first_name': therapist['first_name'],
            'last_name': therapist['last_name']
        }
        
        return jsonify(new_appointment), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/appointments/<appointment_id>', methods=['GET'])
@token_required
def get_appointment(current_user, appointment_id):
    try:
        # Find appointment by ID and user ID
        appointment = mongo.db.appointments.find_one({
            '_id': ObjectId(appointment_id),
            'patient_id': str(current_user['_id'])
        })
        
        if not appointment:
            return jsonify({'message': 'Appointment not found!'}), 404
        
        # Format appointment
        appointment['id'] = str(appointment.pop('_id'))
        
        # Get therapist details
        therapist = mongo.db.users.find_one(
            {'_id': ObjectId(appointment['therapist_id'])},
            {'first_name': 1, 'last_name': 1}
        )
        
        if therapist:
            appointment['therapist'] = {
                'id': str(therapist['_id']),
                'first_name': therapist['first_name'],
                'last_name': therapist['last_name']
            }
        
        return jsonify(appointment), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/appointments/<appointment_id>', methods=['PUT'])
@token_required
def update_appointment(current_user, appointment_id):
    data = request.get_json()
    
    # Fields that can be updated
    allowed_fields = ['date', 'start_time', 'end_time', 'type', 'location', 'notes', 'status']
    
    update_data = {}
    
    # Build update data from allowed fields
    for field in allowed_fields:
        if field in data:
            update_data[field] = data[field]
    
    try:
        # Update appointment
        result = mongo.db.appointments.update_one(
            {'_id': ObjectId(appointment_id), 'patient_id': str(current_user['_id'])},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'message': 'Appointment not found!'}), 404
        
        # Get updated appointment
        updated_appointment = mongo.db.appointments.find_one({
            '_id': ObjectId(appointment_id),
            'patient_id': str(current_user['_id'])
        })
        
        # Format appointment
        updated_appointment['id'] = str(updated_appointment.pop('_id'))
        
        # Get therapist details
        therapist = mongo.db.users.find_one(
            {'_id': ObjectId(updated_appointment['therapist_id'])},
            {'first_name': 1, 'last_name': 1}
        )
        
        if therapist:
            updated_appointment['therapist'] = {
                'id': str(therapist['_id']),
                'first_name': therapist['first_name'],
                'last_name': therapist['last_name']
            }
        
        return jsonify(updated_appointment), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/appointments/<appointment_id>', methods=['DELETE'])
@token_required
def delete_appointment(current_user, appointment_id):
    try:
        # Delete appointment
        result = mongo.db.appointments.delete_one({
            '_id': ObjectId(appointment_id),
            'patient_id': str(current_user['_id'])
        })
        
        if result.deleted_count == 0:
            return jsonify({'message': 'Appointment not found!'}), 404
        
        return jsonify({'message': 'Appointment deleted successfully!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Calendar Routes
@user_bp.route('/api/calendar', methods=['GET'])
@token_required
def get_calendar(current_user):
    try:
        # Get all appointments for the current user
        appointments_cursor = mongo.db.appointments.find({'patient_id': str(current_user['_id'])})
        appointments = list(appointments_cursor)
        
        # Format appointments for calendar
        calendar_events = []
        for appointment in appointments:
            therapist = mongo.db.users.find_one(
                {'_id': ObjectId(appointment['therapist_id'])},
                {'first_name': 1, 'last_name': 1}
            )
            
            therapist_name = "Unknown"
            if therapist:
                therapist_name = f"Dr. {therapist['first_name']} {therapist['last_name']}"
            
            calendar_events.append({
                'id': str(appointment['_id']),
                'title': f"Therapy Session with {therapist_name}",
                'date': appointment['date'],
                'start_time': appointment['start_time'],
                'end_time': appointment['end_time'],
                'type': appointment['type'],
                'location': appointment.get('location', ''),
                'status': appointment.get('status', 'scheduled'),
                'color': 'green' if appointment['type'] == 'video' else 'blue'
            })
        
        return jsonify(calendar_events), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/calendar/month/<year>/<month>', methods=['GET'])
@token_required
def get_month_calendar(current_user, year, month):
    try:
        # Convert year and month to integers
        year = int(year)
        month = int(month)
        
        # Validate year and month
        if not (1900 <= year <= 2100) or not (1 <= month <= 12):
            return jsonify({'message': 'Invalid year or month!'}), 400
        
        # Start and end dates for the month (including padding days)
        start_date = f"{year}-{month:02d}-01"
        
        # Calculate end date (last day of month)
        if month == 12:
            end_year = year + 1
            end_month = 1
        else:
            end_year = year
            end_month = month + 1
        
        end_date = f"{end_year}-{end_month:02d}-01"
        
        # Get all appointments for the current user in the given month
        appointments_cursor = mongo.db.appointments.find({
            'patient_id': str(current_user['_id']),
            'date': {'$gte': start_date, '$lt': end_date}
        })
        
        appointments = list(appointments_cursor)
        
        # Format appointments for calendar
        calendar_events = []
        for appointment in appointments:
            therapist = mongo.db.users.find_one(
                {'_id': ObjectId(appointment['therapist_id'])},
                {'first_name': 1, 'last_name': 1}
            )
            
            therapist_name = "Unknown"
            if therapist:
                therapist_name = f"Dr. {therapist['first_name']} {therapist['last_name']}"
            
            calendar_events.append({
                'id': str(appointment['_id']),
                'title': f"Therapy Session with {therapist_name}",
                'date': appointment['date'],
                'start_time': appointment['start_time'],
                'end_time': appointment['end_time'],
                'type': appointment['type'],
                'location': appointment.get('location', ''),
                'status': appointment.get('status', 'scheduled'),
                'color': 'green' if appointment['type'] == 'video' else 'blue'
            })
        
        return jsonify(calendar_events), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Billing and Payment Routes
@user_bp.route('/api/billing/invoices', methods=['GET'])
@token_required
def get_invoices(current_user):
    try:
        # Get all invoices for the current user
        invoices_cursor = mongo.db.invoices.find({'user_id': str(current_user['_id'])})
        invoices = list(invoices_cursor)
        
        # Format invoices
        formatted_invoices = []
        for invoice in invoices:
            invoice['id'] = str(invoice.pop('_id'))
            formatted_invoices.append(invoice)
        
        return jsonify(formatted_invoices), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/billing/invoices/<invoice_id>', methods=['GET'])
@token_required
def get_invoice(current_user, invoice_id):
    try:
        # Find invoice by ID and user ID
        invoice = mongo.db.invoices.find_one({
            '_id': ObjectId(invoice_id),
            'user_id': str(current_user['_id'])
        })
        
        if not invoice:
            return jsonify({'message': 'Invoice not found!'}), 404
        
        # Format invoice
        invoice['id'] = str(invoice.pop('_id'))
        
        return jsonify(invoice), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/billing/payment-methods', methods=['GET'])
@token_required
def get_payment_methods(current_user):
    try:
        # Get all payment methods for the current user
        payment_methods_cursor = mongo.db.payment_methods.find({
            'user_id': str(current_user['_id'])
        })
        
        payment_methods = list(payment_methods_cursor)
        
        # Format payment methods
        formatted_payment_methods = []
        for method in payment_methods:
            method['id'] = str(method.pop('_id'))
            formatted_payment_methods.append(method)
        
        return jsonify(formatted_payment_methods), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/billing/payment-methods', methods=['POST'])
@token_required
def add_payment_method(current_user):
    data = request.get_json()
    
    # Check if required fields are provided
    required_fields = ['type', 'card_number', 'expiry_month', 'expiry_year', 'cardholder_name']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'{field} is required!'}), 400
    
    # In a real application, you would use a payment processor API
    # For this example, we'll just store the payment method details
    # WARNING: This is not secure and should not be used in production
    
    # Create new payment method
    new_payment_method = {
        'user_id': str(current_user['_id']),
        'type': data['type'],
        'card_number': data['card_number'][-4:],  # Only store last 4 digits
        'expiry_month': data['expiry_month'],
        'expiry_year': data['expiry_year'],
        'cardholder_name': data['cardholder_name'],
        'created_at': datetime.utcnow(),
        'is_default': data.get('is_default', False)
    }
    
    try:
        # If this is set as default, unset any existing default
        if new_payment_method['is_default']:
            mongo.db.payment_methods.update_many(
                {'user_id': str(current_user['_id']), 'is_default': True},
                {'$set': {'is_default': False}}
            )
        
        # Insert payment method to database
        result = mongo.db.payment_methods.insert_one(new_payment_method)
        
        # Return the created payment method
        new_payment_method['id'] = str(result.inserted_id)
        del new_payment_method['_id']
        
        return jsonify(new_payment_method), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/billing/payment-methods/<method_id>', methods=['DELETE'])
@token_required
def delete_payment_method(current_user, method_id):
    try:
        # Delete payment method
        result = mongo.db.payment_methods.delete_one({
            '_id': ObjectId(method_id),
            'user_id': str(current_user['_id'])
        })
        
        if result.deleted_count == 0:
            return jsonify({'message': 'Payment method not found!'}), 404
        
        return jsonify({'message': 'Payment method deleted successfully!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/billing/payment-methods/<method_id>/set-default', methods=['PUT'])
@token_required
def set_default_payment_method(current_user, method_id):
    try:
        # Check if payment method exists
        payment_method = mongo.db.payment_methods.find_one({
            '_id': ObjectId(method_id),
            'user_id': str(current_user['_id'])
        })
        
        if not payment_method:
            return jsonify({'message': 'Payment method not found!'}), 404
        
        # Unset any existing default
        mongo.db.payment_methods.update_many(
            {'user_id': str(current_user['_id']), 'is_default': True},
            {'$set': {'is_default': False}}
        )
        
        # Set this one as default
        mongo.db.payment_methods.update_one(
            {'_id': ObjectId(method_id)},
            {'$set': {'is_default': True}}
        )
        
        return jsonify({'message': 'Default payment method updated successfully!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/billing/subscription', methods=['GET'])
@token_required
def get_subscription(current_user):
    try:
        # Get subscription for the current user
        subscription = mongo.db.subscriptions.find_one({
            'user_id': str(current_user['_id'])
        })
        
        if not subscription:
            return jsonify({'message': 'No active subscription found!'}), 404
        
        # Format subscription
        subscription['id'] = str(subscription.pop('_id'))
        
        return jsonify(subscription), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Chat and Support Routes
@user_bp.route('/api/chat/history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    try:
        # Get chat history for the current user
        messages_cursor = mongo.db.chat_messages.find({
            'user_id': str(current_user['_id'])
        }).sort('timestamp', 1)  # Sort by timestamp ascending
        
        messages = list(messages_cursor)
        
        # Format messages
        formatted_messages = []
        for message in messages:
            message['id'] = str(message.pop('_id'))
            formatted_messages.append(message)
        
        return jsonify(formatted_messages), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/chat/send', methods=['POST'])
@token_required
def send_chat_message(current_user):
    data = request.get_json()
    
    # Check if message content is provided
    if 'content' not in data:
        return jsonify({'message': 'Message content is required!'}), 400
    
    # Create new message
    new_message = {
        'user_id': str(current_user['_id']),
        'content': data['content'],
        'sender': 'user',  # 'user' or 'bot'
        'timestamp': datetime.utcnow(),
        'read': False
    }
    
    try:
        # Insert message to database
        result = mongo.db.chat_messages.insert_one(new_message)
        
        # Return the created message
        new_message['id'] = str(result.inserted_id)
        del new_message['_id']
        
        # In a real application, you would process the message
        # and generate a response from the chatbot
        # For this example, we'll create a simple automatic response
        
        bot_response = {
            'user_id': str(current_user['_id']),
            'content': "I'm an automated response. In a real application, this would be a more sophisticated chatbot response.",
            'sender': 'bot',
            'timestamp': datetime.utcnow(),
            'read': False
        }
        
        # Insert bot response to database
        bot_result = mongo.db.chat_messages.insert_one(bot_response)
        
        # Format bot response
        bot_response['id'] = str(bot_result.inserted_id)
        del bot_response['_id']
        
        return jsonify({
            'user_message': new_message,
            'bot_response': bot_response
        }), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/support/tickets', methods=['GET'])
@token_required
def get_support_tickets(current_user):
    try:
        # Get all support tickets for the current user
        tickets_cursor = mongo.db.support_tickets.find({
            'user_id': str(current_user['_id'])
        }).sort('created_at', -1)  # Sort by creation date descending
        
        tickets = list(tickets_cursor)
        
        # Format tickets
        formatted_tickets = []
        for ticket in tickets:
            ticket['id'] = str(ticket.pop('_id'))
            formatted_tickets.append(ticket)
        
        return jsonify(formatted_tickets), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/support/tickets', methods=['POST'])
@token_required
def create_support_ticket(current_user):
    data = request.get_json()
    
    # Check if required fields are provided
    required_fields = ['category', 'subject', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'{field} is required!'}), 400
    
    # Create new support ticket
    new_ticket = {
        'user_id': str(current_user['_id']),
        'ticket_number': f"#{datetime.now().strftime('%Y%m%d')}-{str(ObjectId())[-6:]}",
        'category': data['category'],
        'subject': data['subject'],
        'description': data['description'],
        'priority': data.get('priority', 'medium'),
        'status': 'open',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'messages': [
            {
                'sender': 'user',
                'sender_name': f"{current_user['first_name']} {current_user['last_name']}",
                'content': data['description'],
                'timestamp': datetime.utcnow()
            }
        ]
    }
    
    try:
        # Insert ticket to database
        result = mongo.db.support_tickets.insert_one(new_ticket)
        
        # Return the created ticket
        new_ticket['id'] = str(result.inserted_id)
        del new_ticket['_id']
        
        return jsonify(new_ticket), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/support/tickets/<ticket_id>', methods=['GET'])
@token_required
def get_support_ticket(current_user, ticket_id):
    try:
        # Find ticket by ID and user ID
        ticket = mongo.db.support_tickets.find_one({
            '_id': ObjectId(ticket_id),
            'user_id': str(current_user['_id'])
        })
        
        if not ticket:
            return jsonify({'message': 'Support ticket not found!'}), 404
        
        # Format ticket
        ticket['id'] = str(ticket.pop('_id'))
        
        return jsonify(ticket), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/support/tickets/<ticket_id>/reply', methods=['POST'])
@token_required
def reply_to_support_ticket(current_user, ticket_id):
    data = request.get_json()
    
    # Check if message content is provided
    if 'content' not in data:
        return jsonify({'message': 'Message content is required!'}), 400
    
    # Create new message
    new_message = {
        'sender': 'user',
        'sender_name': f"{current_user['first_name']} {current_user['last_name']}",
        'content': data['content'],
        'timestamp': datetime.utcnow()
    }
    
    try:
        # Update ticket with new message
        result = mongo.db.support_tickets.update_one(
            {'_id': ObjectId(ticket_id), 'user_id': str(current_user['_id'])},
            {
                '$push': {'messages': new_message},
                '$set': {'updated_at': datetime.utcnow(), 'status': 'open'}
            }
        )
        
        if result.matched_count == 0:
            return jsonify({'message': 'Support ticket not found!'}), 404
        
        return jsonify({'message': 'Reply added successfully!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Session Management Routes
@user_bp.route('/api/sessions', methods=['GET'])
def get_sessions():
    try:
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

        user_id = session['user_id']
        
        # Get total sessions count
        total_sessions = mongo.db.sessions.count_documents({'user_id': user_id})

        # Get upcoming sessions count
        upcoming_sessions = mongo.db.sessions.count_documents({'user_id': user_id, 'date': {'$gte': datetime.utcnow()}, 'status': 'scheduled'})

        # Get completed sessions count
        completed_sessions = mongo.db.sessions.count_documents({'user_id': user_id, 'status': 'completed'})

        # Get recent sessions
        recent_sessions = mongo.db.sessions.find(
            {'user_id': user_id},
            {'_id': 1, 'date': 1, 'duration': 1, 'status': 1, 'notes': 1}
        ).sort('date', -1).limit(5)

        sessions = []
        for session in recent_sessions:
            sessions.append({
                'id': str(session['_id']),
                'date': session['date'],
                'duration': session['duration'],
                'status': session['status'],
                'notes': session['notes']
            })

        return jsonify({
            'status': 'success',
            'sessions': {
                'total': total_sessions,
                'upcoming': upcoming_sessions,
                'completed': completed_sessions,
                'recent': sessions
            }
        })

    except Exception as e:
        print(f"Error fetching sessions: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to fetch sessions'}), 500

@user_bp.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    try:
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

        user_id = session['user_id']
        
        # Get session details
        session_data = mongo.db.sessions.find_one(
            {'_id': session_id, 'user_id': user_id},
            {'_id': 1, 'date': 1, 'duration': 1, 'status': 1, 'notes': 1, 'therapist_id': 1}
        )

        if not session_data:
            return jsonify({'status': 'error', 'message': 'Session not found'}), 404

        return jsonify({
            'status': 'success',
            'session': {
                'id': str(session_data['_id']),
                'date': session_data['date'],
                'duration': session_data['duration'],
                'status': session_data['status'],
                'notes': session_data['notes'],
                'therapist': {
                    'id': str(session_data['therapist_id'])
                }
            }
        })

    except Exception as e:
        print(f"Error fetching session: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to fetch session'}), 500

@user_bp.route('/api/sessions/<int:session_id>/notes', methods=['GET'])
@token_required
def get_session_notes(current_user, session_id):
    try:
        session = mongo.db.sessions.find_one({
            '_id': ObjectId(session_id),
            'user_id': current_user['_id']
        })
        
        if not session:
            return jsonify({'message': 'Session not found!'}), 404
        
        return jsonify({
            'notes': session.get('notes', ''),
            'summary': session.get('summary', '')
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/sessions/<int:session_id>/summary', methods=['GET'])
@token_required
def get_session_summary(current_user, session_id):
    try:
        session = mongo.db.sessions.find_one({
            '_id': ObjectId(session_id),
            'user_id': current_user['_id']
        })
        
        if not session:
            return jsonify({'message': 'Session not found!'}), 404
        
        if not session.get('summary_file'):
            return jsonify({'message': 'No summary file available!'}), 404
        
        return send_file(
            session['summary_file'],
            as_attachment=True,
            download_name=f"session_summary_{session_id}.pdf"
        )
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/emergency/contact', methods=['POST'])
@token_required
def emergency_contact(current_user):
    try:
        # In a real application, this would trigger an emergency response system
        # For now, we'll just log the request and return a success message
        emergency_request = {
            'user_id': current_user['_id'],
            'timestamp': datetime.utcnow(),
            'status': 'pending',
            'location': request.json.get('location', ''),
            'description': request.json.get('description', '')
        }
        
        mongo.db.emergency_requests.insert_one(emergency_request)
        
        return jsonify({
            'message': 'Emergency services have been contacted. Help is on the way.',
            'emergency_id': str(emergency_request['_id'])
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/calendar/events', methods=['GET'])
@token_required
def get_calendar_events(current_user):
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        
        query = {
            'user_id': current_user['_id']
        }
        
        if start_date and end_date:
            query['date'] = {
                '$gte': datetime.fromisoformat(start_date),
                '$lte': datetime.fromisoformat(end_date)
            }
        
        events = list(mongo.db.appointments.find(query))
        
        return jsonify({
            'events': [{
                'id': str(event['_id']),
                'title': f"Session with {event['therapist_name']}",
                'start': event['date'].isoformat(),
                'end': (event['date'] + timedelta(hours=1)).isoformat(),
                'status': event.get('status', 'scheduled'),
                'type': 'appointment'
            } for event in events]
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/chat/messages', methods=['GET'])
@token_required
def get_chat_messages(current_user):
    try:
        therapist_id = request.args.get('therapist_id')
        limit = int(request.args.get('limit', 50))
        before = request.args.get('before')
        
        query = {
            'user_id': current_user['_id'],
            'therapist_id': ObjectId(therapist_id)
        }
        
        if before:
            query['timestamp'] = {'$lt': datetime.fromisoformat(before)}
        
        messages = list(mongo.db.chat_messages
            .find(query)
            .sort('timestamp', -1)
            .limit(limit))
        
        return jsonify({
            'messages': [{
                'id': str(msg['_id']),
                'content': msg['content'],
                'timestamp': msg['timestamp'].isoformat(),
                'sender': msg['sender'],
                'read': msg.get('read', False)
            } for msg in messages]
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/chat/messages/read', methods=['POST'])
@token_required
def mark_messages_read(current_user):
    try:
        message_ids = request.json.get('message_ids', [])
        
        if not message_ids:
            return jsonify({'message': 'No message IDs provided!'}), 400
        
        mongo.db.chat_messages.update_many(
            {
                '_id': {'$in': [ObjectId(id) for id in message_ids]},
                'user_id': current_user['_id']
            },
            {'$set': {'read': True}}
        )
        
        return jsonify({'message': 'Messages marked as read!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/chat/typing', methods=['POST'])
@token_required
def set_typing_status(current_user):
    try:
        therapist_id = request.json.get('therapist_id')
        is_typing = request.json.get('is_typing', False)
        
        if not therapist_id:
            return jsonify({'message': 'Therapist ID is required!'}), 400
        
        mongo.db.chat_status.update_one(
            {
                'user_id': current_user['_id'],
                'therapist_id': ObjectId(therapist_id)
            },
            {
                '$set': {
                    'is_typing': is_typing,
                    'last_updated': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return jsonify({'message': 'Typing status updated!'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@user_bp.route('/api/chat/status', methods=['GET'])
@token_required
def get_chat_status(current_user):
    try:
        therapist_id = request.args.get('therapist_id')
        
        if not therapist_id:
            return jsonify({'message': 'Therapist ID is required!'}), 400
        
        status = mongo.db.chat_status.find_one({
            'user_id': current_user['_id'],
            'therapist_id': ObjectId(therapist_id)
        })
        
        return jsonify({
            'is_typing': status.get('is_typing', False) if status else False,
            'last_updated': status.get('last_updated').isoformat() if status and status.get('last_updated') else None
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Initialize MongoDB collections and indexes
def init_mongo_collections():
    try:
        # Create sessions collection if it doesn't exist
        if 'sessions' not in mongo.db.list_collection_names():
            mongo.db.create_collection('sessions')
            print("Created sessions collection")

        # Create documents collection if it doesn't exist
        if 'documents' not in mongo.db.list_collection_names():
            mongo.db.create_collection('documents')
            print("Created documents collection")

        # Create support_tickets collection if it doesn't exist
        if 'support_tickets' not in mongo.db.list_collection_names():
            mongo.db.create_collection('support_tickets')
            print("Created support_tickets collection")

        # Create indexes for sessions
        mongo.db.sessions.create_index([('user_id', 1)])
        mongo.db.sessions.create_index([('therapist_id', 1)])
        mongo.db.sessions.create_index([('date', -1)])
        mongo.db.sessions.create_index([('status', 1)])

        # Create indexes for documents
        mongo.db.documents.create_index([('user_id', 1)])
        mongo.db.documents.create_index([('is_public', 1)])
        mongo.db.documents.create_index([('created_at', -1)])

        # Create indexes for support_tickets
        mongo.db.support_tickets.create_index([('user_id', 1)])
        mongo.db.support_tickets.create_index([('status', 1)])
        mongo.db.support_tickets.create_index([('created_at', -1)])
        mongo.db.support_tickets.create_index([('priority', 1)])

        print("MongoDB collections and indexes initialized successfully")
    except Exception as e:
        print(f"Error initializing MongoDB collections: {str(e)}")

# Initialize MongoDB when the blueprint is registered
def init_app(app):
    mongo.init_app(app)
    with app.app_context():
        init_mongo_collections()