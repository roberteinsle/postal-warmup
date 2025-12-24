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

        # Fallback templates for when API fails (German)
        self.fallback_templates = {
            'transactional': [
                ("Bestellbestätigung", "Ihre Bestellung wurde bestätigt und wird in Kürze versandt."),
                ("Passwort zurücksetzen", "Wir haben eine Anfrage zum Zurücksetzen Ihres Passworts erhalten."),
                ("Konto-Verifizierung", "Bitte bestätigen Sie Ihre E-Mail-Adresse, um die Registrierung abzuschließen."),
            ],
            'newsletter': [
                ("Monatliches Update", "Hier sind die Neuigkeiten dieses Monats von unserem Service."),
                ("Tipps und Tricks", "Entdecken Sie neue Wege, um das Beste aus unserer Plattform herauszuholen."),
                ("Community-Highlights", "Sehen Sie, was unsere Community diese Woche gemacht hat."),
            ],
            'personal': [
                ("Kurze Frage", "Ich hoffe, es geht Ihnen gut. Ich wollte mich bezüglich... melden."),
                ("Nachfassen", "Ich wollte nur kurz zu unserem letzten Gespräch nachfassen."),
                ("Vielen Dank", "Ich wollte mir einen Moment Zeit nehmen, um mich für Ihre Hilfe zu bedanken."),
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
            'transactional': """Generiere eine professionelle Transaktions-E-Mail auf Deutsch.
            Beispiele: Bestellbestätigung, Passwort zurücksetzen, Kontobestätigung, Versandbenachrichtigung.
            Halte es prägnant (2-3 Sätze) und professionell.
            Antworte NUR in diesem Format:
            SUBJECT: [Betreffzeile]
            BODY: [E-Mail-Text]""",

            'newsletter': """Generiere eine freundliche Newsletter-E-Mail auf Deutsch.
            Themen: Produktupdates, Tipps, Community-News, Feature-Ankündigungen.
            Halte es ansprechend aber kurz (3-4 Sätze).
            Antworte NUR in diesem Format:
            SUBJECT: [Betreffzeile]
            BODY: [E-Mail-Text]""",

            'personal': """Generiere eine lockere, persönliche E-Mail auf Deutsch.
            Themen: Kurze Fragen, Follow-ups, Danksagungen, freundliche Check-ins.
            Halte es warm und gesprächig (2-3 Sätze).
            Antworte NUR in diesem Format:
            SUBJECT: [Betreffzeile]
            BODY: [E-Mail-Text]"""
        }

        prompt = prompts.get(content_type, prompts['personal'])

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent, der realistische E-Mail-Inhalte auf Deutsch generiert."},
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
