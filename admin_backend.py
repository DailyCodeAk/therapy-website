from flask import Blueprint, jsonify, session, render_template, redirect, url_for
from bson.objectid import ObjectId
from datetime import datetime
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create Blueprint
admin_bp = Blueprint('admin', __name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Admin middleware
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        if session.get('role') != 'admin':
            return jsonify({'status': 'error', 'message': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Admin routes
@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
@limiter.limit("30 per minute")
def admin_get_users():
    db = admin_bp.config['mongo'].db
    users = list(db.users.find({}, {'password': 0}).sort('created_at', -1))
    
    # Convert ObjectId to string for JSON serialization
    for user in users:
        user['_id'] = str(user['_id'])
    
    return jsonify({
        'status': 'success',
        'users': users
    })

@admin_bp.route('/admin/contact_messages', methods=['GET'])
@admin_required
@limiter.limit("30 per minute")
def admin_get_contact_messages():
    db = admin_bp.config['mongo'].db
    messages = list(db.contact_messages.find({}).sort('created_at', -1))
    
    # Convert ObjectId to string for JSON serialization
    for message in messages:
        message['_id'] = str(message['_id'])
    
    return jsonify({
        'status': 'success',
        'messages': messages
    })

@admin_bp.route('/admin/surveys', methods=['GET'])
@admin_required
@limiter.limit("30 per minute")
def admin_get_surveys():
    db = admin_bp.config['mongo'].db
    surveys = list(db.surveys.find({}).sort('created_at', -1))
    
    # Convert ObjectId to string for JSON serialization
    for survey in surveys:
        survey['_id'] = str(survey['_id'])
        if 'user_id' in survey:
            survey['user_id'] = str(survey['user_id'])
    
    return jsonify({
        'status': 'success',
        'surveys': surveys
    })

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    db = admin_bp.config['mongo'].db
    # Get statistics for the admin dashboard
    stats = {
        'total_users': db.users.count_documents({}),
        'active_appointments': db.appointments.count_documents({
            'status': {'$in': ['scheduled', 'confirmed']}
        }),
        'total_therapists': db.users.count_documents({'role': 'therapist'}),
        'total_revenue': calculate_total_revenue(db)
    }
    
    return render_template('admin.html', stats=stats)

@admin_bp.route('/admin/appointments', methods=['GET'])
@admin_required
@limiter.limit("30 per minute")
def admin_get_appointments():
    db = admin_bp.config['mongo'].db
    appointments = list(db.appointments.find({}).sort('date', -1))
    
    # Convert ObjectId to string for JSON serialization
    for appointment in appointments:
        appointment['_id'] = str(appointment['_id'])
        if 'user_id' in appointment:
            appointment['user_id'] = str(appointment['user_id'])
    
    return jsonify({
        'status': 'success',
        'appointments': appointments
    })

@admin_bp.route('/admin/therapists', methods=['GET'])
@admin_required
@limiter.limit("30 per minute")
def admin_get_therapists():
    db = admin_bp.config['mongo'].db
    therapists = list(db.users.find({'role': 'therapist'}, {'password': 0}).sort('created_at', -1))
    
    # Convert ObjectId to string for JSON serialization
    for therapist in therapists:
        therapist['_id'] = str(therapist['_id'])
    
    return jsonify({
        'status': 'success',
        'therapists': therapists
    })

# Helper functions
def calculate_total_revenue(db):
    """Calculate total revenue from completed appointments"""
    completed_appointments = db.appointments.find({
        'status': 'completed',
        'payment_status': 'paid'
    })
    
    total_revenue = sum(appointment.get('amount_paid', 0) for appointment in completed_appointments)
    return total_revenue

def init_admin(app, mongo):
    """Initialize the admin blueprint with the Flask app and MongoDB instance"""
    admin_bp.config = {}
    admin_bp.config['mongo'] = mongo
    app.register_blueprint(admin_bp) 