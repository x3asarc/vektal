"""
Flask-Mail configuration for email delivery.

Supports Resend or SendGrid as SMTP providers (user choice per CONTEXT.md).

Environment variables:
- MAIL_SERVER: SMTP server (smtp.resend.com or smtp.sendgrid.net)
- MAIL_PORT: SMTP port (587 for TLS)
- MAIL_USERNAME: SMTP username (resend or apikey)
- MAIL_PASSWORD: API key from provider
- MAIL_DEFAULT_SENDER: Verified sender email
- MAIL_USE_TLS: True for TLS (default)
"""
from flask_mail import Mail
import os

mail = Mail()


def configure_mail(app):
    """
    Configure Flask-Mail with SMTP settings.

    Args:
        app: Flask application instance
    """
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.resend.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'resend')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@example.com')

    # Suppress SMTP debug output unless explicitly enabled
    app.config['MAIL_DEBUG'] = app.debug

    mail.init_app(app)

    return mail
