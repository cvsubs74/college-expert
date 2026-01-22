"""
Scheduled Notifications Cloud Function
Runs daily to check for upcoming deadlines and send reminder emails.
Triggered by Cloud Scheduler via HTTP.
"""

import functions_framework
from flask import jsonify
from google.cloud import firestore
from datetime import datetime, timedelta
import logging
import sys
import os

# Add parent directory for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'profile_manager_v2'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db():
    """Get Firestore client."""
    return firestore.Client()


def get_users_with_notifications_enabled():
    """Get all users who have notifications enabled (or haven't disabled them)."""
    db = get_db()
    users_ref = db.collection('users')
    users = []
    
    for doc in users_ref.stream():
        user_data = doc.to_dict()
        # Check if notifications are not explicitly disabled
        prefs = user_data.get('notification_preferences', {})
        if prefs.get('email_reminders', True):  # Default to enabled
            users.append({
                'user_id': doc.id,
                'email': user_data.get('email') or doc.id,
                'name': user_data.get('name', '')
            })
    
    return users


def get_upcoming_tasks(user_id: str, days_ahead: int = 14):
    """Get tasks due within the specified number of days."""
    db = get_db()
    today = datetime.utcnow().date()
    cutoff = today + timedelta(days=days_ahead)
    
    tasks = []
    
    # Check roadmap_tasks collection
    tasks_ref = db.collection('users').document(user_id).collection('roadmap_tasks')
    for doc in tasks_ref.stream():
        task = doc.to_dict()
        if task.get('status') == 'completed':
            continue
        
        due_date_str = task.get('due_date')
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str.replace('Z', '')).date()
                if today <= due_date <= cutoff:
                    days_until = (due_date - today).days
                    tasks.append({
                        'task_id': doc.id,
                        'title': task.get('title', 'Task'),
                        'due_date': due_date.strftime('%b %d, %Y'),
                        'days_until': days_until,
                        'university_name': task.get('university_name', ''),
                        'task_type': task.get('task_type', 'general')
                    })
            except (ValueError, AttributeError):
                pass
    
    # Sort by days_until
    tasks.sort(key=lambda x: x['days_until'])
    return tasks


def get_user_summary_data(user_id: str):
    """Get summary data for weekly email."""
    db = get_db()
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    week_ahead = today + timedelta(days=7)
    
    summary = {
        'tasks_completed': 0,
        'tasks_upcoming': 0,
        'essays_final': 0,
        'essays_total': 0,
        'schools_count': 0
    }
    
    # Count completed tasks in past week
    tasks_ref = db.collection('users').document(user_id).collection('roadmap_tasks')
    for doc in tasks_ref.stream():
        task = doc.to_dict()
        if task.get('status') == 'completed':
            completed_at = task.get('completed_at')
            if completed_at:
                try:
                    completed_date = datetime.fromisoformat(completed_at.replace('Z', '')).date()
                    if completed_date >= week_ago:
                        summary['tasks_completed'] += 1
                except:
                    pass
        else:
            # Check if due this week
            due_date_str = task.get('due_date')
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '')).date()
                    if today <= due_date <= week_ahead:
                        summary['tasks_upcoming'] += 1
                except:
                    pass
    
    # Count essays
    essays_ref = db.collection('users').document(user_id).collection('essays')
    for doc in essays_ref.stream():
        essay = doc.to_dict()
        summary['essays_total'] += 1
        if essay.get('status') == 'final':
            summary['essays_final'] += 1
    
    # Count schools
    schools_ref = db.collection('users').document(user_id).collection('college_list')
    summary['schools_count'] = len(list(schools_ref.stream()))
    
    return summary


def send_deadline_notifications():
    """Check all users for upcoming deadlines and send notifications."""
    from email_service import send_deadline_reminder_email
    
    users = get_users_with_notifications_enabled()
    sent_count = 0
    
    for user in users:
        try:
            tasks = get_upcoming_tasks(user['user_id'])
            if not tasks:
                continue
            
            # Categorize by urgency
            urgent_tasks = [t for t in tasks if t['days_until'] <= 3]
            upcoming_tasks = [t for t in tasks if 3 < t['days_until'] <= 7]
            soon_tasks = [t for t in tasks if 7 < t['days_until'] <= 14]
            
            # Send most urgent email (only one per day)
            if urgent_tasks:
                if send_deadline_reminder_email(user['email'], urgent_tasks, 'urgent'):
                    sent_count += 1
                    logger.info(f"Sent URGENT reminder to {user['email']}: {len(urgent_tasks)} tasks")
            elif upcoming_tasks:
                if send_deadline_reminder_email(user['email'], upcoming_tasks, 'upcoming'):
                    sent_count += 1
                    logger.info(f"Sent upcoming reminder to {user['email']}: {len(upcoming_tasks)} tasks")
            # Don't send 'soon' emails daily - only on weekly summary
            
        except Exception as e:
            logger.error(f"Error sending notification to {user['email']}: {e}")
    
    return sent_count


def send_weekly_summaries():
    """Send weekly summary emails to all users (called on Sundays)."""
    from email_service import send_weekly_summary_email
    
    users = get_users_with_notifications_enabled()
    sent_count = 0
    
    for user in users:
        try:
            summary = get_user_summary_data(user['user_id'])
            
            # Only send if user has some activity
            if summary['schools_count'] > 0 or summary['tasks_completed'] > 0:
                if send_weekly_summary_email(user['email'], summary):
                    sent_count += 1
                    logger.info(f"Sent weekly summary to {user['email']}")
                    
        except Exception as e:
            logger.error(f"Error sending weekly summary to {user['email']}: {e}")
    
    return sent_count


@functions_framework.http
def scheduled_notifications(request):
    """
    Main entry point for scheduled notifications.
    
    Query params:
        type: 'daily' (default) or 'weekly'
    """
    # Handle CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        notification_type = request.args.get('type', 'daily')
        
        if notification_type == 'weekly':
            sent_count = send_weekly_summaries()
            return jsonify({
                'success': True,
                'type': 'weekly',
                'emails_sent': sent_count
            }), 200, headers
        else:
            sent_count = send_deadline_notifications()
            return jsonify({
                'success': True,
                'type': 'daily',
                'emails_sent': sent_count
            }), 200, headers
            
    except Exception as e:
        logger.error(f"Scheduled notification error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500, headers
