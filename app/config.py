"""
Configuration management for Postal Warmup Application
"""
import os
from datetime import datetime


class Config:
    """Base configuration class"""

    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production-!!!-IMPORTANT')

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///./data/warmup.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG

    # Postal Configuration
    POSTAL_API_KEY = os.getenv('POSTAL_API_KEY')
    POSTAL_BASE_URL = os.getenv('POSTAL_BASE_URL', 'https://postal.einsle.cloud')

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # IMAP Configuration
    IMAP_HOST = os.getenv('IMAP_HOST', 'mail.einsle.cloud')
    IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
    IMAP_USE_SSL = os.getenv('IMAP_USE_SSL', 'true').lower() == 'true'

    # Security
    MASTER_PASSWORD = os.getenv('MASTER_PASSWORD', 'change-me')

    # Email Addresses
    SENDER_ADDRESSES = [
        addr.strip()
        for addr in os.getenv('SENDER_ADDRESSES', '').split(',')
        if addr.strip()
    ]
    RECIPIENT_ADDRESSES = [
        addr.strip()
        for addr in os.getenv('RECIPIENT_ADDRESSES', '').split(',')
        if addr.strip()
    ]

    # IMAP Passwords (format: email1:pass1,email2:pass2)
    _recipient_passwords_raw = os.getenv('RECIPIENT_IMAP_PASSWORDS', '')
    RECIPIENT_IMAP_PASSWORDS = {}
    if _recipient_passwords_raw:
        for item in _recipient_passwords_raw.split(','):
            if ':' in item:
                email, password = item.split(':', 1)
                RECIPIENT_IMAP_PASSWORDS[email.strip()] = password.strip()

    # Warmup Settings
    DAILY_SEND_TIME = os.getenv('DAILY_SEND_TIME', '09:00')
    MIN_DELAY_BETWEEN_SENDS = int(os.getenv('MIN_DELAY_BETWEEN_SENDS_SEC', '2'))
    MAX_DELAY_BETWEEN_SENDS = int(os.getenv('MAX_DELAY_BETWEEN_SENDS_SEC', '5'))
    CHECK_DELAY_MINUTES = int(os.getenv('CHECK_DELAY_MINUTES', '15'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/warmup.log')

    # GitHub Info (for display only)
    GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', 'roberteinsle')
    GITHUB_EMAIL = os.getenv('GITHUB_EMAIL', 'robert@einsle.com')

    # Application Settings
    APP_NAME = 'Postal Warmup'
    APP_VERSION = '1.0.0'

    @staticmethod
    def validate():
        """Validate critical configuration"""
        errors = []

        if not Config.SECRET_KEY or Config.SECRET_KEY == 'dev-key-change-in-production-!!!-IMPORTANT':
            if Config.FLASK_ENV == 'production':
                errors.append("SECRET_KEY must be set in production!")

        if not Config.POSTAL_API_KEY:
            errors.append("POSTAL_API_KEY is required")

        if not Config.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")

        if not Config.SENDER_ADDRESSES:
            errors.append("At least one SENDER_ADDRESS is required")

        if not Config.RECIPIENT_ADDRESSES:
            errors.append("At least one RECIPIENT_ADDRESS is required")

        if errors:
            error_msg = "Configuration Errors:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ValueError(error_msg)

        return True


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on FLASK_ENV"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
