from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from starlette.config import Config

config = Config('.env')

SMTP_HOST = config('SMTP_HOST', default='smtp.gmail.com')
SMTP_PORT = config('SMTP_PORT', cast=int, default=587)
SMTP_USER = config('SMTP_USER', default=None)
SMTP_PASSWORD = config('SMTP_PASSWORD', default=None)
FROM_EMAIL = config('FROM_EMAIL', default=SMTP_USER)

async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> None:
    """Send an email using SMTP."""
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        raise ValueError("Email settings not configured")

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email

    # Add text/plain and text/html parts
    if text_content:
        msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))

    # Send email
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

async def send_reset_password_email(email: str, username: str, reset_link: str) -> None:
    """Send password reset email."""
    subject = "Reset Your Password"
    
    text_content = f"""
    Hello {username},

    You recently requested to reset your password. Click the link below to reset it:

    {reset_link}

    This link will expire in 1 hour.

    If you did not request a password reset, please ignore this email.

    Best regards,
    AI Content Recommendation Team
    """

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c5282;">Reset Your Password</h2>
                
                <p>Hello {username},</p>
                
                <p>You recently requested to reset your password. Click the button below to reset it:</p>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #4299e1; 
                              color: white; 
                              padding: 12px 24px; 
                              text-decoration: none; 
                              border-radius: 5px;
                              display: inline-block;">
                        Reset Password
                    </a>
                </p>
                
                <p style="color: #718096; font-size: 0.9em;">
                    This link will expire in 1 hour.
                </p>
                
                <p style="color: #718096; font-size: 0.9em;">
                    If you did not request a password reset, please ignore this email.
                </p>
                
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                
                <p style="color: #718096; font-size: 0.8em; text-align: center;">
                    Best regards,<br>
                    AI Content Recommendation Team
                </p>
            </div>
        </body>
    </html>
    """

    await send_email(
        to_email=email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    ) 