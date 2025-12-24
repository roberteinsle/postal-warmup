"""
Database initialization and management utilities
"""
from app.models import db, WarmupSchedule, EmailAddress, SenderDomain, Statistic
from app.utils.logger import get_logger
from cryptography.fernet import Fernet
import os

logger = get_logger()


def init_db(app):
    """
    Initialize database with tables and default data

    Args:
        app: Flask application instance
    """
    with app.app_context():
        # Create all tables
        db.create_all()
        logger.info("Database tables created successfully")

        # Seed default data
        seed_default_data(app)


def seed_default_data(app):
    """
    Seed database with default configuration

    Args:
        app: Flask application instance
    """
    with app.app_context():
        # Check if warmup schedule exists
        if WarmupSchedule.query.count() == 0:
            logger.info("Seeding default warmup schedule...")
            default_schedule = [
                {'day': 1, 'target_emails': 5},
                {'day': 2, 'target_emails': 10},
                {'day': 3, 'target_emails': 15},
                {'day': 4, 'target_emails': 20},
                {'day': 5, 'target_emails': 25},
                {'day': 6, 'target_emails': 30},
                {'day': 7, 'target_emails': 35},
                {'day': 8, 'target_emails': 40},
                {'day': 9, 'target_emails': 45},
                {'day': 10, 'target_emails': 50},
                {'day': 11, 'target_emails': 60},
                {'day': 12, 'target_emails': 70},
                {'day': 13, 'target_emails': 80},
                {'day': 14, 'target_emails': 90},
                {'day': 15, 'target_emails': 100},
            ]

            for schedule_data in default_schedule:
                schedule = WarmupSchedule(**schedule_data)
                db.session.add(schedule)

            db.session.commit()
            logger.info(f"Created {len(default_schedule)} warmup schedule entries")

        # Seed email addresses from config
        if EmailAddress.query.count() == 0:
            logger.info("Seeding email addresses from configuration...")

            # Sender addresses
            for sender in app.config.get('SENDER_ADDRESSES', []):
                if sender:
                    email_addr = EmailAddress(
                        email=sender,
                        type='sender',
                        verified=False
                    )
                    db.session.add(email_addr)
                    logger.info(f"Added sender: {sender}")

            # Recipient addresses
            recipient_passwords = app.config.get('RECIPIENT_IMAP_PASSWORDS', {})
            for recipient in app.config.get('RECIPIENT_ADDRESSES', []):
                if recipient:
                    # Encrypt password if available
                    encrypted_password = None
                    if recipient in recipient_passwords:
                        password = recipient_passwords[recipient]
                        encrypted_password = encrypt_password(password, app)

                    email_addr = EmailAddress(
                        email=recipient,
                        type='recipient',
                        verified=False,
                        imap_password=encrypted_password
                    )
                    db.session.add(email_addr)
                    logger.info(f"Added recipient: {recipient}")

            db.session.commit()
            logger.info("Email addresses seeded successfully")

        # Seed sender domain
        if SenderDomain.query.count() == 0:
            logger.info("Seeding sender domain...")
            domain = SenderDomain(
                domain='einsle.cloud',
                ip_address='157.180.87.250',  # IPv4
                reputation_score=0.0
            )
            db.session.add(domain)
            db.session.commit()
            logger.info("Sender domain seeded successfully")


def encrypt_password(password, app):
    """
    Encrypt password using Fernet symmetric encryption

    Args:
        password: Plain text password
        app: Flask application instance

    Returns:
        str: Encrypted password
    """
    # Use SECRET_KEY as encryption key (first 32 bytes, base64 encoded)
    secret_key = app.config['SECRET_KEY'].encode()

    # Generate Fernet key from secret
    # In production, use a dedicated encryption key
    import base64
    import hashlib
    key_bytes = hashlib.sha256(secret_key).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)

    fernet = Fernet(fernet_key)
    encrypted = fernet.encrypt(password.encode())
    return encrypted.decode()


def decrypt_password(encrypted_password, app):
    """
    Decrypt password using Fernet symmetric encryption

    Args:
        encrypted_password: Encrypted password string
        app: Flask application instance

    Returns:
        str: Decrypted password
    """
    # Use SECRET_KEY as encryption key
    secret_key = app.config['SECRET_KEY'].encode()

    import base64
    import hashlib
    key_bytes = hashlib.sha256(secret_key).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)

    fernet = Fernet(fernet_key)
    decrypted = fernet.decrypt(encrypted_password.encode())
    return decrypted.decode()


def reset_database(app):
    """
    Drop all tables and recreate (DANGER: Use with caution!)

    Args:
        app: Flask application instance
    """
    with app.app_context():
        db.drop_all()
        logger.warning("All database tables dropped")
        db.create_all()
        logger.info("Database tables recreated")
        seed_default_data(app)
