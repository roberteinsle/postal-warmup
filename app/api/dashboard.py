"""
Dashboard API Blueprint - Main dashboard with statistics and overview
"""
from flask import Blueprint, render_template, jsonify
from app.models import db, Email, WarmupSchedule, WarmupExecution, Statistic
from datetime import date, datetime, timedelta
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """
    Render main dashboard page
    """
    return render_template('dashboard.html')


@dashboard_bp.route('/api/stats/overview')
def stats_overview():
    """
    Get overview statistics for dashboard

    Returns:
        JSON with current warmup status and key metrics
    """
    try:
        # Get current warmup day
        first_execution = WarmupExecution.query.order_by(
            WarmupExecution.created_at.asc()
        ).first()

        current_day = 1
        if first_execution:
            days_since_start = (date.today() - first_execution.date).days
            current_day = days_since_start + 1

        # Get total days in schedule
        total_days = WarmupSchedule.query.filter_by(enabled=True).count()

        # Get today's schedule
        today_schedule = WarmupSchedule.query.filter_by(
            day=current_day,
            enabled=True
        ).first()

        # Get today's execution
        today_execution = WarmupExecution.query.filter_by(
            date=date.today()
        ).first()

        # Overall email statistics
        total_sent = Email.query.count()
        total_inbox = Email.query.filter_by(delivery_status='inbox').count()
        total_spam = Email.query.filter_by(delivery_status='spam').count()
        total_pending = Email.query.filter_by(delivery_status='pending').count()

        # Calculate rates
        success_rate = (total_inbox / total_sent * 100) if total_sent > 0 else 0
        spam_rate = (total_spam / total_sent * 100) if total_sent > 0 else 0

        # Today's statistics
        today_stats = Statistic.query.filter_by(date=date.today()).first()
        today_sent = today_stats.emails_sent if today_stats else 0
        today_inbox = today_stats.emails_inbox if today_stats else 0
        today_spam = today_stats.emails_spam if today_stats else 0

        return jsonify({
            'warmup': {
                'current_day': current_day,
                'total_days': total_days,
                'progress_percent': round((current_day / total_days * 100), 1) if total_days > 0 else 0,
                'today_target': today_schedule.target_emails if today_schedule else 0,
                'today_sent': today_execution.sent_count if today_execution else 0,
                'today_completed': bool(today_execution and today_execution.completed_at) if today_execution else False
            },
            'overall': {
                'total_sent': total_sent,
                'total_inbox': total_inbox,
                'total_spam': total_spam,
                'total_pending': total_pending,
                'success_rate': round(success_rate, 2),
                'spam_rate': round(spam_rate, 2)
            },
            'today': {
                'sent': today_sent,
                'inbox': today_inbox,
                'spam': today_spam,
                'success_rate': round((today_inbox / today_sent * 100), 2) if today_sent > 0 else 0
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/stats/chart')
def stats_chart():
    """
    Get statistics for chart visualization (last 7 days)

    Returns:
        JSON with daily statistics for charts
    """
    try:
        # Get last 7 days of statistics
        seven_days_ago = date.today() - timedelta(days=6)
        stats = Statistic.query.filter(
            Statistic.date >= seven_days_ago
        ).order_by(Statistic.date.asc()).all()

        # Fill in missing days with zeros
        chart_data = []
        for i in range(7):
            current_date = seven_days_ago + timedelta(days=i)
            stat = next((s for s in stats if s.date == current_date), None)

            if stat:
                chart_data.append({
                    'date': str(current_date),
                    'sent': stat.emails_sent,
                    'inbox': stat.emails_inbox,
                    'spam': stat.emails_spam,
                    'success_rate': round(stat.success_rate, 2),
                    'spam_rate': round(stat.spam_rate, 2)
                })
            else:
                chart_data.append({
                    'date': str(current_date),
                    'sent': 0,
                    'inbox': 0,
                    'spam': 0,
                    'success_rate': 0,
                    'spam_rate': 0
                })

        return jsonify(chart_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/stats/recent-emails')
def recent_emails():
    """
    Get recent emails for dashboard preview

    Returns:
        JSON with last 10 sent emails
    """
    try:
        emails = Email.query.order_by(
            Email.sent_at.desc()
        ).limit(10).all()

        email_list = []
        for email in emails:
            email_list.append({
                'id': email.id,
                'sender': email.sender,
                'recipient': email.recipient,
                'subject': email.subject,
                'content_type': email.content_type,
                'status': email.status,
                'delivery_status': email.delivery_status,
                'sent_at': email.sent_at.isoformat() if email.sent_at else None,
                'checked_at': email.checked_at.isoformat() if email.checked_at else None,
                'is_read': email.is_read
            })

        return jsonify(email_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/scheduler/status')
def scheduler_status():
    """
    Get current scheduler status and next scheduled jobs

    Returns:
        JSON with scheduler information
    """
    try:
        from flask import current_app

        scheduler = current_app.config.get('SCHEDULER')
        if not scheduler:
            return jsonify({'error': 'Scheduler not initialized'}), 500

        jobs = []
        for job in scheduler.get_jobs():
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': next_run,
                'trigger': str(job.trigger)
            })

        return jsonify({
            'running': scheduler.running,
            'jobs': jobs
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
