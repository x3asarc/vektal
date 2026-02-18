"""
OAuth attempt logging for debugging and security monitoring.

Tracks all Shopify OAuth attempts with results and metadata.
State tokens expire in 1 hour for CSRF protection.
"""
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from src.models import db, TimestampMixin


class OAuthAttempt(db.Model, TimestampMixin):
    """
    Log OAuth attempts for debugging and security monitoring.

    Each attempt records shop domain, result, and metadata.
    State tokens are unique and expire in 1 hour.
    """
    __tablename__ = 'oauth_attempts'

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # OAuth details
    shop_domain = db.Column(String(255), nullable=False)
    state_token = db.Column(String(64), unique=True, nullable=False, index=True)

    # Result tracking
    result = db.Column(String(50), nullable=False)  # success, access_denied, network_error, timeout, state_mismatch
    error_details = db.Column(Text, nullable=True)

    # Security monitoring
    ip_address = db.Column(String(45), nullable=True)  # IPv6-compatible
    user_agent = db.Column(String(512), nullable=True)

    # State expiration (1 hour)
    expires_at = db.Column(DateTime, nullable=False, index=True)

    # Relationships
    user = relationship('User', backref='oauth_attempt_logs')

    def __repr__(self):
        return f'<OAuthAttempt user_id={self.user_id} result={self.result}>'

    @classmethod
    def cleanup_expired(cls):
        """Delete expired state tokens. Run daily via Celery."""
        cutoff = datetime.utcnow()
        expired_count = cls.query.filter(cls.expires_at < cutoff).delete()
        db.session.commit()
        return expired_count

    @classmethod
    def create_attempt(cls, user_id: int, shop_domain: str, state_token: str,
                       ip_address: str = None, user_agent: str = None):
        """Create new OAuth attempt record with 1-hour expiration."""
        attempt = cls(
            user_id=user_id,
            shop_domain=shop_domain,
            state_token=state_token,
            result='pending',  # Updated on callback
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(attempt)
        db.session.commit()
        return attempt
