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
    # Import blueprints (will be created in next phase)
    # from app.api.dashboard import dashboard_bp
    # from app.api.emails import emails_bp
    # from app.api.schedule import schedule_bp
    # from app.api.settings import settings_bp

    # Register blueprints
    # app.register_blueprint(dashboard_bp)
    # app.register_blueprint(emails_bp, url_prefix='/api/emails')
    # app.register_blueprint(schedule_bp, url_prefix='/api/schedule')
    # app.register_blueprint(settings_bp, url_prefix='/api/settings')

    # Placeholder route for now
    @app.route('/')
    def index():
        return {
            'status': 'ok',
            'app': app.config.get('APP_NAME'),
            'version': app.config.get('APP_VERSION'),
            'message': 'Postal Warmup API is running'
        }

    @app.route('/health')
    def health():
        """Health check endpoint"""
        return {'status': 'healthy'}, 200


def initialize_scheduler(app):
    """
    Initialize APScheduler for warmup tasks

    Args:
        app: Flask application instance
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    import atexit

    scheduler = BackgroundScheduler()

    # Parse DAILY_SEND_TIME (format: "HH:MM")
    send_time = app.config.get('DAILY_SEND_TIME', '09:00')
    hour, minute = send_time.split(':')

    # Schedule daily warmup task
    # This will be implemented in Phase 3 (Scheduler)
    # For now, just set up the scheduler infrastructure

    # Placeholder for future scheduled jobs
    # from app.core.warmup_scheduler import WarmupScheduler
    # warmup_scheduler = WarmupScheduler(app)
    # scheduler.add_job(
    #     func=warmup_scheduler.send_daily_batch,
    #     trigger=CronTrigger(hour=int(hour), minute=int(minute)),
    #     id='daily_warmup',
    #     name='Daily Warmup Email Batch',
    #     replace_existing=True
    # )

    scheduler.start()
    app.logger.info(f"APScheduler started (daily task at {send_time})")

    # Store scheduler in app config for access
    app.config['SCHEDULER'] = scheduler

    # Shutdown scheduler when app exits
    atexit.register(lambda: scheduler.shutdown())
