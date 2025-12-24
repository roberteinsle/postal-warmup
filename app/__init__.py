"""
Flask Application Factory for Postal Warmup
"""
from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


def create_app(config_name=None):
    """
    Create and configure Flask application

    Args:
        config_name: Configuration name (development, production, testing)

    Returns:
        Flask app instance
    """
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    from app.config import config
    app.config.from_object(config[config_name])

    # Validate configuration
    try:
        from app.config import Config
        Config.validate()
    except ValueError as e:
        app.logger.error(f"Configuration validation failed: {e}")
        if config_name == 'production':
            raise

    # Initialize extensions
    initialize_extensions(app)

    # Setup logging
    from app.utils.logger import setup_logger
    setup_logger(app)

    # Register blueprints
    register_blueprints(app)

    # Initialize database
    with app.app_context():
        from app.database import init_db
        try:
            init_db(app)
            app.logger.info("Database initialized successfully")
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")
            if config_name == 'production':
                raise

    # Initialize scheduler (only in production/development, not testing)
    if not app.config.get('TESTING', False):
        initialize_scheduler(app)

    app.logger.info(f"Postal Warmup Application initialized (env: {config_name})")

    return app


def initialize_extensions(app):
    """
    Initialize Flask extensions

    Args:
        app: Flask application instance
    """
    from app.models import db

    # Initialize SQLAlchemy
    db.init_app(app)

    # Flask-Migrate (optional, for future migrations)
    # from flask_migrate import Migrate
    # migrate = Migrate(app, db)


