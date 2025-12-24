# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Postal Warmup is an automated email warmup application for Postal mail servers. It gradually increases email volume to establish IP reputation through:
- AI-generated German emails via OpenAI
- Automated sending through Postal HTTP API
- IMAP-based delivery verification (inbox vs spam)
- Human behavior simulation (mark as read, move to folders)
- Configurable 15-day warmup schedules

**Target Environment**: Resource-constrained VMs (1 GB RAM, 1 Core)

## Common Commands

### Development Setup
```bash
# Initial setup
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Database initialization
python manage.py init-db

# Run development server
python manage.py run --port 5000
```

### Testing & Validation
```bash
# Test all integrations
python manage.py test-all

# Test individual components
python manage.py test-postal      # Postal API connection
python manage.py test-openai      # OpenAI API connection
python manage.py test-imap <email> <password>  # IMAP connection
python manage.py test-config      # Show configuration
python manage.py test-db          # Database statistics
```

### Database Management
```bash
python manage.py init-db          # Initialize/create tables
python manage.py seed-db          # Seed default 15-day schedule
python manage.py reset-db         # WARNING: Destroys all data
```

## Architecture

### Core Components Flow

```
┌─────────────────────────────────────────────────────────┐
│ WarmupScheduler (app/core/warmup_scheduler.py)         │
│ - Orchestrates entire warmup process                    │
│ - APScheduler integration (daily + 30min checks)        │
└──────────────┬──────────────────────────────────────────┘
               │
               ├─→ EmailContentGenerator (OpenAI GPT-3.5-turbo)
               │   - Generates German emails (transactional/newsletter/personal)
               │   - Fallback templates if API fails
               │
               ├─→ PostalEmailSender (Postal HTTP API)
               │   - Sends via /api/v1/send/message
               │   - Rate limiting: 2-5 sec between sends
               │
               └─→ IMAPEmailChecker (IMAP connection)
                   - Checks inbox vs spam folders
                   - Simulates human behavior (70% chance):
                     * Mark as read (80% chance)
                     * Move to folder (30% chance)
```

### Database Schema (SQLite)

**Critical relationships:**
- `WarmupSchedule.day` → defines target_emails per warmup day
- `WarmupExecution.schedule_day_id` → tracks actual execution per date
- `Email.check_scheduled_at` → controls when IMAP check runs
- `Statistic.date` → daily aggregated metrics

**Encryption:**
- IMAP passwords stored encrypted (Fernet) in `email_addresses.imap_password`
- Encryption key derived from `SECRET_KEY` in environment

### Flask Application Factory Pattern

**Blueprint Registration** (app/__init__.py):
- Dashboard Blueprint → `/` (main UI)
- Emails Blueprint → `/emails` (email management)
- Schedule Blueprint → `/schedule` (warmup plan editor)

**Scheduler Initialization:**
- Only runs when `TESTING=False`
- Creates two APScheduler jobs:
  1. Daily warmup batch (configurable time, default 09:00)
  2. Pending email checks (every 30 minutes)

### Configuration Architecture

All config via environment variables (.env file):

**Critical settings:**
- `POSTAL_API_KEY` + `POSTAL_BASE_URL` - Required for sending
- `OPENAI_API_KEY` - Required for content generation
- `SENDER_ADDRESSES` / `RECIPIENT_ADDRESSES` - Comma-separated
- `RECIPIENT_IMAP_PASSWORDS` - Format: `email1:pass1,email2:pass2`

**Parsing locations:**
- `app/config.py` - Environment variable parsing
- `app/database.py` - IMAP password encryption on seed

### Warmup Scheduler Workflow

1. **Daily Batch Execution** (`send_daily_batch()`):
   - Calculates current warmup day based on first execution
   - Retrieves schedule for current day
   - Sends `target_emails` with random delays
   - Creates `WarmupExecution` record
   - Each email gets `check_scheduled_at = now + CHECK_DELAY_MINUTES`

2. **Email Checking** (`check_pending_emails()`):
   - Queries emails where `check_scheduled_at <= now` and not yet checked
   - Connects via IMAP to each recipient
   - Updates `delivery_status` (inbox/spam/unknown)
   - Simulates human behavior for inbox emails
   - Updates daily `Statistic` record

3. **Manual Triggering** (`trigger_manual_send()`):
   - Bypasses schedule, sends N emails immediately
   - Used for testing or catch-up

### Email Content Generation

**OpenAI Integration** (app/core/content_generator.py):
- Model: `gpt-3.5-turbo` (cost-effective)
- System prompt: "Du bist ein hilfreicher Assistent, der realistische E-Mail-Inhalte auf Deutsch generiert."
- Temperature: 0.9 (high variety)
- Response format: `SUBJECT: [...]\\nBODY: [...]`
- **Fallback**: German templates if API fails

**Content Types:**
- `transactional` - Order confirmations, password resets
- `newsletter` - Product updates, tips
- `personal` - Questions, follow-ups, thanks
- `mixed` - Random selection

## Important Implementation Details

