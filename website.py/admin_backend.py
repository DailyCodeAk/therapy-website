from flask import Blueprint, jsonify, request, session
from functools import wraps
from bson.objectid import ObjectId
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'role' not in session or session['role'] != 'admin':
            return jsonify({'status': 'error', 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def init_admin(app, mongo):
    db = mongo.db
    
    @admin_bp.route('/api/admin/users', methods=['GET'])
    @admin_required
    def get_users():
        users = list(db.users.find({}, {'password': 0}))
        return jsonify({
            'status': 'success',
            'users': [{**user, '_id': str(user['_id'])} for user in users]
        })

    @admin_bp.route('/api/admin/therapists', methods=['GET', 'POST'])
    @admin_required
    def manage_therapists():
        if request.method == 'GET':
            therapists = list(db.therapists.find())
            return jsonify({
                'status': 'success',
                'therapists': [{**t, '_id': str(t['_id'])} for t in therapists]
            })
        
        elif request.method == 'POST':
            data = request.json
            required_fields = ['name', 'title', 'bio']
            
            if not all(field in data for field in required_fields):
                return jsonify({
                    'status': 'error',
                    'message': 'Missing required fields'
                }), 400
            
            therapist = {
                'name': data['name'],
                'title': data['title'],
                'bio': data['bio'],
                'image_url': data.get('image_url', ''),
                'social_links': data.get('social_links', {}),
                'created_at': datetime.utcnow()
            }
            
            result = db.therapists.insert_one(therapist)
            return jsonify({
                'status': 'success',
                'message': 'Therapist added successfully',
                'therapist_id': str(result.inserted_id)
            })

    @admin_bp.route('/api/admin/appointments', methods=['GET'])
    @admin_required
    def get_appointments():
        appointments = list(db.appointments.find())
        return jsonify({
            'status': 'success',
            'appointments': [{**apt, '_id': str(apt['_id'])} for apt in appointments]
        })

    app.register_blueprint(admin_bp) 