def register_blueprints(app):
    """
    Register Flask blueprints

    Args:
        app: Flask application instance
    """
    # Import blueprints
    from app.api.dashboard import dashboard_bp
    from app.api.emails import emails_bp
    from app.api.schedule import schedule_bp

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(emails_bp, url_prefix='/emails')
    app.register_blueprint(schedule_bp, url_prefix='/schedule')

    @app.route('/health')
    def health():
        """Health check endpoint"""
        return {'status': 'healthy'}, 200

    @app.route('/debug/config')
    def debug_config():
        """Debug endpoint to show configuration (development only)"""
        if app.config.get('FLASK_ENV') != 'development':
            return {'error': 'Only available in development mode'}, 403

        return {
            'environment': app.config.get('FLASK_ENV'),
            'debug': app.config.get('DEBUG'),
            'database': app.config.get('SQLALCHEMY_DATABASE_URI'),
            'postal_url': app.config.get('POSTAL_BASE_URL'),
            'postal_api_configured': bool(app.config.get('POSTAL_API_KEY')),
            'openai_api_configured': bool(app.config.get('OPENAI_API_KEY')),
            'imap_host': f"{app.config.get('IMAP_HOST')}:{app.config.get('IMAP_PORT')}",
            'sender_addresses': app.config.get('SENDER_ADDRESSES'),
            'recipient_addresses': app.config.get('RECIPIENT_ADDRESSES'),
            'daily_send_time': app.config.get('DAILY_SEND_TIME'),
            'check_delay_minutes': app.config.get('CHECK_DELAY_MINUTES')
        }

    @app.route('/debug/database')
    def debug_database():
        """Debug endpoint to show database statistics"""
        from app.models import db, Email, WarmupSchedule, EmailAddress, Statistic

        try:
            stats = {
                'emails': Email.query.count(),
                'warmup_schedule_days': WarmupSchedule.query.count(),
                'email_addresses': EmailAddress.query.count(),
                'statistics_records': Statistic.query.count(),
                'database_file': app.config.get('SQLALCHEMY_DATABASE_URI')
            }

            # Get first 5 warmup schedule entries
            schedules = WarmupSchedule.query.order_by(WarmupSchedule.day).limit(5).all()
            stats['warmup_schedule_preview'] = [
                {
                    'day': s.day,
                    'target_emails': s.target_emails,
                    'enabled': s.enabled
                }
                for s in schedules
            ]

            # Get email addresses
            addresses = EmailAddress.query.all()
            stats['email_addresses_list'] = [
                {
                    'email': a.email,
                    'type': a.type,
                    'verified': a.verified
                }
                for a in addresses
            ]

            return stats
        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/test/send-email', methods=['POST'])
    def test_send_email():
        """Test endpoint to send a single email"""
        from app.core.email_sender import PostalEmailSender
        from app.core.content_generator import EmailContentGenerator
        from flask import request

        try:
            # Get parameters
            data = request.get_json() or {}
            sender = data.get('sender', app.config.get('SENDER_ADDRESSES', [''])[0])
            recipient = data.get('recipient', app.config.get('RECIPIENT_ADDRESSES', [''])[0])
            content_type = data.get('content_type', 'mixed')

            # Initialize services
            postal_sender = PostalEmailSender(
                app.config.get('POSTAL_API_KEY'),
                app.config.get('POSTAL_BASE_URL')
            )

            content_generator = EmailContentGenerator(
                app.config.get('OPENAI_API_KEY')
            )

            # Generate content
            subject, body = content_generator.generate_email(content_type)

            # Send email
            result = postal_sender.send_email(sender, recipient, subject, body)

            return {
                'success': result['success'],
                'message_id': result.get('message_id'),
                'sender': sender,
                'recipient': recipient,
                'subject': subject,
                'body': body[:100] + '...' if len(body) > 100 else body,
                'content_type': content_type,
                'result': result
            }

        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/test/check-email', methods=['POST'])
    def test_check_email():
        """Test endpoint to check email delivery"""
        from app.core.email_checker import IMAPEmailChecker
        from flask import request

        try:
            # Get parameters
            data = request.get_json() or {}
            email_address = data.get('email', app.config.get('RECIPIENT_ADDRESSES', [''])[0])
            password = app.config.get('RECIPIENT_IMAP_PASSWORDS', {}).get(email_address, '')
            subject = data.get('subject')
            message_id = data.get('message_id')

            if not password:
                return {'error': f'No IMAP password configured for {email_address}'}, 400

            # Initialize checker
            checker = IMAPEmailChecker(
                app.config.get('IMAP_HOST'),
                app.config.get('IMAP_PORT'),
                app.config.get('IMAP_USE_SSL')
            )

            # Check email
            result = checker.check_email(email_address, password, message_id, subject)

            return {
                'email': email_address,
                'result': result
            }

        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/test/full-cycle', methods=['POST'])
    def test_full_cycle():
        """Test endpoint for full send + check cycle"""
        from app.core.email_sender import PostalEmailSender
        from app.core.content_generator import EmailContentGenerator
        from app.core.email_checker import IMAPEmailChecker
        from flask import request
        import time

        try:
            # Get parameters
            data = request.get_json() or {}
            sender = data.get('sender', app.config.get('SENDER_ADDRESSES', [''])[0])
            recipient = data.get('recipient', app.config.get('RECIPIENT_ADDRESSES', [''])[0])
            content_type = data.get('content_type', 'mixed')
            check_delay = data.get('check_delay', 30)  # seconds

            # Initialize services
            postal_sender = PostalEmailSender(
                app.config.get('POSTAL_API_KEY'),
                app.config.get('POSTAL_BASE_URL')
            )

            content_generator = EmailContentGenerator(
                app.config.get('OPENAI_API_KEY')
            )

            checker = IMAPEmailChecker(
                app.config.get('IMAP_HOST'),
                app.config.get('IMAP_PORT'),
                app.config.get('IMAP_USE_SSL')
            )

            # Step 1: Generate content
            subject, body = content_generator.generate_email(content_type)

            # Step 2: Send email
            send_result = postal_sender.send_email(sender, recipient, subject, body)

            if not send_result['success']:
                return {
                    'success': False,
                    'step': 'send',
                    'error': send_result.get('error'),
                    'result': send_result
                }, 500

            # Step 3: Wait before checking
            app.logger.info(f"Waiting {check_delay}s before checking...")
            time.sleep(check_delay)

            # Step 4: Check delivery
            password = app.config.get('RECIPIENT_IMAP_PASSWORDS', {}).get(recipient, '')
            if not password:
                return {
                    'success': True,
                    'step': 'check_skipped',
                    'message': f'No IMAP password for {recipient}',
                    'send_result': send_result
                }

            check_result = checker.check_email(recipient, password, None, subject)

            return {
                'success': True,
                'sender': sender,
                'recipient': recipient,
                'subject': subject,
                'content_type': content_type,
                'send_result': send_result,
                'check_result': check_result,
                'delivery_status': check_result.get('delivery_status'),
                'found_in_folder': check_result.get('folder')
            }

        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/test/batch-send', methods=['POST'])
    def test_batch_send():
        """Test endpoint for batch sending via warmup scheduler"""
        from flask import request

        try:
            # Get parameters
            data = request.get_json() or {}
            count = data.get('count', 3)  # Default: 3 emails
            senders = data.get('senders')
            recipients = data.get('recipients')

            # Get warmup scheduler from app config
            warmup_scheduler = app.config.get('WARMUP_SCHEDULER')
            if not warmup_scheduler:
                return {'error': 'Warmup scheduler not initialized'}, 500

            # Trigger manual send
            result = warmup_scheduler.trigger_manual_send(
                count=count,
                senders=senders,
                recipients=recipients
            )

            return result

        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/test/check-pending', methods=['POST'])
    def test_check_pending():
        """Test endpoint to manually trigger pending email checks"""
        try:
            # Get warmup scheduler from app config
            warmup_scheduler = app.config.get('WARMUP_SCHEDULER')
            if not warmup_scheduler:
                return {'error': 'Warmup scheduler not initialized'}, 500

            # Check pending emails
            result = warmup_scheduler.check_pending_emails()

            return result

        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/test/warmup-progress', methods=['GET'])
    def test_warmup_progress():
        """Test endpoint to get current warmup progress"""
        try:
            # Get warmup scheduler from app config
            warmup_scheduler = app.config.get('WARMUP_SCHEDULER')
            if not warmup_scheduler:
                return {'error': 'Warmup scheduler not initialized'}, 500

            # Get progress
            progress = warmup_scheduler.get_warmup_progress()

            return progress

        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/test/daily-batch', methods=['POST'])
    def test_daily_batch():
        """Test endpoint to manually trigger daily batch"""
        try:
            # Get warmup scheduler from app config
            warmup_scheduler = app.config.get('WARMUP_SCHEDULER')
            if not warmup_scheduler:
                return {'error': 'Warmup scheduler not initialized'}, 500

            # Send daily batch
            result = warmup_scheduler.send_daily_batch()

            return result

        except Exception as e:
            return {'error': str(e)}, 500