### Email Tracking State Machine

```
Email.status:          sent → failed/bounced
Email.delivery_status: pending → inbox/spam/unknown/failed
```

**Timing:**
- `sent_at` - When Postal API accepted email
- `check_scheduled_at` - When IMAP check should run (sent_at + CHECK_DELAY_MINUTES)
- `checked_at` - When IMAP check actually ran

### APScheduler Jobs

**Daily Warmup Job:**
- Trigger: CronTrigger (hour/minute from DAILY_SEND_TIME)
- Idempotent: Checks if today already executed via `WarmupExecution.completed_at`

**Email Check Job:**
- Trigger: IntervalTrigger (every 30 minutes)
- Batch limit: Max 50 emails per run

### Flask App Context Management

All database operations in `WarmupScheduler` wrapped with:
```python
with self.app.app_context():
    # Database queries here
```

This is required because APScheduler runs in background threads.

### IMAP Password Handling

**Encryption on seed** (app/database.py):
```python
from cryptography.fernet import Fernet
key = base64.urlsafe_b64encode(app.config['SECRET_KEY'][:32].encode().ljust(32)[:32])
cipher = Fernet(key)
encrypted = cipher.encrypt(password.encode()).decode()
```

**Decryption** (app/core/email_checker.py):
- Same process in reverse when connecting to IMAP

### German Language Requirement

**Critical:** All email content MUST be in German. This is a core requirement for the warmup to appear natural for the target IP addresses (German mail server).

**Enforcement:**
- OpenAI prompts explicitly request German
- Fallback templates are German
- System messages to OpenAI in German

## Development Workflow

### Adding New Email Content Types

1. Add type to `EmailContentGenerator.fallback_templates`
2. Add OpenAI prompt in `_generate_with_openai.prompts`
3. Update `Email.content_type` choices if needed

### Modifying Warmup Schedule

**Via Database:**
```python
from app.models import WarmupSchedule
schedule = WarmupSchedule.query.filter_by(day=1).first()
schedule.target_emails = 10
schedule.enabled = True
db.session.commit()
```

**Via Dashboard:**
- Navigate to `/schedule`
- Edit inline or use modal
- Bulk update available

### Testing Email Flow End-to-End

Use the test endpoints (only available in development):
```bash
# Send single email
curl -X POST http://localhost:5000/test/send-email \
  -H "Content-Type: application/json" \
  -d '{"content_type": "newsletter"}'

# Full cycle (send + wait + check)
curl -X POST http://localhost:5000/test/full-cycle \
  -H "Content-Type: application/json" \
  -d '{"check_delay": 30}'
```

## Dashboard API Patterns

### Real-time Updates

Dashboard auto-refreshes every 30 seconds:
```javascript
setInterval(loadDashboard, 30000);
```

**API Endpoints:**
- `/api/stats/overview` - Current warmup status, today's progress
- `/api/stats/chart` - Last 7 days for Chart.js visualization
- `/api/stats/recent-emails` - Last 10 emails for preview

### Chart.js Integration

Two charts on dashboard:
1. **Volume Chart** (Bar) - Sent/Inbox/Spam per day
2. **Success Rate Chart** (Line) - Success % and Spam % trends

Data fetched from `/api/stats/chart`, returns 7 days with fill for missing dates.

## Critical Files

- **app/core/warmup_scheduler.py** - Main orchestration logic (466 lines)
- **app/__init__.py** - Flask factory + scheduler initialization
- **app/models.py** - SQLAlchemy models, relationships, and calculation methods
- **app/database.py** - DB init + 15-day schedule seeding
- **manage.py** - CLI entry point with Click commands

## Performance Considerations

**Memory Optimization:**
- SQLite instead of PostgreSQL (no separate service)
- APScheduler instead of Celery + Redis
- Server-side rendering instead of SPA framework

**Database Optimization:**
- `Email.query.limit(50)` on pending checks
- Pagination on email list (25 per page)
- Indexes on frequently queried fields (not explicitly defined, SQLAlchemy defaults)

**Rate Limiting:**
- Random delay between sends: `random.uniform(MIN_DELAY, MAX_DELAY)`
- Default: 2-5 seconds between emails
- IMAP checks batch limited to 50 emails per run

## Deployment Notes

**Docker:**
- Dockerfile creates non-root user `postal_user`
- Volumes: `./data` (SQLite), `./logs`
- Port: 5000

**Production Checklist:**
1. Change `SECRET_KEY` from default
2. Set `MASTER_PASSWORD` for settings page
3. Use HTTPS for dashboard access
4. Set `FLASK_ENV=production`
5. Consider using Gunicorn instead of Flask dev server

## Known Limitations

1. **IMAP Compatibility**: Some compatibility issues with Python 3.14 (non-critical, core functionality works)
2. **Duplicate Email Addresses**: Database seed may fail if same email used as sender AND recipient (constraint error, non-blocking)
3. **Windows Console Encoding**: Unicode symbols in manage.py output may fail on Windows CMD (cosmetic only)
