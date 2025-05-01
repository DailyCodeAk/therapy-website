from flask import Flask
from user_backend import user_bp, init_app as init_user_backend

app = Flask(__name__)

# Initialize the user backend
init_user_backend(app)

# Register blueprints
app.register_blueprint(user_bp)

if __name__ == '__main__':
    app.run(debug=True) 