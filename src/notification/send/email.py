import smtplib
import os
import json
import base64
import logging
from email.message import EmailMessage

# Configure logging
logging.basicConfig(level=logging.DEBUG,  # Adjust level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                    format='%(asctime)s - %(levelname)s - %(message)s - {%(pathname)s:%(lineno)d}')
logger = logging.getLogger(__name__)

def notification(message):
    try:
        logging.debug("Starting notification process")

        # Load and parse the message
        message = json.loads(message)
        mp3_fid = message["mp3_fid"]
        receiver_address = message["username"]

        logging.debug(f"Parsed mp3_fid: {mp3_fid}")
        logging.debug(f"Receiver address: {receiver_address}")

        # Get sender credentials from environment variables
        sender_address = os.environ.get("GMAIL_ADDRESS")
        sender_password_b64 = os.environ.get("GMAIL_PASSWORD")

        if not sender_address or not sender_password_b64:
            logging.error("Sender address or password not found in environment variables")
            return "Sender credentials not found"

        sender_password = base64.b64decode(sender_password_b64).decode('utf-8')

        # Create email message
        msg = EmailMessage()
        msg.set_content(f"mp3 file_id: {mp3_fid} is now ready!")
        msg["Subject"] = "MP3 Download"
        msg["From"] = sender_address
        msg["To"] = receiver_address

        logging.debug("Email message created successfully")

        # Send email
        logging.debug("Connecting to SMTP server")
        session = smtplib.SMTP("smtp-mail.outlook.com", 587)
        session.starttls()
        session.login(sender_address, sender_password)
        session.send_message(msg, sender_address, receiver_address)
        session.quit()

        logging.info("Mail sent successfully")
        print("Mail Sent")

    except Exception as err:
        logging.error(f"An error occurred: {err}")
        return str(err)