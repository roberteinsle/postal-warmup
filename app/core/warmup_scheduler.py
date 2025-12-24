"""
Warmup Scheduler - Orchestrates automated email warmup campaigns
"""
from datetime import datetime, date, timedelta
import random
from app.models import db, Email, WarmupSchedule, WarmupExecution, Statistic
from app.core.email_sender import PostalEmailSender
from app.core.email_checker import IMAPEmailChecker
from app.core.content_generator import EmailContentGenerator
from app.utils.logger import get_logger

logger = get_logger()


class WarmupScheduler:
    """
    Manages warmup email campaigns with scheduling and tracking
    """

    def __init__(self, app):
        """
        Initialize Warmup Scheduler

        Args:
            app: Flask application instance
        """
        self.app = app
        self.postal_sender = PostalEmailSender(
            app.config.get('POSTAL_API_KEY'),
            app.config.get('POSTAL_BASE_URL')
        )
        self.content_generator = EmailContentGenerator(
            app.config.get('OPENAI_API_KEY')
        )
        self.imap_checker = IMAPEmailChecker(
            app.config.get('IMAP_HOST'),
            app.config.get('IMAP_PORT'),
            app.config.get('IMAP_USE_SSL')
        )

    def get_current_warmup_day(self):
        """
        Calculate current warmup day based on first execution

        Returns:
            int: Current warmup day (1-based)
        """
        with self.app.app_context():
            first_execution = WarmupExecution.query.order_by(
                WarmupExecution.created_at.asc()
            ).first()

            if not first_execution:
                return 1  # First day

            days_since_start = (date.today() - first_execution.date).days
            return days_since_start + 1

    def get_today_schedule(self):
        """
        Get warmup schedule for today

        Returns:
            WarmupSchedule: Today's schedule or None
        """
        with self.app.app_context():
            current_day = self.get_current_warmup_day()
            schedule = WarmupSchedule.query.filter_by(
                day=current_day,
                enabled=True
            ).first()
            return schedule

    def should_send_today(self):
        """
        Check if emails should be sent today

        Returns:
            bool: True if should send
        """
        with self.app.app_context():
            # Check if already executed today
            today_execution = WarmupExecution.query.filter_by(
                date=date.today()
            ).first()

            if today_execution and today_execution.completed_at:
                logger.info("Already executed today")
                return False

            # Check if there's a schedule for today
            schedule = self.get_today_schedule()
            if not schedule:
                logger.info("No schedule for today")
                return False

            return True

    def send_daily_batch(self):
        """
        Send daily batch of warmup emails

        Returns:
            dict: Execution results
        """
        logger.info("Starting daily warmup batch...")

        with self.app.app_context():
            # Get today's schedule
            schedule = self.get_today_schedule()
            if not schedule:
                logger.warning("No schedule found for today")
                return {'success': False, 'error': 'No schedule for today'}

            # Check if already executed
            if not self.should_send_today():
                return {'success': False, 'error': 'Already executed today'}

            target_emails = schedule.target_emails
            logger.info(f"Target emails for today: {target_emails}")

            # Get sender and recipient addresses
            senders = self.app.config.get('SENDER_ADDRESSES', [])
            recipients = self.app.config.get('RECIPIENT_ADDRESSES', [])

            if not senders or not recipients:
                logger.error("No sender or recipient addresses configured")
                return {'success': False, 'error': 'No addresses configured'}

            # Create or get today's execution record
            execution = WarmupExecution.query.filter_by(
                date=date.today()
            ).first()

            if not execution:
                execution = WarmupExecution(
                    schedule_day_id=schedule.id,
                    date=date.today(),
                    sent_count=0
                )
                db.session.add(execution)
                db.session.commit()

            # Send emails
            results = []
            min_delay = self.app.config.get('MIN_DELAY_BETWEEN_SENDS', 2)
            max_delay = self.app.config.get('MAX_DELAY_BETWEEN_SENDS', 5)
            check_delay_minutes = self.app.config.get('CHECK_DELAY_MINUTES', 15)

            for i in range(target_emails):
                # Select random sender and recipient
                sender = random.choice(senders)
                recipient = random.choice(recipients)
                content_type = random.choice(['transactional', 'newsletter', 'personal', 'mixed'])

                # Generate content
                subject, body = self.content_generator.generate_email(content_type)

                # Send email
                send_result = self.postal_sender.send_email(sender, recipient, subject, body)

                # Save to database
                email = Email(
                    sender=sender,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    content_type=content_type,
                    postal_message_id=send_result.get('message_id'),
                    status='sent' if send_result['success'] else 'failed',
                    delivery_status='pending',
                    sent_at=datetime.utcnow(),
                    check_scheduled_at=datetime.utcnow() + timedelta(minutes=check_delay_minutes)
                )
                db.session.add(email)

                results.append({
                    'success': send_result['success'],
                    'email_id': None,  # Will be set after commit
                    'subject': subject
                })

                # Update execution count
                execution.sent_count += 1

                # Random delay before next send (except for last email)
                if i < target_emails - 1:
                    import time
                    delay = random.uniform(min_delay, max_delay)
                    logger.debug(f"Waiting {delay:.2f}s before next send...")
                    time.sleep(delay)

            # Mark execution as completed
            execution.completed_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Daily batch complete: {execution.sent_count} emails sent")

            # Update statistics
            self.update_daily_statistics()

            return {
                'success': True,
                'sent_count': execution.sent_count,
                'target_count': target_emails,
                'results': results
            }

    def check_pending_emails(self):
        """
        Check delivery status of pending emails

        Returns:
            dict: Check results
        """
        logger.info("Checking pending emails...")

        with self.app.app_context():
            # Get emails that are ready to be checked
            now = datetime.utcnow()
            pending_emails = Email.query.filter(
                Email.delivery_status == 'pending',
                Email.check_scheduled_at <= now,
                Email.checked_at.is_(None)
            ).limit(50).all()  # Process max 50 at a time

            if not pending_emails:
                logger.info("No pending emails to check")
                return {'checked': 0}

            logger.info(f"Checking {len(pending_emails)} emails")

            checked_count = 0
            recipient_passwords = self.app.config.get('RECIPIENT_IMAP_PASSWORDS', {})

            for email in pending_emails:
                # Get IMAP password for recipient
                password = recipient_passwords.get(email.recipient)
                if not password:
                    logger.warning(f"No IMAP password for {email.recipient}")
                    email.delivery_status = 'unknown'
                    email.checked_at = datetime.utcnow()
                    continue

                # Check email delivery
                try:
                    result = self.imap_checker.check_email(
                        email.recipient,
                        password,
                        email.postal_message_id,
                        email.subject
                    )

                    email.delivery_status = result.get('delivery_status', 'unknown')
                    email.checked_at = datetime.utcnow()

                    # Simulate human behavior for inbox emails
                    if email.delivery_status == 'inbox' and random.random() < 0.7:  # 70% chance
                        try:
                            # Mark as read
                            if random.random() < 0.8:  # 80% chance
                                self.imap_checker.mark_as_read(
                                    email.recipient,
                                    password,
                                    subject=email.subject
                                )
                                email.is_read = True

                            # Move to folder
                            if random.random() < 0.3:  # 30% chance
                                folders = ['Archive', 'Important', 'Work']
                                target_folder = random.choice(folders)
                                success = self.imap_checker.move_to_folder(
                                    email.recipient,
                                    password,
                                    target_folder,
                                    subject=email.subject
                                )
                                if success:
                                    email.moved_to_folder = target_folder

                        except Exception as e:
                            logger.warning(f"Failed to simulate behavior: {e}")

                    checked_count += 1

                except Exception as e:
                    logger.error(f"Failed to check email {email.id}: {e}")
                    email.delivery_status = 'failed'
                    email.checked_at = datetime.utcnow()

            db.session.commit()
            logger.info(f"Checked {checked_count} emails")

            # Update statistics after checking
            self.update_daily_statistics()

            return {'checked': checked_count}

    def update_daily_statistics(self):
        """
        Update daily statistics based on email tracking
        """
        with self.app.app_context():
            today = date.today()

            # Get or create today's statistics
            stats = Statistic.query.filter_by(date=today).first()
            if not stats:
                stats = Statistic(date=today)
                db.session.add(stats)

            # Count today's emails
            today_start = datetime.combine(today, datetime.min.time())
            today_emails = Email.query.filter(
                Email.sent_at >= today_start
            ).all()

            stats.emails_sent = len(today_emails)
            stats.emails_inbox = sum(1 for e in today_emails if e.delivery_status == 'inbox')
            stats.emails_spam = sum(1 for e in today_emails if e.delivery_status == 'spam')
            stats.emails_failed = sum(1 for e in today_emails if e.status == 'failed')
            stats.bounce_count = sum(1 for e in today_emails if e.status == 'bounced')

            # Calculate rates
            stats.calculate_rates()

            db.session.commit()
            logger.info(f"Updated statistics for {today}: {stats.emails_sent} sent, {stats.success_rate:.1f}% success")

    def trigger_manual_send(self, count, senders=None, recipients=None):
        """
        Manually trigger email sending (outside of schedule)

        Args:
            count: Number of emails to send
            senders: List of senders (optional)
            recipients: List of recipients (optional)

        Returns:
            dict: Send results
        """
        logger.info(f"Manual send triggered: {count} emails")

        with self.app.app_context():
            if not senders:
                senders = self.app.config.get('SENDER_ADDRESSES', [])
            if not recipients:
                recipients = self.app.config.get('RECIPIENT_ADDRESSES', [])

            if not senders or not recipients:
                return {'success': False, 'error': 'No addresses configured'}

            results = []
            min_delay = self.app.config.get('MIN_DELAY_BETWEEN_SENDS', 2)
            max_delay = self.app.config.get('MAX_DELAY_BETWEEN_SENDS', 5)
            check_delay_minutes = self.app.config.get('CHECK_DELAY_MINUTES', 15)

            for i in range(count):
                sender = random.choice(senders)
                recipient = random.choice(recipients)
                content_type = random.choice(['transactional', 'newsletter', 'personal', 'mixed'])

                # Generate and send
                subject, body = self.content_generator.generate_email(content_type)
                send_result = self.postal_sender.send_email(sender, recipient, subject, body)

                # Save to database
                email = Email(
                    sender=sender,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    content_type=content_type,
                    postal_message_id=send_result.get('message_id'),
                    status='sent' if send_result['success'] else 'failed',
                    delivery_status='pending',
                    sent_at=datetime.utcnow(),
                    check_scheduled_at=datetime.utcnow() + timedelta(minutes=check_delay_minutes)
                )
                db.session.add(email)

                results.append({
                    'success': send_result['success'],
                    'subject': subject,
                    'sender': sender,
                    'recipient': recipient
                })

                # Delay
                if i < count - 1:
                    import time
                    delay = random.uniform(min_delay, max_delay)
                    time.sleep(delay)

            db.session.commit()
            self.update_daily_statistics()

            success_count = sum(1 for r in results if r['success'])
            logger.info(f"Manual send complete: {success_count}/{count} successful")

            return {
                'success': True,
                'sent_count': success_count,
                'total_count': count,
                'results': results
            }

    def get_warmup_progress(self):
        """
        Get current warmup progress and statistics

        Returns:
            dict: Progress information
        """
        with self.app.app_context():
            current_day = self.get_current_warmup_day()
            total_days = WarmupSchedule.query.filter_by(enabled=True).count()

            # Get all executions
            executions = WarmupExecution.query.order_by(
                WarmupExecution.date.desc()
            ).limit(7).all()

            # Get recent statistics
            recent_stats = Statistic.query.order_by(
                Statistic.date.desc()
            ).limit(7).all()

            # Overall statistics
            total_sent = Email.query.count()
            total_inbox = Email.query.filter_by(delivery_status='inbox').count()
            total_spam = Email.query.filter_by(delivery_status='spam').count()

            overall_success_rate = (total_inbox / total_sent * 100) if total_sent > 0 else 0
            overall_spam_rate = (total_spam / total_sent * 100) if total_sent > 0 else 0

            return {
                'current_day': current_day,
                'total_days': total_days,
                'total_sent': total_sent,
                'total_inbox': total_inbox,
                'total_spam': total_spam,
                'overall_success_rate': round(overall_success_rate, 2),
                'overall_spam_rate': round(overall_spam_rate, 2),
                'recent_executions': [
                    {
                        'date': str(e.date),
                        'sent_count': e.sent_count,
                        'completed': bool(e.completed_at)
                    }
                    for e in executions
                ],
                'recent_statistics': [
                    {
                        'date': str(s.date),
                        'sent': s.emails_sent,
                        'inbox': s.emails_inbox,
                        'spam': s.emails_spam,
                        'success_rate': round(s.success_rate, 2),
                        'spam_rate': round(s.spam_rate, 2)
                    }
                    for s in recent_stats
                ]
            }
