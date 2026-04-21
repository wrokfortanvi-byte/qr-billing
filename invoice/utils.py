from twilio.rest import Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_whatsapp_message(phone, message):
    try:
        # =========================
        # CLEAN PHONE FORMAT
        # =========================
        if not phone:
            return False

        phone = str(phone).strip()

        if not phone.startswith("+"):
            phone = "+91" + phone   # India default

        # =========================
        # TWILIO CLIENT
        # =========================
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

        client.messages.create(
            body=message,
            from_=f'whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}',
            to=f'whatsapp:{phone}'
        )

        return True

    except Exception as e:
        logger.error(f"WhatsApp send failed: {str(e)}")
        return False