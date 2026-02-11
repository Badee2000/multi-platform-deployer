# FastAPI Example Application

A complete FastAPI application ready for deployment with the multi-platform-deployer.

## Features

- Modern async Python web framework
- Built-in API documentation (Swagger UI)
- Type hints and validation
- CORS support
- Health check endpoints
- Database integration example

## Setup

```bash
cd examples/fastapi_app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run application
uvicorn app:app --reload
```

## Project Structure

```
fastapi_app/
├── app.py              # Main application
├── config.py           # Configuration
├── requirements.txt    # Dependencies
├── .env.example       # Environment variables example
├── deployment.yaml    # Deployment configuration
└── README.md
```

## Deployment

### To Vercel
```bash
cd ..
python -m src.main deploy vercel --config fastapi_app/deployment.yaml
```

### To Render
```bash
python -m src.main deploy render --config fastapi_app/deployment.yaml
```

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /api/status` - Application status
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

## Environment Variables

See `.env.example` for required variables:
- `DEBUG` - Debug mode
- `DATABASE_URL` - Database connection string

## Testing

```bash
pip install pytest httpx

pytest tests/
```
