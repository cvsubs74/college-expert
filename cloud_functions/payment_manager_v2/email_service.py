"""
Email Service for Subscription Notifications
Sends transactional emails for subscription lifecycle events.
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


# Global Secret Manager Client (Lazy initialization to avoid import-time errors)
_secret_manager_client = None

def get_secret_manager_client():
    global _secret_manager_client
    if _secret_manager_client is None:
        _secret_manager_client = secretmanager.SecretManagerServiceClient()
    return _secret_manager_client

def get_secret(secret_id: str) -> str:
    """Fetch secret from Google Cloud Secret Manager"""
    try:
        client = get_secret_manager_client()
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
        text_content: Plain text fallback (optional, derived from html if not provided)
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Get SMTP credentials
        smtp_username = get_secret('SMTP_USERNAME')
        smtp_password = get_secret('SMTP_PASSWORD')
        
        if not smtp_username or not smtp_password:
            logger.error("SMTP credentials not configured in Secret Manager")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{FROM_NAME} <{smtp_username}>"
        msg['To'] = to_email
        
        # Plain text fallback
        if not text_content:
            # Simple HTML strip for fallback
            text_content = html_content.replace('<br>', '\n').replace('</p>', '\n')
            import re
            text_content = re.sub(r'<[^>]+>', '', text_content)
        
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
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
        <!--[if !mso]><!-->
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        </style>
        <!--<![endif]-->
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: 'Inter', Arial, sans-serif;">
        <!-- Preheader text (hidden but shows in email preview) -->
        <div style="display: none; max-height: 0; overflow: hidden;">
            {preheader}
        </div>
        
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


# ============================================================================
# EMAIL TEMPLATES
# ============================================================================

def send_welcome_email(user_email: str, plan_name: str, credits: int) -> bool:
    """Send welcome email when subscription starts"""
    
    content = f"""
    <h2 style="color: {BRAND_GREEN}; margin: 0 0 20px 0; font-size: 24px;">Welcome to Stratia Admissions! 🎉</h2>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Thank you for subscribing to <strong>{plan_name}</strong>! Your account is now active and ready to use.
    </p>
    
    <div style="background-color: {BRAND_GREEN_LIGHT}; border-radius: 8px; padding: 20px; margin: 25px 0;">
        <h3 style="color: {BRAND_GREEN}; margin: 0 0 15px 0; font-size: 18px;">Your Plan Includes:</h3>
        <ul style="color: #333; margin: 0; padding-left: 20px; line-height: 1.8;">
            <li><strong>{credits}</strong> Fit Analysis credits</li>
            <li>Unlimited AI chat conversations</li>
            <li>Personalized college recommendations</li>
            <li>Essay assistance tools</li>
        </ul>
    </div>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Ready to start exploring? Click below to find your perfect college matches!
    </p>
    
    {get_button_html("Explore Universities", f"{FRONTEND_URL}/universities")}
    
    <p style="color: {BRAND_GRAY}; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
        If you have any questions, our support team is here to help. Just reply to this email or visit our help center.
    </p>
    """
    
    html = get_email_wrapper(content, f"Welcome to Stratia Admissions! Your {plan_name} is now active.")
    return send_email(user_email, f"Welcome to Stratia Admissions! 🎓", html)


def send_payment_failed_email(user_email: str, attempt_count: int, next_attempt_date: str = None) -> bool:
    """Send warning email when payment fails"""
    
    retry_text = ""
    if next_attempt_date:
        retry_text = f"<p style='color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;'>We'll automatically retry on <strong>{next_attempt_date}</strong>.</p>"
    
    urgency = "soon" if attempt_count < 3 else "immediately"
    
    content = f"""
    <h2 style="color: #D32F2F; margin: 0 0 20px 0; font-size: 24px;">⚠️ Payment Failed</h2>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        We were unable to process your subscription payment. This is attempt <strong>#{attempt_count}</strong>.
    </p>
    
    {retry_text}
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        To avoid any interruption to your service, please update your payment method {urgency}.
    </p>
    
    <div style="background-color: #FFF3E0; border-left: 4px solid #FF9800; padding: 15px 20px; margin: 25px 0;">
        <p style="color: #333; margin: 0; font-size: 14px;">
            <strong>What happens if not resolved?</strong><br>
            After multiple failed attempts, your subscription will be canceled and you'll lose access to premium features.
        </p>
    </div>
    
    {get_button_html("Update Payment Method", f"{FRONTEND_URL}/account/billing")}
    
    <p style="color: {BRAND_GRAY}; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
        If you believe this is an error or need assistance, please contact our support team.
    </p>
    """
    
    html = get_email_wrapper(content, f"Action required: Your payment failed (attempt #{attempt_count})")
    return send_email(user_email, f"⚠️ Payment Failed - Action Required", html)


def send_subscription_ended_email(user_email: str, plan_name: str) -> bool:
    """Send email when subscription ends"""
    
    content = f"""
    <h2 style="color: {BRAND_GREEN}; margin: 0 0 20px 0; font-size: 24px;">Your Subscription Has Ended</h2>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Your <strong>{plan_name}</strong> subscription has ended. We're sad to see you go! 😢
    </p>
    
    <div style="background-color: #f5f5f5; border-radius: 8px; padding: 20px; margin: 25px 0;">
        <h3 style="color: #333; margin: 0 0 15px 0; font-size: 18px;">What This Means:</h3>
        <ul style="color: #333; margin: 0; padding-left: 20px; line-height: 1.8;">
            <li>Your premium features have been deactivated</li>
            <li>Your saved data and preferences are preserved</li>
            <li>You can resubscribe anytime to restore full access</li>
        </ul>
    </div>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Ready to continue your college journey? Reactivate your subscription to pick up where you left off.
    </p>
    
    {get_button_html("Resubscribe Now", f"{FRONTEND_URL}/pricing")}
    
    <p style="color: {BRAND_GRAY}; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
        We'd love to hear your feedback! Reply to this email to let us know how we can improve.
    </p>
    """
    
    html = get_email_wrapper(content, f"Your {plan_name} subscription has ended. We'll miss you!")
    return send_email(user_email, f"Your Stratia Subscription Has Ended", html)


def send_cancellation_confirmed_email(user_email: str, plan_name: str, end_date: str) -> bool:
    """Send confirmation when user schedules cancellation"""
    
    content = f"""
    <h2 style="color: {BRAND_GREEN}; margin: 0 0 20px 0; font-size: 24px;">Cancellation Confirmed</h2>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        We've received your cancellation request for <strong>{plan_name}</strong>.
    </p>
    
    <div style="background-color: {BRAND_GREEN_LIGHT}; border-radius: 8px; padding: 20px; margin: 25px 0; text-align: center;">
        <p style="color: {BRAND_GREEN}; margin: 0 0 5px 0; font-size: 14px; font-weight: 600;">ACCESS UNTIL</p>
        <p style="color: {BRAND_GREEN}; margin: 0; font-size: 28px; font-weight: 700;">{end_date}</p>
    </div>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        You'll continue to have full access to all premium features until your subscription period ends. No further charges will be made.
    </p>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Changed your mind? You can reactivate your subscription anytime before it ends.
    </p>
    
    {get_button_html("Keep My Subscription", f"{FRONTEND_URL}/account/billing", primary=False)}
    
    <p style="color: {BRAND_GRAY}; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
        We appreciate your feedback! Let us know why you're leaving so we can improve.
    </p>
    """
    
    html = get_email_wrapper(content, f"Your cancellation is confirmed. Access continues until {end_date}.")
    return send_email(user_email, f"Cancellation Confirmed - Access Until {end_date}", html)


def send_credits_low_email(user_email: str, credits_remaining: int) -> bool:
    """Send reminder when credits are running low"""
    
    content = f"""
    <h2 style="color: {BRAND_GREEN}; margin: 0 0 20px 0; font-size: 24px;">Running Low on Credits! 📊</h2>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Just a heads up - you have <strong>{credits_remaining}</strong> Fit Analysis credits remaining.
    </p>
    
    <div style="background-color: #FFF8E1; border-radius: 8px; padding: 20px; margin: 25px 0; text-align: center;">
        <p style="color: #F57C00; margin: 0 0 5px 0; font-size: 14px; font-weight: 600;">CREDITS REMAINING</p>
        <p style="color: #F57C00; margin: 0; font-size: 48px; font-weight: 700;">{credits_remaining}</p>
    </div>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Don't run out at a critical moment! Add more credits to continue discovering your perfect college matches.
    </p>
    
    {get_button_html("Get More Credits", f"{FRONTEND_URL}/pricing")}
    
    <p style="color: {BRAND_GRAY}; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
        Monthly subscribers: Your credits will reset on your next billing date.
    </p>
    """
    
    html = get_email_wrapper(content, f"You have {credits_remaining} Fit Analysis credits remaining.")
    return send_email(user_email, f"📊 {credits_remaining} Credits Remaining - Top Up?", html)


def send_renewal_success_email(user_email: str, plan_name: str, credits_granted: int, next_billing_date: str) -> bool:
    """Send confirmation when subscription renews successfully"""
    
    content = f"""
    <h2 style="color: {BRAND_GREEN}; margin: 0 0 20px 0; font-size: 24px;">Subscription Renewed! ✅</h2>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Great news! Your <strong>{plan_name}</strong> subscription has been renewed successfully.
    </p>
    
    <div style="background-color: {BRAND_GREEN_LIGHT}; border-radius: 8px; padding: 20px; margin: 25px 0;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td style="width: 50%; text-align: center; padding: 10px;">
                    <p style="color: {BRAND_GREEN}; margin: 0 0 5px 0; font-size: 12px; font-weight: 600;">CREDITS ADDED</p>
                    <p style="color: {BRAND_GREEN}; margin: 0; font-size: 32px; font-weight: 700;">{credits_granted}</p>
                </td>
                <td style="width: 50%; text-align: center; padding: 10px; border-left: 1px solid {BRAND_GREEN};">
                    <p style="color: {BRAND_GREEN}; margin: 0 0 5px 0; font-size: 12px; font-weight: 600;">NEXT BILLING</p>
                    <p style="color: {BRAND_GREEN}; margin: 0; font-size: 18px; font-weight: 700;">{next_billing_date}</p>
                </td>
            </tr>
        </table>
    </div>
    
    <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
        Your credits have been refreshed. Keep exploring and finding your perfect college matches!
    </p>
    
    {get_button_html("Continue Exploring", f"{FRONTEND_URL}/universities")}
    """
    
    html = get_email_wrapper(content, f"Your subscription renewed! {credits_granted} credits added.")
    return send_email(user_email, f"✅ Subscription Renewed - {credits_granted} Credits Added", html)
