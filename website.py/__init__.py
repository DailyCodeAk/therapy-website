from flask import Flask
from .appointments import appointments_bp

def create_app():
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(appointments_bp)
    
    return app 