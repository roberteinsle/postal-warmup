"""
Emails API Blueprint - Email management and history
"""
from flask import Blueprint, render_template, jsonify, request
from app.models import db, Email
from datetime import datetime, timedelta
from sqlalchemy import or_

emails_bp = Blueprint('emails', __name__)


@emails_bp.route('/')
def index():
    """
    Render emails list page
    """
    return render_template('emails.html')


@emails_bp.route('/api/list')
def list_emails():
    """
    Get paginated list of emails with optional filters

    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 25)
        status (str): Filter by status
        delivery_status (str): Filter by delivery status
        search (str): Search in subject/sender/recipient

    Returns:
        JSON with paginated email list
    """
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status_filter = request.args.get('status')
        delivery_filter = request.args.get('delivery_status')
        search = request.args.get('search', '').strip()

        # Build query
        query = Email.query

        # Apply filters
        if status_filter:
            query = query.filter(Email.status == status_filter)

        if delivery_filter:
            query = query.filter(Email.delivery_status == delivery_filter)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Email.subject.like(search_pattern),
                    Email.sender.like(search_pattern),
                    Email.recipient.like(search_pattern)
                )
            )

        # Order by sent_at descending
        query = query.order_by(Email.sent_at.desc())

        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Format results
        emails = []
        for email in pagination.items:
            emails.append({
                'id': email.id,
                'sender': email.sender,
                'recipient': email.recipient,
                'subject': email.subject,
                'content_type': email.content_type,
                'status': email.status,
                'delivery_status': email.delivery_status,
                'sent_at': email.sent_at.isoformat() if email.sent_at else None,
                'checked_at': email.checked_at.isoformat() if email.checked_at else None,
                'is_read': email.is_read,
                'moved_to_folder': email.moved_to_folder
            })

        return jsonify({
            'emails': emails,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@emails_bp.route('/api/<int:email_id>')
def get_email(email_id):
    """
    Get detailed information about a specific email

    Args:
        email_id: Email ID

    Returns:
        JSON with full email details
    """
    try:
        email = Email.query.get_or_404(email_id)

        return jsonify({
            'id': email.id,
            'sender': email.sender,
            'recipient': email.recipient,
            'subject': email.subject,
            'body': email.body,
            'content_type': email.content_type,
            'postal_message_id': email.postal_message_id,
            'status': email.status,
            'delivery_status': email.delivery_status,
            'sent_at': email.sent_at.isoformat() if email.sent_at else None,
            'check_scheduled_at': email.check_scheduled_at.isoformat() if email.check_scheduled_at else None,
            'checked_at': email.checked_at.isoformat() if email.checked_at else None,
            'is_read': email.is_read,
            'moved_to_folder': email.moved_to_folder,
            'created_at': email.created_at.isoformat() if email.created_at else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@emails_bp.route('/api/stats')
def email_stats():
    """
    Get email statistics summary

    Returns:
        JSON with email counts by status and delivery status
    """
    try:
        total = Email.query.count()

        # Status counts
        sent = Email.query.filter_by(status='sent').count()
        failed = Email.query.filter_by(status='failed').count()
        bounced = Email.query.filter_by(status='bounced').count()

        # Delivery status counts
        pending = Email.query.filter_by(delivery_status='pending').count()
        inbox = Email.query.filter_by(delivery_status='inbox').count()
        spam = Email.query.filter_by(delivery_status='spam').count()
        unknown = Email.query.filter_by(delivery_status='unknown').count()

        # Content type counts
        from sqlalchemy import func
        content_types = db.session.query(
            Email.content_type,
            func.count(Email.id)
        ).group_by(Email.content_type).all()

        content_type_stats = {ct: count for ct, count in content_types}

        return jsonify({
            'total': total,
            'by_status': {
                'sent': sent,
                'failed': failed,
                'bounced': bounced
            },
            'by_delivery': {
                'pending': pending,
                'inbox': inbox,
                'spam': spam,
                'unknown': unknown
            },
            'by_content_type': content_type_stats
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@emails_bp.route('/api/send-manual', methods=['POST'])
def send_manual():
    """
    Manually trigger sending emails

    Request Body:
        count (int): Number of emails to send
        senders (list): Optional list of sender addresses
        recipients (list): Optional list of recipient addresses

    Returns:
        JSON with send results
    """
    try:
        from flask import current_app

        data = request.get_json() or {}
        count = data.get('count', 1)
        senders = data.get('senders')
        recipients = data.get('recipients')

        # Get warmup scheduler
        warmup_scheduler = current_app.config.get('WARMUP_SCHEDULER')
        if not warmup_scheduler:
            return jsonify({'error': 'Warmup scheduler not initialized'}), 500

        # Trigger manual send
        result = warmup_scheduler.trigger_manual_send(
            count=count,
            senders=senders,
            recipients=recipients
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@emails_bp.route('/api/check-pending', methods=['POST'])
def check_pending():
    """
    Manually trigger checking of pending emails

    Returns:
        JSON with check results
    """
    try:
        from flask import current_app

        # Get warmup scheduler
        warmup_scheduler = current_app.config.get('WARMUP_SCHEDULER')
        if not warmup_scheduler:
            return jsonify({'error': 'Warmup scheduler not initialized'}), 500

        # Check pending emails
        result = warmup_scheduler.check_pending_emails()

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
