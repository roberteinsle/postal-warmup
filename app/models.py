"""
Database models for Postal Warmup Application
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()


class Email(db.Model):
    """Track sent emails"""
    __tablename__ = 'emails'

    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(255), nullable=False, index=True)
    recipient = db.Column(db.String(255), nullable=False, index=True)
    subject = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    content_type = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )  # transactional, newsletter, personal, mixed

    # Postal tracking
    postal_message_id = db.Column(db.String(255), unique=True, index=True)

    # Status tracking
    status = db.Column(
        db.String(50),
        nullable=False,
        default='pending',
        index=True
    )  # pending, sending, sent, failed, bounced

    delivery_status = db.Column(
        db.String(50),
        default='pending',
        index=True
    )  # pending, inbox, spam, unknown, failed

    # Timestamps
    sent_at = db.Column(db.DateTime, index=True)
    check_scheduled_at = db.Column(db.DateTime, index=True)
    checked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Interaction tracking
    is_read = db.Column(db.Boolean, default=False)
    moved_to_folder = db.Column(db.String(255))

    @property
    def is_inbox(self):
        """Check if email landed in inbox"""
        return self.delivery_status == 'inbox'

    @property
    def is_spam(self):
        """Check if email landed in spam"""
        return self.delivery_status == 'spam'

    def is_pending_check(self):
        """Check if email is pending delivery check"""
        if not self.check_scheduled_at or self.checked_at:
            return False
        return datetime.utcnow() >= self.check_scheduled_at

    def __repr__(self):
        return f'<Email {self.id}: {self.sender} -> {self.recipient}>'


class WarmupSchedule(db.Model):
    """Configurable warmup plan"""
    __tablename__ = 'warmup_schedule'

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Integer, nullable=False, unique=True, index=True)
    target_emails = db.Column(db.Integer, nullable=False, default=0)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationship
    executions = db.relationship(
        'WarmupExecution',
        backref='schedule',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<WarmupSchedule Day {self.day}: {self.target_emails} emails>'


class WarmupExecution(db.Model):
    """Track actual warmup execution"""
    __tablename__ = 'warmup_execution'

    id = db.Column(db.Integer, primary_key=True)
    schedule_day_id = db.Column(
        db.Integer,
        db.ForeignKey('warmup_schedule.id'),
        nullable=False,
        index=True
    )
    date = db.Column(db.Date, nullable=False, index=True)
    sent_count = db.Column(db.Integer, default=0, nullable=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f'<WarmupExecution {self.date}: {self.sent_count} emails>'


class EmailAddress(db.Model):
    """Manage sender and recipient email addresses"""
    __tablename__ = 'email_addresses'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    type = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )  # sender, recipient
    verified = db.Column(db.Boolean, default=False, nullable=False)
    imap_password = db.Column(db.Text)  # Encrypted, for recipients only
    last_used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f'<EmailAddress {self.email} ({self.type})>'


class Setting(db.Model):
    """Application configuration settings"""
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), nullable=False, unique=True, index=True)
    value = db.Column(db.Text)
    is_encrypted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f'<Setting {self.key}>'


class Statistic(db.Model):
    """Daily aggregated metrics"""
    __tablename__ = 'statistics'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    emails_sent = db.Column(db.Integer, default=0, nullable=False)
    emails_inbox = db.Column(db.Integer, default=0, nullable=False)
    emails_spam = db.Column(db.Integer, default=0, nullable=False)
    emails_failed = db.Column(db.Integer, default=0, nullable=False)
    bounce_count = db.Column(db.Integer, default=0, nullable=False)

    # Calculated rates (stored for historical tracking)
    success_rate = db.Column(db.Float, default=0.0)
    spam_rate = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def calculate_rates(self):
        """Calculate success and spam rates"""
        if self.emails_sent > 0:
            self.success_rate = (self.emails_inbox / self.emails_sent) * 100
            self.spam_rate = (self.emails_spam / self.emails_sent) * 100
        else:
            self.success_rate = 0.0
            self.spam_rate = 0.0

    def __repr__(self):
        return f'<Statistic {self.date}: {self.emails_sent} sent, {self.success_rate:.1f}% success>'


class SenderDomain(db.Model):
    """Track sender domain reputation metrics"""
    __tablename__ = 'sender_domains'

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), nullable=False, unique=True, index=True)
    ip_address = db.Column(db.String(50))  # IPv4 or IPv6

    # Reputation metrics
    reputation_score = db.Column(db.Float, default=0.0)  # 0-100
    bounce_rate = db.Column(db.Float, default=0.0)
    spam_rate = db.Column(db.Float, default=0.0)
    delivery_success_rate = db.Column(db.Float, default=0.0)

    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f'<SenderDomain {self.domain}: Score {self.reputation_score:.1f}>'
