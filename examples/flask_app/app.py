"""Flask example application."""

import os
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['DEBUG'] = os.getenv('FLASK_ENV') == 'development'

# Database URL (if using SQLAlchemy)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')


@app.route('/')
def index():
    """Welcome endpoint."""
    return jsonify({
        'message': 'Welcome to Flask Example App',
        'version': '1.0.0',
        'status': 'running',
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'flask-app',
    }), 200


@app.route('/api/status')
def api_status():
    """API status endpoint."""
    return jsonify({
        'service': 'flask-api',
        'status': 'operational',
        'database': check_database(),
    }), 200


def check_database():
    """Check database connectivity."""
    try:
        # Add your database check logic here
        return 'connected'
    except Exception as e:
        return f'error: {str(e)}'


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=app.config['DEBUG']
    )
