"""
Email sending functions for authentication flows.

Uses Flask-Mail to send transactional emails:
- Email verification
- Welcome email after account creation
- OAuth reminder emails (future)

NOTE: Password reset emails are deferred to Phase 4.1 per CONTEXT.md.
"""
from flask import current_app, render_template_string
from flask_mail import Message
from src.config.email_config import mail


# Email templates (inline for now - move to templates/ in Phase 7)
VERIFICATION_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Verify Your Email</title></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #333;">Verify Your Email Address</h1>
    <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
    <p style="margin: 30px 0;">
        <a href="{{ verification_url }}"
           style="background-color: #4CAF50; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 4px; display: inline-block;">
            Verify Email
        </a>
    </p>
    <p style="color: #666; font-size: 14px;">
        Or copy this link: <br>
        <a href="{{ verification_url }}">{{ verification_url }}</a>
    </p>
    <p style="color: #666; font-size: 14px;">
        This link expires in 1 hour. If you didn't create an account, you can ignore this email.
    </p>
</body>
</html>
"""

WELCOME_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Welcome!</title></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #333;">Welcome to {{ app_name }}!</h1>
    <p>Your account has been created successfully. Here's what to do next:</p>
    <ol style="line-height: 1.8;">
        <li>Verify your email address (check your inbox)</li>
        <li>Connect your Shopify store</li>
        <li>Start managing your products!</li>
    </ol>
    <p style="margin: 30px 0;">
        <a href="{{ dashboard_url }}"
           style="background-color: #4CAF50; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 4px; display: inline-block;">
            Go to Dashboard
        </a>
    </p>
    <p style="color: #666; font-size: 14px;">
        Need help? Reply to this email or visit our documentation.
    </p>
</body>
</html>
"""


def send_verification_email(email: str, verification_url: str) -> bool:
    """
    Send email verification link.

    Args:
        email: Recipient email address
        verification_url: Full URL with verification token

    Returns:
        True if sent successfully, False on error
    """
    try:
        html_body = render_template_string(
            VERIFICATION_EMAIL_TEMPLATE,
            verification_url=verification_url
        )

        msg = Message(
            subject="Verify Your Email Address",
            recipients=[email],
            html=html_body
        )

        mail.send(msg)
        current_app.logger.info(f'Verification email sent to {email}')
        return True

    except Exception as e:
        current_app.logger.error(f'Failed to send verification email to {email}: {str(e)}')
        return False


def send_welcome_email(email: str, dashboard_url: str, app_name: str = "Shopify Multi-Supplier Platform") -> bool:
    """
    Send welcome email after account creation.

    Args:
        email: Recipient email address
        dashboard_url: URL to the user dashboard
        app_name: Application name for branding

    Returns:
        True if sent successfully, False on error
    """
    try:
        html_body = render_template_string(
            WELCOME_EMAIL_TEMPLATE,
            dashboard_url=dashboard_url,
            app_name=app_name
        )

        msg = Message(
            subject=f"Welcome to {app_name}!",
            recipients=[email],
            html=html_body
        )

        mail.send(msg)
        current_app.logger.info(f'Welcome email sent to {email}')
        return True

    except Exception as e:
        current_app.logger.error(f'Failed to send welcome email to {email}: {str(e)}')
        return False


def send_oauth_reminder_email(email: str, connect_url: str, days_remaining: int) -> bool:
    """
    Send reminder to complete OAuth setup.

    Per CONTEXT.md: Send reminders on Day 1, 3, 6 of 7-day grace period.

    Args:
        email: Recipient email address
        connect_url: URL to connect Shopify store
        days_remaining: Days left in grace period

    Returns:
        True if sent successfully, False on error
    """
    try:
        subject = f"Complete Your Setup - {days_remaining} days remaining"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Complete Your Setup</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #333;">Complete Your Shopify Connection</h1>
            <p>Your account is almost ready! You have <strong>{days_remaining} days</strong>
               remaining to connect your Shopify store.</p>
            <p style="margin: 30px 0;">
                <a href="{connect_url}"
                   style="background-color: #4CAF50; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Connect Shopify Store
                </a>
            </p>
            <p style="color: #666; font-size: 14px;">
                If you need help connecting your store, reply to this email.
            </p>
        </body>
        </html>
        """

        msg = Message(
            subject=subject,
            recipients=[email],
            html=html_body
        )

        mail.send(msg)
        current_app.logger.info(f'OAuth reminder email sent to {email}')
        return True

    except Exception as e:
        current_app.logger.error(f'Failed to send OAuth reminder to {email}: {str(e)}')
        return False
