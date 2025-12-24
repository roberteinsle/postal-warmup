"""
Postal API Integration for sending emails
"""
import requests
import time
import random
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger()


class PostalEmailSender:
    """
    Handles email sending through Postal HTTP API
    """

    def __init__(self, api_key, base_url):
        """
        Initialize Postal Email Sender

        Args:
            api_key: Postal API key
            base_url: Postal server base URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1/send/message"

    def send_email(self, sender, recipient, subject, body, html_body=None):
        """
        Send a single email via Postal API

        Args:
            sender: From email address
            recipient: To email address
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)

        Returns:
            dict: Response with message_id and status
        """
        try:
            # Prepare email data
            email_data = {
                'to': [recipient],
                'from': sender,
                'subject': subject,
                'plain_body': body,
            }

            if html_body:
                email_data['html_body'] = html_body

            # Prepare headers
            headers = {
                'X-Server-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }

            logger.info(f"Sending email from {sender} to {recipient}: {subject}")

            # Send request to Postal API
            response = requests.post(
                self.api_url,
                json=email_data,
                headers=headers,
                timeout=30
            )

            # Parse response
            response_data = response.json()

            if response.status_code == 200 and response_data.get('status') == 'success':
                message_id = response_data.get('data', {}).get('message_id')
                logger.info(f"Email sent successfully. Message ID: {message_id}")

                return {
                    'success': True,
                    'message_id': message_id,
                    'status': 'sent',
                    'response': response_data
                }
            else:
                error_msg = response_data.get('data', {}).get('message', 'Unknown error')
                logger.error(f"Failed to send email: {error_msg}")

                return {
                    'success': False,
                    'message_id': None,
                    'status': 'failed',
                    'error': error_msg,
                    'response': response_data
                }

        except requests.exceptions.Timeout:
            logger.error("Postal API request timed out")
            return {
                'success': False,
                'message_id': None,
                'status': 'failed',
                'error': 'Request timed out'
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Postal API request failed: {e}")
            return {
                'success': False,
                'message_id': None,
                'status': 'failed',
                'error': str(e)
            }

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return {
                'success': False,
                'message_id': None,
                'status': 'failed',
                'error': str(e)
            }

    def batch_send(self, senders, recipients, emails_count, content_generator,
                   min_delay=2, max_delay=5):
        """
        Send multiple emails with rate limiting

        Args:
            senders: List of sender email addresses
            recipients: List of recipient email addresses
            emails_count: Number of emails to send
            content_generator: EmailContentGenerator instance
            min_delay: Minimum delay between sends (seconds)
            max_delay: Maximum delay between sends (seconds)

        Returns:
            list: Results for each sent email
        """
        results = []

        logger.info(f"Starting batch send: {emails_count} emails")

        for i in range(emails_count):
            # Randomly select sender and recipient
            sender = random.choice(senders)
            recipient = random.choice(recipients)

            # Generate email content
            content_type = random.choice(['transactional', 'newsletter', 'personal', 'mixed'])
            subject, body = content_generator.generate_email(content_type)

            # Send email
            result = self.send_email(sender, recipient, subject, body)
            result['sender'] = sender
            result['recipient'] = recipient
            result['subject'] = subject
            result['content_type'] = content_type
            result['sent_at'] = datetime.utcnow()

            results.append(result)

            # Rate limiting: random delay between sends
            if i < emails_count - 1:  # Don't delay after last email
                delay = random.uniform(min_delay, max_delay)
                logger.debug(f"Waiting {delay:.2f}s before next send...")
                time.sleep(delay)

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"Batch send complete: {success_count}/{emails_count} successful")

        return results

    def validate_connection(self):
        """
        Validate Postal API connection and credentials

        Returns:
            bool: True if connection is valid
        """
        try:
            # Try to access a simple API endpoint
            headers = {
                'X-Server-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }

            # Use the deliveries endpoint as a connectivity test
            test_url = f"{self.base_url}/api/v1/messages/deliveries"
            response = requests.get(
                test_url,
                headers=headers,
                params={'id': 'test'},  # Dummy parameter
                timeout=10
            )

            # Even if the query fails (parameter error), 200 means API is reachable
            if response.status_code == 200:
                logger.info("Postal API connection validated successfully")
                return True
            elif response.status_code == 401:
                logger.error("Postal API authentication failed - invalid API key")
                return False
            else:
                logger.warning(f"Postal API returned status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to validate Postal API connection: {e}")
            return False
