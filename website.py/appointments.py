from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os

appointments_bp = Blueprint('appointments', __name__)

# In a real application, you would use a database
# For this example, we'll use a JSON file to simulate a database
APPOINTMENTS_FILE = 'appointments.json'

def load_appointments():
    if os.path.exists(APPOINTMENTS_FILE):
        with open(APPOINTMENTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_appointments(appointments):
    with open(APPOINTMENTS_FILE, 'w') as f:
        json.dump(appointments, f, indent=4)

@appointments_bp.route('/api/appointments', methods=['GET'])
def get_appointments():
    appointments = load_appointments()
    return jsonify(appointments)

@appointments_bp.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.json
    
    # Validate required fields
    required_fields = ['date', 'time', 'sessionType']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Validate date format
    try:
        datetime.strptime(data['date'], '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Validate time format
    try:
        datetime.strptime(data['time'], '%H:%M')
    except ValueError:
        return jsonify({'error': 'Invalid time format. Use HH:MM'}), 400
    
    # Create new appointment
    appointments = load_appointments()
    new_appointment = {
        'id': str(datetime.now().timestamp()),
        'date': data['date'],
        'time': data['time'],
        'sessionType': data['sessionType'],
        'notes': data.get('notes', ''),
        'status': 'Confirmed',
        'createdAt': datetime.now().isoformat()
    }
    
    appointments.append(new_appointment)
    save_appointments(appointments)
    
    return jsonify(new_appointment), 201

@appointments_bp.route('/api/appointments/<appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    data = request.json
    appointments = load_appointments()
    
    # Find the appointment
    appointment_index = next((i for i, a in enumerate(appointments) if a['id'] == appointment_id), None)
    if appointment_index is None:
        return jsonify({'error': 'Appointment not found'}), 404
    
    # Validate date format if provided
    if 'date' in data:
        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Validate time format if provided
    if 'time' in data:
        try:
            datetime.strptime(data['time'], '%H:%M')
        except ValueError:
            return jsonify({'error': 'Invalid time format. Use HH:MM'}), 400
    
    # Update appointment
    appointments[appointment_index].update({
        'date': data.get('date', appointments[appointment_index]['date']),
        'time': data.get('time', appointments[appointment_index]['time']),
        'sessionType': data.get('sessionType', appointments[appointment_index]['sessionType']),
        'notes': data.get('notes', appointments[appointment_index]['notes']),
        'updatedAt': datetime.now().isoformat()
    })
    
    save_appointments(appointments)
    return jsonify(appointments[appointment_index])

@appointments_bp.route('/api/appointments/<appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    appointments = load_appointments()
    
    # Find the appointment
    appointment_index = next((i for i, a in enumerate(appointments) if a['id'] == appointment_id), None)
    if appointment_index is None:
        return jsonify({'error': 'Appointment not found'}), 404
    
    # Remove appointment
    deleted_appointment = appointments.pop(appointment_index)
    save_appointments(appointments)
    
    return jsonify(deleted_appointment) 