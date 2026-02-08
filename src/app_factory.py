"""
Flask application factory for CLI commands.

This module provides the app instance for Flask-Migrate CLI commands:
- flask db init
- flask db migrate
- flask db upgrade
- flask db downgrade

Usage:
    export FLASK_APP=src/app_factory.py  # or set FLASK_APP in .env
    flask db migrate -m "Migration message"
    flask db upgrade
"""
from src.database import create_app

# Create app instance for Flask CLI
app = create_app()

if __name__ == '__main__':
    app.run()
