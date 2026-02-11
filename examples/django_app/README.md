# Django Example Application

A complete Django application ready for deployment with the multi-platform-deployer.

## Features

- Full Django project setup
- Production-ready security settings
- Static files configuration
- Database migrations
- Admin interface
- REST API example

## Setup

```bash
cd examples/django_app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server
python manage.py runserver
```

## Project Structure

```
django_app/
├── manage.py
├── config/              # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   └── core/           # Core app
├── static/             # Static files
├── templates/          # Django templates
├── requirements.txt
├── .env.example
├── deployment.yaml
└── README.md
```

## Deployment

### To Render
```bash
cd ..
python -m src.main deploy render --config django_app/deployment.yaml
```

### To Railway
```bash
python -m src.main deploy railway --config django_app/deployment.yaml
```

## Environment Variables

See `.env.example` for required variables:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (False in production)
- `ALLOWED_HOSTS` - Allowed hostnames
- `DATABASE_URL` - Database connection
- `STATIC_ROOT` - Static files directory

## Testing

```bash
python manage.py test
```

## Admin Interface

Access Django admin at `/admin` with your superuser credentials.
