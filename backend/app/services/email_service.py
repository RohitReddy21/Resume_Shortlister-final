import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    async def send_password_reset_email(to_email: str, reset_link: str) -> None:
        # Replace this placeholder with a production email provider such as SendGrid, SES, or Resend.
        logger.info(f"Password reset requested for {to_email}: {reset_link}")
        print(f"[EMAIL] Password reset for {to_email}: {reset_link}")

    @staticmethod
    async def send_stage_change_email(
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        new_stage: str,
    ) -> None:
        """Notify a candidate that their application has moved to a new stage.

        Gracefully skips sending if SMTP is not configured (dev environments).
        """
        settings = get_settings()

        stage_messages = {
            "Screening": "Your application is being reviewed by our team.",
            "Shortlisted": "Great news — you've been shortlisted!",
            "Interview": "You've been invited to interview!",
            "Technical": "You've been invited to a technical round.",
            "HR": "You've been invited to an HR discussion.",
            "Offer": "Congratulations! We have an offer for you.",
            "Hired": "Welcome to the team! You've been hired.",
            "Rejected": "Thank you for your interest. We've decided to move forward with other candidates.",
        }
        message = stage_messages.get(new_stage, f"Your application status has been updated to: {new_stage}.")

        subject = f"Update on your {job_title} application"
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: #0f172a; padding: 24px; border-radius: 12px;">
              <h2 style="color: #22d3ee; margin: 0 0 8px;">Application Update</h2>
              <p style="color: #94a3b8; margin: 0;">ResumeParser.AI</p>
            </div>
            <div style="padding: 24px;">
              <p>Hi {candidate_name},</p>
              <p>{message}</p>
              <p><strong>Role:</strong> {job_title}</p>
              <p><strong>New Stage:</strong> {new_stage}</p>
              <p style="margin-top: 24px; color: #64748b; font-size: 13px;">
                You received this email because you applied through ResumeParser.AI.
              </p>
            </div>
          </body>
        </html>
        """

        # Skip silently if SMTP is not configured
        if not settings.smtp_host or not settings.smtp_username:
            logger.info(
                f"[EMAIL SKIPPED] Stage change email to {candidate_email}: "
                f"{job_title} -> {new_stage} (SMTP not configured)"
            )
            print(
                f"[EMAIL] Stage change: {candidate_name} <{candidate_email}> | "
                f"{job_title} -> {new_stage}"
            )
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.smtp_from
            msg["To"] = candidate_email
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.smtp_from, [candidate_email], msg.as_string())

            logger.info(f"Stage change email sent to {candidate_email}")
        except Exception as exc:
            logger.error(f"Failed to send stage change email to {candidate_email}: {exc}")
