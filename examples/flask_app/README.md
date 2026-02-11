# Flask Example Application

A complete Flask application ready for deployment with the multi-platform-deployer.

## Features

- Simple REST API with health check
- Production-ready configuration
- Database integration example (SQLAlchemy)
- Error handling
- CORS support
- Environment variable support

## Setup

```bash
cd examples/flask_app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run application
python app.py
```

## Project Structure

```
flask_app/
├── app.py              # Main application
├── config.py           # Configuration
├── requirements.txt    # Dependencies
├── .env.example       # Environment variables example
├── deployment.yaml    # Deployment configuration
└── README.md
```

## Deployment

### To Render
```bash
cd ..
python -m src.main deploy render --config flask_app/deployment.yaml
```

### To Railway
```bash
python -m src.main deploy railway --config flask_app/deployment.yaml
```

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /api/status` - Application status

## Environment Variables

See `.env.example` for required environment variables:
- `FLASK_ENV` - Development or production
- `SECRET_KEY` - Secret key for sessions
- `DATABASE_URL` - Database connection string

## Testing

```bash
pip install pytest

pytest tests/
```
