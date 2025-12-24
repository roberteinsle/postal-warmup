"""
IMAP Integration for checking email delivery and inbox/spam placement
"""
import imapclient
import random
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger()


class IMAPEmailChecker:
    """
    Handles email checking via IMAP to detect inbox vs spam placement
    """

    def __init__(self, host, port=993, use_ssl=True):
        """
        Initialize IMAP Email Checker

        Args:
            host: IMAP server hostname
            port: IMAP server port (default 993 for SSL)
            use_ssl: Use SSL/TLS connection (default True)
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl

    def check_email(self, email_address, password, message_id=None, subject=None):
        """
        Check if an email was delivered and where (inbox/spam)

        Args:
            email_address: Email account to check
            password: IMAP password
            message_id: Message ID to search for (optional)
            subject: Subject to search for (optional)

        Returns:
            dict: Delivery status information
        """
        try:
            # Connect to IMAP server
            logger.info(f"Connecting to IMAP: {email_address}@{self.host}")

            client = imapclient.IMAPClient(
                self.host,
                port=self.port,
                ssl=self.use_ssl
            )

            # Login
            client.login(email_address, password)
            logger.info(f"IMAP login successful for {email_address}")

            # Search in INBOX first
            inbox_found = self._search_in_folder(client, 'INBOX', message_id, subject)

            if inbox_found:
                client.logout()
                logger.info(f"Email found in INBOX for {email_address}")
                return {
                    'found': True,
                    'delivery_status': 'inbox',
                    'folder': 'INBOX',
                    'checked_at': datetime.utcnow()
                }

            # Search in common spam folders
            spam_folders = ['[Gmail]/Spam', 'Spam', 'Junk', 'SPAM', '[Gmail]/Junk']

            for spam_folder in spam_folders:
                try:
                    spam_found = self._search_in_folder(client, spam_folder, message_id, subject)
                    if spam_found:
                        client.logout()
                        logger.warning(f"Email found in SPAM folder ({spam_folder}) for {email_address}")
                        return {
                            'found': True,
                            'delivery_status': 'spam',
                            'folder': spam_folder,
                            'checked_at': datetime.utcnow()
                        }
                except Exception:
                    # Folder might not exist, continue to next
                    continue

            # Email not found in any folder
            client.logout()
            logger.warning(f"Email not found for {email_address}")
            return {
                'found': False,
                'delivery_status': 'unknown',
                'folder': None,
                'checked_at': datetime.utcnow()
            }

        except imapclient.exceptions.LoginError as e:
            logger.error(f"IMAP login failed for {email_address}: {e}")
            return {
                'found': False,
                'delivery_status': 'failed',
                'folder': None,
                'error': f'Login failed: {str(e)}',
                'checked_at': datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"IMAP check failed for {email_address}: {e}")
            return {
                'found': False,
                'delivery_status': 'failed',
                'folder': None,
                'error': str(e),
                'checked_at': datetime.utcnow()
            }

    def _search_in_folder(self, client, folder_name, message_id=None, subject=None):
        """
        Search for email in a specific folder

        Args:
            client: IMAPClient instance
            folder_name: Folder to search in
            message_id: Message ID to search for
            subject: Subject to search for

        Returns:
            bool: True if email found
        """
        try:
            # Select folder
            client.select_folder(folder_name, readonly=True)

            # Build search criteria
            search_criteria = []

            if message_id:
                search_criteria.append(['HEADER', 'Message-ID', message_id])

            if subject:
                search_criteria.append(['SUBJECT', subject])

            if not search_criteria:
                # Search for recent emails if no specific criteria
                search_criteria = [['SINCE', datetime.now().date()]]

            # Search
            messages = client.search(search_criteria[0] if len(search_criteria) == 1 else ['OR'] + search_criteria)

            return len(messages) > 0

        except Exception as e:
            logger.debug(f"Could not search folder {folder_name}: {e}")
            return False

    def mark_as_read(self, email_address, password, message_id=None, subject=None):
        """
        Mark email as read to simulate human behavior

        Args:
            email_address: Email account
            password: IMAP password
            message_id: Message ID
            subject: Subject

        Returns:
            bool: True if successful
        """
        try:
            client = imapclient.IMAPClient(self.host, port=self.port, ssl=self.use_ssl)
            client.login(email_address, password)

            # Search in INBOX
            client.select_folder('INBOX')

            search_criteria = []
            if message_id:
                search_criteria.append(['HEADER', 'Message-ID', message_id])
            if subject:
                search_criteria.append(['SUBJECT', subject])

            messages = client.search(search_criteria[0] if search_criteria else ['UNSEEN'])

            if messages:
                # Mark first matching message as read
                client.add_flags(messages[0], [imapclient.SEEN])
                logger.info(f"Marked email as read for {email_address}")
                client.logout()
                return True

            client.logout()
            return False

        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}")
            return False

    def move_to_folder(self, email_address, password, target_folder, message_id=None, subject=None):
        """
        Move email to a different folder

        Args:
            email_address: Email account
            password: IMAP password
            target_folder: Target folder name
            message_id: Message ID
            subject: Subject

        Returns:
            bool: True if successful
        """
        try:
            client = imapclient.IMAPClient(self.host, port=self.port, ssl=self.use_ssl)
            client.login(email_address, password)

            # Search in INBOX
            client.select_folder('INBOX')

            search_criteria = []
            if message_id:
                search_criteria.append(['HEADER', 'Message-ID', message_id])
            if subject:
                search_criteria.append(['SUBJECT', subject])

            messages = client.search(search_criteria[0] if search_criteria else ['ALL'])

            if messages:
                # Move first matching message
                client.move(messages[0], target_folder)
                logger.info(f"Moved email to {target_folder} for {email_address}")
                client.logout()
                return True

            client.logout()
            return False

        except Exception as e:
            logger.error(f"Failed to move email: {e}")
            return False

    def simulate_human_behavior(self, email_address, password):
        """
        Simulate human-like email interactions

        Args:
            email_address: Email account
            password: IMAP password

        Returns:
            dict: Actions performed
        """
        actions = {
            'read_count': 0,
            'moved_count': 0,
            'deleted_count': 0
        }

        try:
            client = imapclient.IMAPClient(self.host, port=self.port, ssl=self.use_ssl)
            client.login(email_address, password)
            client.select_folder('INBOX')

            # Get some unread messages
            messages = client.search(['UNSEEN'])

            if messages:
                # Randomly read some messages (50% chance per message, max 5)
                to_read = random.sample(messages, min(len(messages), random.randint(1, 5)))
                for msg_id in to_read:
                    client.add_flags(msg_id, [imapclient.SEEN])
                    actions['read_count'] += 1

            # Get some old messages to possibly delete
            old_messages = client.search(['BEFORE', datetime.now().date()])
            if old_messages and random.random() < 0.3:  # 30% chance to delete
                to_delete = random.sample(old_messages, min(len(old_messages), 2))
                for msg_id in to_delete:
                    client.delete_messages(msg_id)
                    actions['deleted_count'] += 1

            client.logout()
            logger.info(f"Simulated human behavior for {email_address}: {actions}")

        except Exception as e:
            logger.error(f"Failed to simulate human behavior: {e}")

        return actions

    def validate_connection(self, email_address, password):
        """
        Validate IMAP connection and credentials

        Args:
            email_address: Email account
            password: IMAP password

        Returns:
            bool: True if connection is valid
        """
        try:
            client = imapclient.IMAPClient(self.host, port=self.port, ssl=self.use_ssl)
            client.login(email_address, password)

            # List folders as a connectivity test
            folders = client.list_folders()

            client.logout()
            logger.info(f"IMAP connection validated for {email_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to validate IMAP connection for {email_address}: {e}")
            return False
