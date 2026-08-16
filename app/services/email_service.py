import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Union
from app.config import settings
from app.services.template_service import template_service

logger = logging.getLogger("pulse.email")


class EmailService:
    """SMTP Email Dispatch Service with Pulse HTML template support."""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_TLS
        self.use_ssl = settings.SMTP_SSL

    def is_configured(self) -> bool:
        """Check if SMTP settings are populated with non-placeholder credentials."""
        if not self.host or not self.port or not self.user or not self.password:
            return False
        if "your_email" in self.user or "your_password" in self.password:
            return False
        return True

    def _send_sync(
        self,
        recipients: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        if not self.is_configured():
            logger.info(f"[DEV MODE] SMTP not fully configured. Simulated sending '{subject}' to {recipients}")
            return True  # Return True in simulated development mode to prevent crashing endpoints

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = ", ".join(recipients)

        text_part = MIMEText(body_text or "Please view this email in an HTML-compatible client.", "plain")
        html_part = MIMEText(body_html, "html")
        message.attach(text_part)
        message.attach(html_part)

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)

            server.ehlo()
            if self.use_tls and not self.use_ssl:
                server.starttls()
                server.ehlo()

            server.login(self.user, self.password)
            server.sendmail(self.from_email, recipients, message.as_string())
            server.quit()
            logger.info(f"Email '{subject}' sent successfully to {recipients}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipients}: {e}")
            if settings.DEBUG:
                logger.info(f"[DEV FALLBACK] Simulated success for '{subject}' despite SMTP error: {e}")
                return True
            return False

    async def send_email(
        self,
        to_email: Union[str, List[str]],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """Asynchronously dispatch email using background thread execution."""
        recipients = [to_email] if isinstance(to_email, str) else to_email
        return await asyncio.to_thread(self._send_sync, recipients, subject, body_html, body_text)

    # Templated Email Helpers
    async def send_otp_email(self, to_email: str, user_name: str, otp_code: str, expire_minutes: int = 10) -> bool:
        """Send OTP verification code email using modern Pulse template."""
        html_content = template_service.render(
            "otp.html",
            {
                "user_name": user_name,
                "otp_code": otp_code,
                "expire_minutes": expire_minutes
            }
        )
        return await self.send_email(
            to_email=to_email,
            subject=f"{otp_code} is your Pulse verification code",
            body_html=html_content,
            body_text=f"Your verification code is: {otp_code}. Valid for {expire_minutes} minutes."
        )

    async def send_welcome_email(self, to_email: str, user_name: str, dashboard_url: Optional[str] = None) -> bool:
        """Send Welcome email using Pulse brand template."""
        html_content = template_service.render(
            "welcome.html",
            {
                "user_name": user_name,
                "dashboard_url": dashboard_url or f"{settings.FRONTEND_URL}/dashboard"
            }
        )

        return await self.send_email(
            to_email=to_email,
            subject="Welcome to Pulse!",
            body_html=html_content,
            body_text=f"Welcome to Pulse, {user_name}! Your account is ready."
        )

    async def send_password_reset_email(self, to_email: str, user_name: str, reset_url: str, expire_minutes: int = 30) -> bool:
        """Send Password Reset instructions email using Pulse template."""
        html_content = template_service.render(
            "password_reset.html",
            {
                "user_name": user_name,
                "reset_url": reset_url,
                "expire_minutes": expire_minutes
            }
        )
        return await self.send_email(
            to_email=to_email,
            subject="Reset your Pulse password",
            body_html=html_content,
            body_text=f"Reset your password by visiting: {reset_url}"
        )

    async def send_password_changed_email(self, to_email: str, user_name: str, change_time: Optional[str] = None) -> bool:
        """Send Password Changed security notification email."""
        html_content = template_service.render(
            "password_changed.html",
            {
                "user_name": user_name,
                "change_time": change_time or "recently"
            }
        )
        return await self.send_email(
            to_email=to_email,
            subject="Security Alert: Your Pulse password was updated",
            body_html=html_content,
            body_text=f"Hi {user_name}, your password was updated."
        )


email_service = EmailService()
