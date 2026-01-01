"""
Contact Form Cloud Function
Sends contact form submissions via Gmail SMTP
"""

import functions_framework
from flask import jsonify
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from google.cloud import secretmanager

# Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
RECIPIENT_EMAIL = "stratiaadmissions@gmail.com"

def get_secret(secret_id):
    """Fetch secret from Google Cloud Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get('GCP_PROJECT', 'college-counselling-478115')
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def add_cors_headers(response_data, status_code=200):
    """Add CORS headers to response"""
    response = jsonify(response_data)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response, status_code

@functions_framework.http
def send_contact_email(request):
    """
    HTTP Cloud Function to send contact form emails.
    
    Expected JSON body:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "subject": "Question about Stratia",
        "message": "Hello, I have a question..."
    }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 204
    
    if request.method != 'POST':
        return add_cors_headers({'error': 'Method not allowed'}, 405)
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'subject', 'message']
        for field in required_fields:
            if not data.get(field):
                return add_cors_headers({'error': f'Missing required field: {field}'}, 400)
        
        name = data['name']
        sender_email = data['email']
        subject = data['subject']
        message = data['message']
        
        # Get SMTP credentials from Secret Manager
        smtp_username = get_secret('SMTP_USERNAME')  # Gmail address
        smtp_password = get_secret('SMTP_PASSWORD')  # App password
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[Stratia Contact] {subject}"
        msg['From'] = smtp_username
        msg['To'] = RECIPIENT_EMAIL
        msg['Reply-To'] = sender_email
        
        # Plain text version
        text_content = f"""
New contact form submission from Stratia Admissions

From: {name}
Email: {sender_email}
Subject: {subject}

Message:
{message}
        """
        
        # HTML version
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1A4D2E; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0;">New Contact Form Submission</h2>
            </div>
            <div style="padding: 20px; background: #f9f9f9;">
                <p><strong>From:</strong> {name}</p>
                <p><strong>Email:</strong> <a href="mailto:{sender_email}">{sender_email}</a></p>
                <p><strong>Subject:</strong> {subject}</p>
                <hr style="border: 1px solid #ddd;">
                <p><strong>Message:</strong></p>
                <p style="white-space: pre-wrap;">{message}</p>
            </div>
            <div style="padding: 15px; background: #eee; text-align: center; font-size: 12px; color: #666;">
                Sent from Stratia Admissions Contact Form
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email via SMTP
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, RECIPIENT_EMAIL, msg.as_string())
        
        return add_cors_headers({
            'success': True,
            'message': 'Your message has been sent successfully!'
        })
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return add_cors_headers({
            'error': 'Failed to send message. Please try again later.'
        }, 500)
