"""
Email Service for Profile Manager V2
Sends welcome and notification emails for user events.
Uses Gmail SMTP via Google Cloud Secret Manager credentials.
"""

import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from google.cloud import secretmanager
import os

logger = logging.getLogger(__name__)

# Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
FROM_NAME = "Stratia Admissions"
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://stratiaadmissions.com')

# Brand colors
BRAND_GREEN = "#1A4D2E"
BRAND_GREEN_LIGHT = "#D6E8D5"
BRAND_GRAY = "#666666"


def get_secret(secret_id: str) -> str:
    """Fetch secret from Google Cloud Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get('GCP_PROJECT', 'college-counselling-478115')
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to get secret {secret_id}: {e}")
        return None


def send_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
    """
    Send an email via SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_content: HTML email body
        text_content: Plain text fallback (optional)
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        smtp_username = get_secret('SMTP_USERNAME')
        smtp_password = get_secret('SMTP_PASSWORD')
        
        if not smtp_username or not smtp_password:
            logger.error("SMTP credentials not configured in Secret Manager")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{FROM_NAME} <{smtp_username}>"
        msg['To'] = to_email
        
        if not text_content:
            import re
            text_content = html_content.replace('<br>', '\n').replace('</p>', '\n')
            text_content = re.sub(r'<[^>]+>', '', text_content)
        
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, to_email, msg.as_string())
        
        logger.info(f"Email sent successfully to {to_email}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def get_email_wrapper(content: str, preheader: str = "") -> str:
    """Wrap content in branded email template"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stratia Admissions</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: 'Inter', Arial, sans-serif;">
        <div style="display: none; max-height: 0; overflow: hidden;">{preheader}</div>
        
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f4;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, {BRAND_GREEN} 0%, #2D6B45 100%); padding: 30px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">Stratia Admissions</h1>
                                <p style="margin: 8px 0 0 0; color: {BRAND_GREEN_LIGHT}; font-size: 14px;">Your College Strategy Partner</p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                {content}
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f9f9f9; padding: 25px 30px; text-align: center; border-top: 1px solid #eee;">
                                <p style="margin: 0 0 10px 0; color: {BRAND_GRAY}; font-size: 13px;">
                                    Need help? <a href="{FRONTEND_URL}/contact" style="color: {BRAND_GREEN}; text-decoration: none;">Contact Support</a>
                                </p>
                                <p style="margin: 0; color: #999; font-size: 12px;">
                                    © {datetime.now().year} Stratia Admissions. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def get_button_html(text: str, url: str, primary: bool = True) -> str:
    """Generate a call-to-action button"""
    bg_color = BRAND_GREEN if primary else "#ffffff"
    text_color = "#ffffff" if primary else BRAND_GREEN
    border = f"2px solid {BRAND_GREEN}"
    
    return f"""
    <table role="presentation" cellspacing="0" cellpadding="0" style="margin: 25px auto;">
        <tr>
            <td style="background-color: {bg_color}; border-radius: 8px; border: {border};">
                <a href="{url}" target="_blank" style="display: inline-block; padding: 14px 32px; color: {text_color}; text-decoration: none; font-weight: 600; font-size: 16px;">
                    {text}
                </a>
            </td>
        </tr>
    </table>
    """


def send_signup_welcome_email(user_email: str) -> bool:
    """Send welcome email when user signs up/signs in for the first time"""
    
    content = f"""
    <h2 style="color: {BRAND_GREEN}; margin: 0 0 20px 0; font-size: 24px;">Welcome to Stratia Admissions! 🎓</h2>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        We're thrilled to have you join our community of ambitious students navigating the college admissions journey!
    </p>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Stratia Admissions uses AI to help you find your perfect college match, craft compelling essays, and build a strategic application strategy.
    </p>
    
    <div style="background-color: {BRAND_GREEN_LIGHT}; border-radius: 8px; padding: 20px; margin: 25px 0;">
        <h3 style="color: {BRAND_GREEN}; margin: 0 0 15px 0; font-size: 18px;">Here's What You Can Do:</h3>
        <ul style="color: #333; margin: 0; padding-left: 20px; line-height: 1.8;">
            <li><strong>Discover Universities</strong> - Explore 200+ schools with AI-powered insights</li>
            <li><strong>Get Fit Analysis</strong> - See how well you match with each school</li>
            <li><strong>Chat with AI</strong> - Ask questions about any university or your profile</li>
            <li><strong>Essay Help</strong> - Get personalized guidance on your application essays</li>
        </ul>
    </div>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Start by completing your profile so we can give you personalized recommendations!
    </p>
    
    {get_button_html("Complete Your Profile", f"{FRONTEND_URL}/profile")}
    
    <p style="color: {BRAND_GRAY}; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
        Questions? Just reply to this email or reach out through our contact page. We're here to help you succeed!
    </p>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 20px 0 0 0;">
        Best of luck on your journey,<br>
        <strong style="color: {BRAND_GREEN};">The Stratia Admissions Team</strong>
    </p>
    """
    
    html = get_email_wrapper(content, "Welcome to Stratia Admissions! Start your college journey today.")
    return send_email(user_email, "Welcome to Stratia Admissions! 🎓", html)