def initialize_scheduler(app):
    """
    Initialize APScheduler for warmup tasks

    Args:
        app: Flask application instance
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from app.core.warmup_scheduler import WarmupScheduler
    import atexit

    scheduler = BackgroundScheduler()
    warmup_scheduler = WarmupScheduler(app)

    # Parse DAILY_SEND_TIME (format: "HH:MM")
    send_time = app.config.get('DAILY_SEND_TIME', '09:00')
    hour, minute = send_time.split(':')

    # Schedule daily warmup batch
    scheduler.add_job(
        func=warmup_scheduler.send_daily_batch,
        trigger=CronTrigger(hour=int(hour), minute=int(minute)),
        id='daily_warmup',
        name='Daily Warmup Email Batch',
        replace_existing=True
    )

    # Schedule email checking every 30 minutes
    scheduler.add_job(
        func=warmup_scheduler.check_pending_emails,
        trigger='interval',
        minutes=30,
        id='check_emails',
        name='Check Pending Email Delivery',
        replace_existing=True
    )

    scheduler.start()
    app.logger.info(f"APScheduler started (daily warmup at {send_time}, email checks every 30min)")

    # Store scheduler and warmup_scheduler in app config for access
    app.config['SCHEDULER'] = scheduler
    app.config['WARMUP_SCHEDULER'] = warmup_scheduler

    # Shutdown scheduler when app exits
    atexit.register(lambda: scheduler.shutdown())
