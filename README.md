# Postal Warmup - Email IP Warming Tool

An automated email warmup application for [Postal](https://postalserver.io/) mail servers. This tool helps establish IP reputation by gradually increasing email volume and simulating natural human email behavior.

## Features

- 📧 Automated email sending through Postal HTTP API
- 🤖 AI-generated email content via OpenAI (mixed types: transactional, newsletter, personal)
- 📊 Real-time statistics dashboard
- ✅ Inbox vs Spam detection via IMAP
- 👤 Human behavior simulation (mark as read, move to folders)
- ⏰ Configurable warmup schedules
- 🎯 Manual and automatic email sending
- 🔒 Secure credential management
- 🐳 Docker-ready deployment
- 💾 SQLite database (lightweight, no extra services)

## Quick Start

### Prerequisites

- Python 3.11+
- Postal mail server with API access
- OpenAI API key
- IMAP access to test email accounts

### Installation

1. Clone the repository:
```bash
git clone https://github.com/roberteinsle/postal-warmup.git
cd postal-warmup
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Initialize database:
```bash
python manage.py init-db
```

6. Run the application:
```bash
python manage.py run
```

The application will be available at `http://localhost:5000`

## Configuration

All configuration is done via environment variables in the `.env` file:

### Required Settings

- `POSTAL_API_KEY`: Your Postal server API key
- `POSTAL_BASE_URL`: URL to your Postal instance (e.g., https://postal.example.com)
- `OPENAI_API_KEY`: Your OpenAI API key
- `SENDER_ADDRESSES`: Comma-separated sender email addresses
- `RECIPIENT_ADDRESSES`: Comma-separated test recipient addresses
- `RECIPIENT_IMAP_PASSWORDS`: Format: `email1:password1,email2:password2`

### Optional Settings

- `DAILY_SEND_TIME`: Time to send daily batch (default: 09:00)
- `MIN_DELAY_BETWEEN_SENDS_SEC`: Minimum delay between emails (default: 2)
- `MAX_DELAY_BETWEEN_SENDS_SEC`: Maximum delay between emails (default: 5)
- `CHECK_DELAY_MINUTES`: Minutes to wait before checking delivery (default: 15)
- `MASTER_PASSWORD`: Password for settings page (default: change-me)

## Management CLI

The `manage.py` script provides various management commands:

### Database Commands

```bash
python manage.py init-db          # Initialize database
python manage.py reset-db          # Reset database (WARNING: destroys data)
python manage.py seed-db           # Seed with default data
```

### Testing Commands

```bash
python manage.py test-config       # Show current configuration
python manage.py test-db           # Display database statistics
python manage.py test-postal       # Test Postal API connection
python manage.py test-openai       # Test OpenAI API connection
python manage.py test-imap <email> <password>  # Test IMAP connection
python manage.py test-all          # Run all tests
```

### Running the Application

```bash
python manage.py run               # Run development server
python manage.py run --host 0.0.0.0 --port 5000  # Custom host/port
```

## Docker Deployment

### Build and Run

```bash
docker-compose up -d
```

The application will be available at `http://localhost:5000`

### Environment Variables

Set environment variables in `.env` file or pass them to docker-compose:

```bash
docker-compose --env-file .env up -d
```

## Project Structure

```
postal-warmup/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── config.py             # Configuration management
│   ├── models.py             # Database models
│   ├── database.py           # DB initialization
│   ├── core/                 # Business logic
│   │   ├── email_sender.py   # Postal API integration
│   │   ├── email_checker.py  # IMAP integration
│   │   ├── warmup_scheduler.py  # Scheduling logic
│   │   └── content_generator.py  # OpenAI integration
│   ├── api/                  # Flask routes
│   ├── templates/            # HTML templates
│   ├── static/               # CSS/JS assets
│   └── utils/                # Utilities
├── data/                     # SQLite database
├── logs/                     # Log files
├── manage.py                 # Management CLI
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker configuration
└── docker-compose.yml       # Docker Compose setup
```

## Default Warmup Schedule

The application comes with a default 15-day warmup schedule:

- Day 1: 5 emails
- Day 2: 10 emails
- Day 3: 15 emails
- ...
- Day 15: 100 emails

You can customize this schedule in the dashboard or directly in the database.

## API Endpoints

### Dashboard
- `GET /` - Main dashboard
- `GET /api/dashboard/stats` - Real-time statistics

### Emails
- `GET /emails` - Email list
- `POST /api/emails/send` - Manual send trigger
- `POST /api/emails/check-now` - Check delivery status

### Schedule
- `GET /schedule` - Schedule editor
- `GET /api/schedule` - Get schedule
- `POST /api/schedule` - Update schedule

### Settings
- `GET /settings` - Settings page
- `POST /api/settings/*` - Update settings

## Security Notes

- Never commit the `.env` file to version control
- Always use strong passwords in production
- The `.env.example` file is safe to commit (no real credentials)
- IMAP passwords are encrypted in the database using Fernet
- Use HTTPS in production for the dashboard

## Performance

Optimized for resource-constrained environments:

- **Memory footprint**: ~100 MB
- **Database**: SQLite (file-based, no extra service)
- **Scheduler**: APScheduler (no Redis/Celery)
- **Recommended VM**: 1 GB RAM, 1 Core

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this for your own Postal warmup needs.

## Author

Created by Robert Einsle (robert@einsle.com)

## Acknowledgments

- [Postal](https://postalserver.io/) - Open-source mail delivery platform
- [OpenAI](https://openai.com/) - AI-powered content generation
- [Flask](https://flask.palletsprojects.com/) - Python web framework
