"""
Schedule API Blueprint - Warmup schedule management
"""
from flask import Blueprint, render_template, jsonify, request
from app.models import db, WarmupSchedule, WarmupExecution
from datetime import datetime, date

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('/')
def index():
    """
    Render schedule editor page
    """
    return render_template('schedule.html')


@schedule_bp.route('/api/list')
def list_schedule():
    """
    Get complete warmup schedule

    Returns:
        JSON with all schedule days
    """
    try:
        schedules = WarmupSchedule.query.order_by(WarmupSchedule.day.asc()).all()

        schedule_list = []
        for schedule in schedules:
            # Get execution history for this day
            executions = WarmupExecution.query.filter_by(
                schedule_day_id=schedule.id
            ).order_by(WarmupExecution.date.desc()).limit(5).all()

            execution_history = []
            for exec in executions:
                execution_history.append({
                    'date': str(exec.date),
                    'sent_count': exec.sent_count,
                    'completed': bool(exec.completed_at)
                })

            schedule_list.append({
                'id': schedule.id,
                'day': schedule.day,
                'target_emails': schedule.target_emails,
                'enabled': schedule.enabled,
                'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
                'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None,
                'execution_history': execution_history
            })

        return jsonify(schedule_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/<int:schedule_id>')
def get_schedule(schedule_id):
    """
    Get specific schedule day

    Args:
        schedule_id: Schedule ID

    Returns:
        JSON with schedule details
    """
    try:
        schedule = WarmupSchedule.query.get_or_404(schedule_id)

        return jsonify({
            'id': schedule.id,
            'day': schedule.day,
            'target_emails': schedule.target_emails,
            'enabled': schedule.enabled,
            'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
            'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """
    Update schedule day

    Args:
        schedule_id: Schedule ID

    Request Body:
        target_emails (int): Number of emails to send
        enabled (bool): Whether this day is enabled

    Returns:
        JSON with updated schedule
    """
    try:
        schedule = WarmupSchedule.query.get_or_404(schedule_id)
        data = request.get_json() or {}

        # Update fields
        if 'target_emails' in data:
            target_emails = int(data['target_emails'])
            if target_emails < 0:
                return jsonify({'error': 'target_emails must be >= 0'}), 400
            schedule.target_emails = target_emails

        if 'enabled' in data:
            schedule.enabled = bool(data['enabled'])

        schedule.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'id': schedule.id,
            'day': schedule.day,
            'target_emails': schedule.target_emails,
            'enabled': schedule.enabled,
            'updated_at': schedule.updated_at.isoformat()
        })

    except ValueError as e:
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/create', methods=['POST'])
def create_schedule():
    """
    Create new schedule day

    Request Body:
        day (int): Day number
        target_emails (int): Number of emails to send
        enabled (bool): Whether this day is enabled (default: True)

    Returns:
        JSON with created schedule
    """
    try:
        data = request.get_json() or {}

        # Validate required fields
        if 'day' not in data or 'target_emails' not in data:
            return jsonify({'error': 'day and target_emails are required'}), 400

        day = int(data['day'])
        target_emails = int(data['target_emails'])
        enabled = data.get('enabled', True)

        # Check if day already exists
        existing = WarmupSchedule.query.filter_by(day=day).first()
        if existing:
            return jsonify({'error': f'Schedule for day {day} already exists'}), 400

        # Create schedule
        schedule = WarmupSchedule(
            day=day,
            target_emails=target_emails,
            enabled=enabled
        )
        db.session.add(schedule)
        db.session.commit()

        return jsonify({
            'id': schedule.id,
            'day': schedule.day,
            'target_emails': schedule.target_emails,
            'enabled': schedule.enabled,
            'created_at': schedule.created_at.isoformat()
        }), 201

    except ValueError as e:
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """
    Delete schedule day

    Args:
        schedule_id: Schedule ID

    Returns:
        JSON with success message
    """
    try:
        schedule = WarmupSchedule.query.get_or_404(schedule_id)

        db.session.delete(schedule)
        db.session.commit()

        return jsonify({'message': f'Schedule day {schedule.day} deleted successfully'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/bulk-update', methods=['POST'])
def bulk_update():
    """
    Bulk update multiple schedule days

    Request Body:
        schedules (list): List of schedule updates
            Each item: {id: int, target_emails: int, enabled: bool}

    Returns:
        JSON with update results
    """
    try:
        data = request.get_json() or {}
        schedules = data.get('schedules', [])

        if not schedules:
            return jsonify({'error': 'No schedules provided'}), 400

        updated_count = 0
        errors = []

        for item in schedules:
            try:
                schedule_id = item.get('id')
                if not schedule_id:
                    continue

                schedule = WarmupSchedule.query.get(schedule_id)
                if not schedule:
                    errors.append(f'Schedule {schedule_id} not found')
                    continue

                if 'target_emails' in item:
                    schedule.target_emails = int(item['target_emails'])

                if 'enabled' in item:
                    schedule.enabled = bool(item['enabled'])

                schedule.updated_at = datetime.utcnow()
                updated_count += 1

            except Exception as e:
                errors.append(f'Error updating schedule {schedule_id}: {str(e)}')

        db.session.commit()

        return jsonify({
            'updated': updated_count,
            'errors': errors
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/execution-history')
def execution_history():
    """
    Get warmup execution history

    Query Parameters:
        limit (int): Number of records to return (default: 30)

    Returns:
        JSON with execution history
    """
    try:
        limit = request.args.get('limit', 30, type=int)

        executions = WarmupExecution.query.order_by(
            WarmupExecution.date.desc()
        ).limit(limit).all()

        history = []
        for exec in executions:
            schedule = WarmupSchedule.query.get(exec.schedule_day_id)

            history.append({
                'id': exec.id,
                'date': str(exec.date),
                'schedule_day': schedule.day if schedule else None,
                'target_emails': schedule.target_emails if schedule else None,
                'sent_count': exec.sent_count,
                'completed': bool(exec.completed_at),
                'completed_at': exec.completed_at.isoformat() if exec.completed_at else None,
                'created_at': exec.created_at.isoformat() if exec.created_at else None
            })

        return jsonify(history)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
