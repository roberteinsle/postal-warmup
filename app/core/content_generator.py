"""
OpenAI Integration for generating email content
"""
import random
from openai import OpenAI
from app.utils.logger import get_logger

logger = get_logger()


class EmailContentGenerator:
    """
    Generates realistic email content using OpenAI API
    """

    def __init__(self, api_key):
        """
        Initialize Email Content Generator

        Args:
            api_key: OpenAI API key
        """
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"  # Cost-effective model

        # Fallback templates for when API fails
        self.fallback_templates = {
            'transactional': [
                ("Order Confirmation", "Your order has been confirmed and will be shipped soon."),
                ("Password Reset", "We received a request to reset your password."),
                ("Account Verification", "Please verify your email address to complete registration."),
            ],
            'newsletter': [
                ("Monthly Update", "Here's what's new this month with our service."),
                ("Tips and Tricks", "Discover new ways to get the most out of our platform."),
                ("Community Highlights", "See what our community has been up to this week."),
            ],
            'personal': [
                ("Quick Question", "I hope this email finds you well. I wanted to reach out about..."),
                ("Following Up", "Just wanted to follow up on our previous conversation."),
                ("Thank You", "I wanted to take a moment to thank you for your help."),
            ]
        }

    def generate_email(self, content_type='mixed'):
        """
        Generate email subject and body

        Args:
            content_type: Type of email (transactional, newsletter, personal, mixed)

        Returns:
            tuple: (subject, body)
        """
        # If mixed, randomly choose a type
        if content_type == 'mixed':
            content_type = random.choice(['transactional', 'newsletter', 'personal'])

        try:
            subject, body = self._generate_with_openai(content_type)
            logger.info(f"Generated {content_type} email via OpenAI: {subject}")
            return subject, body

        except Exception as e:
            logger.warning(f"OpenAI generation failed, using fallback: {e}")
            return self._get_fallback_content(content_type)

    def _generate_with_openai(self, content_type):
        """
        Generate content using OpenAI API

        Args:
            content_type: Type of email

        Returns:
            tuple: (subject, body)
        """
        # Create appropriate prompt based on content type
        prompts = {
            'transactional': """Generate a professional transactional email.
            Examples: order confirmation, password reset, account verification, shipping notification.
            Keep it concise (2-3 sentences) and professional.
            Return ONLY in this format:
            SUBJECT: [subject line]
            BODY: [email body]""",

            'newsletter': """Generate a friendly newsletter-style email.
            Topics: product updates, tips, community news, feature announcements.
            Keep it engaging but brief (3-4 sentences).
            Return ONLY in this format:
            SUBJECT: [subject line]
            BODY: [email body]""",

            'personal': """Generate a casual, personal email.
            Topics: quick questions, follow-ups, thank you notes, friendly check-ins.
            Keep it warm and conversational (2-3 sentences).
            Return ONLY in this format:
            SUBJECT: [subject line]
            BODY: [email body]"""
        }

        prompt = prompts.get(content_type, prompts['personal'])

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates realistic email content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.9  # Higher temperature for more variety
        )

        # Parse response
        content = response.choices[0].message.content.strip()

        # Extract subject and body
        subject = ""
        body = ""

        lines = content.split('\n')
        for line in lines:
            if line.startswith('SUBJECT:'):
                subject = line.replace('SUBJECT:', '').strip()
            elif line.startswith('BODY:'):
                body = line.replace('BODY:', '').strip()

        # Fallback if parsing failed
        if not subject or not body:
            logger.warning("Failed to parse OpenAI response, using fallback")
            return self._get_fallback_content(content_type)

        return subject, body

    def _get_fallback_content(self, content_type):
        """
        Get fallback content when OpenAI fails

        Args:
            content_type: Type of email

        Returns:
            tuple: (subject, body)
        """
        templates = self.fallback_templates.get(
            content_type,
            self.fallback_templates['personal']
        )

        subject, body = random.choice(templates)
        return subject, body

    def generate_batch(self, count, content_types=None):
        """
        Generate multiple emails

        Args:
            count: Number of emails to generate
            content_types: List of content types to use (or None for mixed)

        Returns:
            list: List of (subject, body, content_type) tuples
        """
        results = []

        if not content_types:
            content_types = ['mixed']

        for i in range(count):
            content_type = random.choice(content_types)
            subject, body = self.generate_email(content_type)
            results.append((subject, body, content_type))

        logger.info(f"Generated {count} emails")
        return results

    def test_connection(self):
        """
        Test OpenAI API connection

        Returns:
            bool: True if connection is valid
        """
        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Say 'OK' if you can read this."}
                ],
                max_tokens=10
            )

            if response.choices[0].message.content:
                logger.info("OpenAI API connection validated successfully")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to validate OpenAI API connection: {e}")
            return False
