"""
Tests for the Notification microservice.
Covers: email.notification() logic.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import os

os.environ.setdefault("MP3_QUEUE", "mp3")
os.environ.setdefault("GMAIL_ADDRESS", "test@test.com")
os.environ.setdefault("GMAIL_PASSWORD", "dGVzdA==")  # base64("test")


class TestEmailNotification:
    """Tests for the email notification logic."""

    @patch("send.email.smtplib.SMTP")
    def test_notification_sends_email_successfully(self, mock_smtp):
        from send.email import notification

        mock_session = MagicMock()
        mock_smtp.return_value = mock_session

        message = json.dumps({
            "mp3_fid": "abc123",
            "username": "user@test.com"
        })

        result = notification(message)

        # Verify SMTP session was created and email sent
        mock_smtp.assert_called_once_with("smtp-mail.outlook.com", 587)
        mock_session.starttls.assert_called_once()
        mock_session.login.assert_called_once()
        mock_session.send_message.assert_called_once()
        mock_session.quit.assert_called_once()
        assert result is None  # No error

    def test_notification_handles_invalid_json(self):
        from send.email import notification

        result = notification(b"not valid json")
        assert result is not None  # Should return error string

    @patch("send.email.smtplib.SMTP")
    def test_notification_handles_smtp_failure(self, mock_smtp):
        from send.email import notification

        mock_smtp.side_effect = Exception("SMTP connection refused")

        message = json.dumps({
            "mp3_fid": "abc123",
            "username": "user@test.com"
        })

        result = notification(message)
        assert result is not None  # Should return error

    @patch.dict(os.environ, {"GMAIL_ADDRESS": "", "GMAIL_PASSWORD": ""})
    def test_notification_handles_missing_credentials(self):
        from send.email import notification

        message = json.dumps({
            "mp3_fid": "abc123",
            "username": "user@test.com"
        })

        result = notification(message)
        assert result is not None  # Should return error
