import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    def _create_email_body(
        self,
        notification_type: str,
        title: str,
        message: str,
        document_number: str = None,
        metadata: dict = None
    ) -> str:
        """
        Create HTML email body

        Args:
            notification_type: Type of notification
            title: Email title
            message: Notification message
            document_number: Optional document number
            metadata: Additional context

        Returns:
            HTML email body
        """
        app_name = settings.APP_NAME
        document_line = f'<p class="document-number">Document: {document_number}</p>' if document_number else ''

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 5px 5px;
                }}
                .notification-type {{
                    display: inline-block;
                    padding: 5px 10px;
                    background-color: #3498db;
                    color: white;
                    border-radius: 3px;
                    font-size: 12px;
                    margin-bottom: 15px;
                }}
                .message {{
                    font-size: 16px;
                    margin: 20px 0;
                }}
                .document-number {{
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #777;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app_name}</h1>
            </div>
            <div class="content">
                <span class="notification-type">{notification_type.replace('_', ' ').title()}</span>
                <h2>{title}</h2>
                {document_line}
                <p class="message">{message}</p>
            </div>
            <div class="footer">
                <p>This is an automated notification from {app_name}</p>
                <p>Please do not reply to this email</p>
            </div>
        </body>
        </html>
        """

    async def send_notification_email(
        self,
        to_email: str,
        notification_type: str,
        title: str,
        message: str,
        document_number: str = None,
        metadata: dict = None
    ) -> bool:
        """
        Send notification email

        Args:
            to_email: Recipient email address
            notification_type: Type of notification
            title: Email subject/title
            message: Notification message
            document_number: Optional document number
            metadata: Additional context

        Returns:
            True if sent successfully, False otherwise
        """
        # Skip if SMTP not configured
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP not configured, skipping email send")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{settings.APP_NAME}] {title}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email

            # Create HTML body
            html_body = self._create_email_body(
                notification_type=notification_type,
                title=title,
                message=message,
                document_number=document_number,
                metadata=metadata
            )

            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_batch_emails(
        self,
        recipients: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Send multiple emails in batch

        Args:
            recipients: List of dicts with keys: to_email, notification_type, title, message, etc.

        Returns:
            Dict with success and failure counts
        """
        success_count = 0
        failure_count = 0

        for recipient in recipients:
            result = await self.send_notification_email(**recipient)
            if result:
                success_count += 1
            else:
                failure_count += 1

        return {"success": success_count, "failed": failure_count}
