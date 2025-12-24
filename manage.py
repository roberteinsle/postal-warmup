#!/usr/bin/env python3
"""
Management CLI for Postal Warmup Application
"""
import click
from app import create_app
from app.models import db
from app.database import init_db, reset_database, seed_default_data


@click.group()
def cli():
    """Postal Warmup Management CLI"""
    pass


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=5000, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def run(host, port, debug):
    """Run the Flask development server"""
    app = create_app()
    click.echo(f"Starting Postal Warmup on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


@cli.command()
def init_db_command():
    """Initialize the database"""
    app = create_app()
    click.echo("Initializing database...")
    init_db(app)
    click.echo("Database initialized successfully!")


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to reset the database? All data will be lost!')
def reset_db():
    """Reset the database (WARNING: Destroys all data!)"""
    app = create_app()
    click.echo("Resetting database...")
    reset_database(app)
    click.echo("Database reset successfully!")


@cli.command()
def seed_db():
    """Seed database with default data"""
    app = create_app()
    click.echo("Seeding database...")
    seed_default_data(app)
    click.echo("Database seeded successfully!")


@cli.command()
def test_config():
    """Test configuration and display settings"""
    app = create_app()

    click.echo("\n=== Postal Warmup Configuration ===\n")
    click.echo(f"App Name: {app.config.get('APP_NAME')}")
    click.echo(f"Version: {app.config.get('APP_VERSION')}")
    click.echo(f"Environment: {app.config.get('FLASK_ENV')}")
    click.echo(f"Debug: {app.config.get('DEBUG')}")
    click.echo(f"\nDatabase: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

    click.echo(f"\nPostal URL: {app.config.get('POSTAL_BASE_URL')}")
    click.echo(f"Postal API Key: {'Set' if app.config.get('POSTAL_API_KEY') else 'NOT SET'}")

    click.echo(f"\nOpenAI API Key: {'Set' if app.config.get('OPENAI_API_KEY') else 'NOT SET'}")

    click.echo(f"\nIMAP Host: {app.config.get('IMAP_HOST')}:{app.config.get('IMAP_PORT')}")
    click.echo(f"IMAP SSL: {app.config.get('IMAP_USE_SSL')}")

    sender_addrs = app.config.get('SENDER_ADDRESSES', [])
    click.echo(f"\nSender Addresses ({len(sender_addrs)}):")
    for addr in sender_addrs:
        click.echo(f"  - {addr}")

    recipient_addrs = app.config.get('RECIPIENT_ADDRESSES', [])
    click.echo(f"\nRecipient Addresses ({len(recipient_addrs)}):")
    for addr in recipient_addrs:
        click.echo(f"  - {addr}")

    click.echo(f"\nDaily Send Time: {app.config.get('DAILY_SEND_TIME')}")
    click.echo(f"Delay Between Sends: {app.config.get('MIN_DELAY_BETWEEN_SENDS')}-{app.config.get('MAX_DELAY_BETWEEN_SENDS')}s")
    click.echo(f"Check Delay: {app.config.get('CHECK_DELAY_MINUTES')} minutes")

    click.echo(f"\nLog Level: {app.config.get('LOG_LEVEL')}")
    click.echo(f"Log File: {app.config.get('LOG_FILE')}")

    click.echo("\n")


@cli.command()
def test_db():
    """Test database connection and display stats"""
    app = create_app()

    with app.app_context():
        from app.models import Email, WarmupSchedule, EmailAddress, Statistic

        click.echo("\n=== Database Statistics ===\n")
        click.echo(f"Emails: {Email.query.count()}")
        click.echo(f"Warmup Schedule Entries: {WarmupSchedule.query.count()}")
        click.echo(f"Email Addresses: {EmailAddress.query.count()}")
        click.echo(f"Statistics Records: {Statistic.query.count()}")

        # Show warmup schedule
        schedules = WarmupSchedule.query.order_by(WarmupSchedule.day).limit(10).all()
        if schedules:
            click.echo("\nWarmup Schedule (first 10 days):")
            for schedule in schedules:
                status = "✓" if schedule.enabled else "✗"
                click.echo(f"  Day {schedule.day}: {schedule.target_emails} emails {status}")

        # Show email addresses
        addresses = EmailAddress.query.all()
        if addresses:
            click.echo("\nEmail Addresses:")
            for addr in addresses:
                click.echo(f"  [{addr.type}] {addr.email}")

        click.echo("\n")


@cli.command()
@click.argument('email')
@click.argument('password')
def test_imap(email, password):
    """Test IMAP connection"""
    app = create_app()

    click.echo(f"\nTesting IMAP connection to {app.config.get('IMAP_HOST')}...")

    try:
        import imapclient

        client = imapclient.IMAPClient(
            app.config.get('IMAP_HOST'),
            port=app.config.get('IMAP_PORT'),
            ssl=app.config.get('IMAP_USE_SSL')
        )
        client.login(email, password)

        click.echo(f"✓ Successfully connected as {email}")

        # List folders
        folders = client.list_folders()
        click.echo(f"\nFolders ({len(folders)}):")
        for folder in folders[:10]:  # Show first 10
            click.echo(f"  - {folder[2]}")

        client.logout()
        click.echo("\n✓ IMAP test successful!\n")

    except Exception as e:
        click.echo(f"\n✗ IMAP test failed: {e}\n")


@cli.command()
def test_postal():
    """Test Postal API connection"""
    app = create_app()
    import requests

    click.echo(f"\nTesting Postal API connection to {app.config.get('POSTAL_BASE_URL')}...")

    api_key = app.config.get('POSTAL_API_KEY')
    if not api_key:
        click.echo("✗ POSTAL_API_KEY not set\n")
        return

    try:
        # Test API endpoint (get server info)
        url = f"{app.config.get('POSTAL_BASE_URL')}/api/v1/messages/deliveries"
        headers = {
            'X-Server-API-Key': api_key,
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code in [200, 401, 403]:
            click.echo(f"✓ Postal API is reachable (status: {response.status_code})")
            if response.status_code == 401:
                click.echo("  ⚠ API Key may be invalid (401 Unauthorized)")
            elif response.status_code == 403:
                click.echo("  ⚠ API Key may lack permissions (403 Forbidden)")
            else:
                click.echo("  ✓ API Key appears valid")
        else:
            click.echo(f"✗ Unexpected response: {response.status_code}")

        click.echo("")

    except Exception as e:
        click.echo(f"✗ Postal API test failed: {e}\n")


@cli.command()
def test_openai():
    """Test OpenAI API connection"""
    app = create_app()

    click.echo("\nTesting OpenAI API connection...")

    api_key = app.config.get('OPENAI_API_KEY')
    if not api_key:
        click.echo("✗ OPENAI_API_KEY not set\n")
        return

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        # Simple test: list models (lightweight operation)
        models = client.models.list()

        click.echo("✓ OpenAI API connection successful")
        click.echo(f"  Available models: {len(list(models.data))}")
        click.echo("")

    except Exception as e:
        click.echo(f"✗ OpenAI API test failed: {e}\n")


@cli.command()
def test_all():
    """Run all connection tests"""
    app = create_app()

    click.echo("\n" + "="*50)
    click.echo("Running All Connection Tests")
    click.echo("="*50)

    # Test configuration
    test_config.invoke(click.Context(test_config))

    # Test database
    test_db.invoke(click.Context(test_db))

    # Test Postal
    test_postal.invoke(click.Context(test_postal))

    # Test OpenAI
    test_openai.invoke(click.Context(test_openai))

    click.echo("="*50)
    click.echo("Tests Complete")
    click.echo("="*50 + "\n")


if __name__ == '__main__':
    cli()
