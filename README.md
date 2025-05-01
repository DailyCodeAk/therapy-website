# Therapy Website

A comprehensive therapy website platform that connects therapists with patients, providing features for appointment scheduling, session management, and patient progress tracking.

## Features

- User authentication and role-based access control
- Appointment scheduling and management
- Session notes and progress tracking
- Goal setting and milestone tracking
- Secure messaging system
- Resource sharing
- Payment processing
- Report generation
- Notification system

## Tech Stack

- Backend: Python (Flask)
- Database: MongoDB
- Authentication: JWT
- Testing: pytest
- API Documentation: Swagger/OpenAPI

## Setup

1. Clone the repository:
```bash
git clone https://github.com/dailycodeak/therapy-website.git
cd therapy-website
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
python init_db.py
```

6. Run the development server:
```bash
python website.py/app.py
```

## Testing

Run the test suite:
```bash
pytest
```

## API Documentation

API documentation is available at `/api/docs` when running the development server.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
