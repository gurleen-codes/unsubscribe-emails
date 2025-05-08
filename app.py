from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, Response
from email_unsubscriber import EmailUnsubscriber
from secure_email_client import SecureEmailClient
from oauth_authentication import OAuthHandler
from email_categorizer import EmailCategorizer
from subscription_analytics import SubscriptionAnalytics
from email_scan_scheduler import EmailScanScheduler
import os
import json
import logging
import threading
from datetime import datetime, timedelta
import csv
from io import StringIO

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CleanInbox')

# Initialize Flask app
app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))  # For session management
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Initialize components
oauth_handler = OAuthHandler(app)
email_categorizer = EmailCategorizer()
subscription_analytics = SubscriptionAnalytics()
email_scheduler = EmailScanScheduler(app)

# Start the email scheduler
email_scheduler.start()

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/', methods=['GET'])
def index():
    # Check if user is already logged in
    if 'email' in session and (session.get('oauth_authenticated') or 'password' in session):
        return redirect('/dashboard')
    
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_emails():
    try:
        data = request.json
        email_address = data.get('email')
        password = data.get('password')
        provider = data.get('provider', 'gmail')
        
        # Validate required inputs
        if not email_address:
            return jsonify({
                'status': 'error',
                'message': 'Email address is required'
            }), 400
            
        # Store basic info in session
        session['email'] = email_address
        session['provider'] = provider
        
        # Determine authentication method
        use_oauth = data.get('use_oauth', False)
        
        if use_oauth:
            # For OAuth, redirect to the provider's auth page
            session['oauth_flow'] = True
            auth_url = oauth_handler.get_auth_url(provider)
            
            if not auth_url:
                return jsonify({
                    'status': 'error',
                    'message': f'OAuth is not configured for {provider}'
                }), 400
                
            return jsonify({
                'status': 'oauth_redirect',
                'redirect_url': auth_url
            })
        else:
            # For password auth, validate password
            if not password:
                return jsonify({
                    'status': 'error',
                    'message': 'Password is required for direct authentication'
                }), 400
                
            # Store password in session (encrypt in production!)
            session['password'] = password
            
            # Create secure email client
            client = SecureEmailClient(email_address, provider)
            client.set_password(password)
            
            # If user selects "Custom Provider", use their custom IMAP settings
            if provider == "custom":
                if 'custom_server' not in data or 'custom_port' not in data:
                    return jsonify({
                        'status': 'error',
                        'message': 'Custom server and port are required for custom provider'
                    }), 400
                
                session['custom_server'] = data['custom_server']
                session['custom_port'] = data['custom_port']
                client.set_custom_imap(data['custom_server'], int(data['custom_port']))
        
            # Authenticate and scan
            if not client.authenticate():
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication failed. Please check your credentials.'
                }), 401
            
            num_emails = int(data.get('num_emails', 50))
            if num_emails <= 0:
                return jsonify({
                    'status': 'error',
                    'message': 'Number of emails must be greater than 0'
                }), 400
                
            # Find unsubscribe links
            unsubscribe_data = client.find_unsubscribe_links(num_emails=num_emails)
            
            # Process the data for the dashboard
            processed_data = process_subscription_data(unsubscribe_data)
            
            # Store in session for quick access
            session['last_scan_data'] = processed_data
            session['last_scan_time'] = datetime.now().isoformat()
            
            # Track total found
            session['total_found'] = len(processed_data)
            if 'total_unsubscribed' not in session:
                session['total_unsubscribed'] = 0
            
            # Return subscription data and redirect to dashboard
            return jsonify({
                'status': 'success',
                'data': processed_data,
                'redirect': '/dashboard',
                'totalUnsubscribed': session.get('total_unsubscribed', 0),
                'timeSaved': calculate_time_saved(len(processed_data))
            })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'Invalid input: {str(e)}'
        }), 400
    except ConnectionError as e:
        return jsonify({
            'status': 'error',
            'message': f'Connection error: {str(e)}'
        }), 503
    except Exception as e:
        logger.error(f"Scan error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/oauth/callback')
def oauth_callback():
    """Handle OAuth callback from providers"""
    # Process the callback with OAuth handler
    result = oauth_handler.handle_callback(request)
    
    if not result['success']:
        # OAuth failed, redirect to login with error
        return redirect(f"/?error={result['error']}")
    
    # OAuth succeeded
    if 'email' in result:
        # If we got an email from OAuth response, store it
        session['email'] = result['email']
    
    # Mark as authenticated with OAuth
    session['oauth_authenticated'] = True
    session['oauth_provider'] = result['provider']
    
    # Redirect to dashboard or scan page
    if session.get('oauth_flow'):
        # We were in the middle of scanning, continue
        del session['oauth_flow']
        return redirect('/scan_with_oauth')
    else:
        # Normal OAuth login, go to dashboard
        return redirect('/dashboard')

@app.route('/scan_with_oauth')
def scan_with_oauth():
    """Scan emails using OAuth authentication"""
    if not session.get('oauth_authenticated') or 'email' not in session:
        return redirect('/')
    
    try:
        # Get provider and email from session
        provider = session.get('oauth_provider', 'gmail')
        email_address = session['email']
        
        # Create secure email client with OAuth
        client = SecureEmailClient(email_address, provider, oauth_handler)
        client.use_oauth()
        
        # Authenticate
        if not client.authenticate():
            return redirect(f"/?error=OAuth authentication failed")
        
        # Default to 100 emails for OAuth
        num_emails = 100
            
        # Find unsubscribe links
        unsubscribe_data = client.find_unsubscribe_links(num_emails=num_emails)
        
        # Process the data for the dashboard
        processed_data = process_subscription_data(unsubscribe_data)
        
        # Store in session for quick access
        session['last_scan_data'] = processed_data
        session['last_scan_time'] = datetime.now().isoformat()
        
        # Track total found
        session['total_found'] = len(processed_data)
        if 'total_unsubscribed' not in session:
            session['total_unsubscribed'] = 0
        
        # Redirect to dashboard
        return redirect('/dashboard')
    except Exception as e:
        logger.error(f"OAuth scan error: {str(e)}")
        return redirect(f"/?error={str(e)}")

def process_subscription_data(unsubscribe_data):
    """Process subscription data for the dashboard"""
    processed_data = []
    
    for item in unsubscribe_data:
        # Extract basic info
        email_data = {
            'subject': item.get('subject', ''),
            'sender': item.get('sender', 'Unknown Sender'),
            'content': item.get('body_preview', '')
        }
        
        # Get category using enhanced categorizer if not already categorized
        if 'category' not in item or not item['category']:
            category, confidence = email_categorizer.categorize(email_data)
        else:
            category = item.get('category', 'Unknown')
            confidence = {}
        
        # Create processed item
        processed_item = {
            'sender': item.get('sender', 'Unknown Sender'),
            'email': item.get('email', ''),
            'category': category,
            'last_received': item.get('last_received', 'N/A'),
            'unsubscribe_link': item.get('unsubscribe_link', ''),
            'method': item.get('method', 'unknown'),
            'confidence': confidence,
            'email_id': item.get('email_id', str(hash(item.get('sender', '') + item.get('unsubscribe_link', ''))))
        }
        processed_data.append(processed_item)
    
    return processed_data

# Helper function to estimate time saved based on number of subscriptions
def calculate_time_saved(num_subscriptions):
    """
    Calculate estimated time saved by unsubscribing
    
    Args:
        num_subscriptions: Number of subscriptions found
        
    Returns:
        float: Estimated time saved in minutes per month
    """
    # Assume each subscription sends 5 emails per month
    emails_per_month = num_subscriptions * 5
    
    # Assume each email takes 30 seconds to process
    seconds_saved = emails_per_month * 30
    
    # Convert to minutes
    return round(seconds_saved / 60)

@app.route('/store_credentials', methods=['POST'])
def store_credentials():
    """Store user credentials in session"""
    try:
        data = request.get_json()
        
        if 'email' in data:
            session['email'] = data.get('email')
            
        if 'password' in data:
            session['password'] = data.get('password')
            
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error storing credentials: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe from a single newsletter"""
    # Ensure user is authenticated
    if 'email' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        # Get unsubscribe info from request
        data = request.get_json()
        link = data.get('link')
        sender = data.get('sender')
        
        if not link:
            return jsonify({'status': 'error', 'message': 'No unsubscribe link provided'}), 400
        
        # Create client based on authentication method
        if session.get('oauth_authenticated'):
            client = SecureEmailClient(session['email'], session.get('oauth_provider', 'gmail'), oauth_handler)
            client.use_oauth()
        else:
            if 'password' not in session:
                return jsonify({'status': 'error', 'message': 'No password stored'}), 401
            
            client = SecureEmailClient(session['email'], session.get('provider', 'gmail'))
            client.set_password(session['password'])
            
            # Add custom IMAP settings if needed
            if session.get('provider') == 'custom' and session.get('custom_server'):
                client.set_custom_imap(
                    session.get('custom_server'), 
                    int(session.get('custom_port', 993))
                )
        
        # Authenticate client
        if not client.authenticate():
            return jsonify({
                'status': 'error',
                'message': 'Authentication failed'
            }), 401
        
        # Perform unsubscribe
        success = client.unsubscribe(link)
        
        # Update counts if successful
        if success:
            if 'total_unsubscribed' not in session:
                session['total_unsubscribed'] = 0
            session['total_unsubscribed'] += 1
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': f'Successfully unsubscribed from {sender}' if success else f'Failed to unsubscribe from {sender}'
        })
    except Exception as e:
        logger.error(f"Unsubscribe error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Render the dashboard page"""
    # Redirect to login if not authenticated
    if 'email' not in session or (not session.get('oauth_authenticated') and 'password' not in session):
        return redirect('/')
    
    # Pass the email and authentication method to the template
    return render_template(
        'dashboard.html', 
        email=session.get('email'),
        auth_method='oauth' if session.get('oauth_authenticated') else 'password',
        provider=session.get('oauth_provider') if session.get('oauth_authenticated') else session.get('provider', 'unknown')
    )

@app.route('/api/subscription_data', methods=['GET'])
def get_subscription_data():
    """API endpoint to get subscription data"""
    # Only proceed if user is logged in
    if 'email' not in session or (not session.get('oauth_authenticated') and 'password' not in session):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        # Check if we have cached data
        if 'last_scan_data' in session and 'last_scan_time' in session:
            # Check if the cache is recent (less than 30 minutes old)
            last_scan_time = datetime.fromisoformat(session['last_scan_time'])
            cache_age = (datetime.now() - last_scan_time).total_seconds() / 60
            
            if cache_age < 30:
                # Use cached data
                scan_data = session['last_scan_data']
                logger.info(f"Using cached subscription data for {session['email']}")
                
                # Generate analytics
                analytics = subscription_analytics.analyze_subscriptions(scan_data, session['email'])
                
                return jsonify({
                    'status': 'success',
                    'subscriptions': scan_data,
                    'stats': {
                        'total_found': len(scan_data),
                        'categories': {item['category']: len([s for s in scan_data if s['category'] == item['category']]) 
                                     for item in scan_data if 'category' in item}
                    },
                    'analytics': analytics,
                    'totalUnsubscribed': session.get('total_unsubscribed', 0),
                    'timeSaved': calculate_time_saved(len(scan_data)),
                    'cached': True,
                    'cache_age': round(cache_age)
                })
        
        # No cache or cache expired, perform a new scan
        # Create client based on authentication method
        if session.get('oauth_authenticated'):
            client = SecureEmailClient(session['email'], session.get('oauth_provider', 'gmail'), oauth_handler)
            client.use_oauth()
        else:
            if 'password' not in session:
                return jsonify({'status': 'error', 'message': 'No password stored'}), 401
            
            client = SecureEmailClient(session['email'], session.get('provider', 'gmail'))
            client.set_password(session['password'])
            
            # Add custom IMAP settings if needed
            if session.get('provider') == 'custom' and session.get('custom_server'):
                client.set_custom_imap(
                    session.get('custom_server'), 
                    int(session.get('custom_port', 993))
                )
        
        # Authenticate client
        if not client.authenticate():
            return jsonify({
                'status': 'error',
                'message': 'Authentication failed'
            }), 401
        
        # Find unsubscribe links
        unsubscribe_data = client.find_unsubscribe_links()
        
        # Process the data
        processed_data = process_subscription_data(unsubscribe_data)
        
        # Update session cache
        session['last_scan_data'] = processed_data
        session['last_scan_time'] = datetime.now().isoformat()
        
        # Generate analytics
        analytics = subscription_analytics.analyze_subscriptions(processed_data, session['email'])
        
        return jsonify({
            'status': 'success',
            'subscriptions': processed_data,
            'stats': {
                'total_found': len(processed_data),
                'categories': {item['category']: len([s for s in processed_data if s['category'] == item['category']]) 
                             for item in processed_data if 'category' in item}
            },
            'analytics': analytics,
            'totalUnsubscribed': session.get('total_unsubscribed', 0),
            'timeSaved': calculate_time_saved(len(processed_data)),
            'cached': False
        })
    except Exception as e:
        logger.error(f"Error getting subscription data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/bulk_unsubscribe', methods=['POST'])
def bulk_unsubscribe():
    """API endpoint for bulk unsubscribing"""
    if 'email' not in session or (not session.get('oauth_authenticated') and 'password' not in session):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    links = data.get('links', [])
    
    if not links:
        return jsonify({'status': 'error', 'message': 'No links provided'}), 400
    
    try:
        # Create client based on authentication method
        if session.get('oauth_authenticated'):
            client = SecureEmailClient(session['email'], session.get('oauth_provider', 'gmail'), oauth_handler)
            client.use_oauth()
        else:
            if 'password' not in session:
                return jsonify({'status': 'error', 'message': 'No password stored'}), 401
            
            client = SecureEmailClient(session['email'], session.get('provider', 'gmail'))
            client.set_password(session['password'])
            
            # Add custom IMAP settings if needed
            if session.get('provider') == 'custom' and session.get('custom_server'):
                client.set_custom_imap(
                    session.get('custom_server'), 
                    int(session.get('custom_port', 993))
                )
        
        # Authenticate client
        if not client.authenticate():
            return jsonify({
                'status': 'error',
                'message': 'Authentication failed'
            }), 401
        
        results = []
        succeeded = 0
        failed = 0
        
        # Process links in batches to avoid overwhelming the server
        batch_size = 5
        for i in range(0, len(links), batch_size):
            batch = links[i:i+batch_size]
            for link_info in batch:
                try:
                    success = client.unsubscribe(link_info['link'])
                    if success:
                        succeeded += 1
                    else:
                        failed += 1
                        
                    results.append({
                        'sender': link_info['sender'],
                        'success': success,
                        'error': None if success else 'Failed to process unsubscribe request'
                    })
                except Exception as e:
                    failed += 1
                    results.append({
                        'sender': link_info['sender'],
                        'success': False,
                        'error': str(e)
                    })
                    
                # Brief pause between requests
                import time
                time.sleep(1)
        
        # Update session count
        if 'total_unsubscribed' not in session:
            session['total_unsubscribed'] = 0
        session['total_unsubscribed'] += succeeded
        
        return jsonify({
            'status': 'success',
            'results': results,
            'summary': {
                'total': len(links),
                'succeeded': succeeded,
                'failed': failed
            }
        })
    except Exception as e:
        logger.error(f"Bulk unsubscribe error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/schedule_scan', methods=['POST'])
def schedule_scan():
    """API endpoint to schedule automated scans"""
    if 'email' not in session or (not session.get('oauth_authenticated') and 'password' not in session):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        frequency = data.get('frequency', 'weekly')
        num_emails = int(data.get('num_emails', 100))
        
        # Get authentication details
        email = session['email']
        provider = session.get('oauth_provider') if session.get('oauth_authenticated') else session.get('provider', 'gmail')
        
        # For OAuth, we don't store a password
        if session.get('oauth_authenticated'):
            # We can't store OAuth tokens for automatic scanning without a secure database
            # This would require implementation of a token storage system
            return jsonify({
                'status': 'error',
                'message': 'Scheduled scans with OAuth require a persistent token storage system'
            }), 400
        
        # For password auth, we need the password
        if 'password' not in session:
            return jsonify({'status': 'error', 'message': 'No password stored'}), 401
        
        password = session['password']
        
        # Schedule the scan
        success = email_scheduler.schedule_scan(email, password, provider, frequency, num_emails)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Scheduled {frequency} scan for {email}',
                'schedule': email_scheduler.get_user_schedule(email)
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to schedule scan'
            }), 400
    except Exception as e:
        logger.error(f"Schedule scan error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/cancel_scheduled_scan', methods=['POST'])
def cancel_scheduled_scan():
    """API endpoint to cancel scheduled scans"""
    if 'email' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        email = session['email']
        success = email_scheduler.cancel_scan(email)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Canceled scheduled scan for {email}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No scheduled scan found'
            }), 404
    except Exception as e:
        logger.error(f"Cancel scheduled scan error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/get_scheduled_scans', methods=['GET'])
def get_scheduled_scans():
    """API endpoint to get scheduled scans for the current user"""
    if 'email' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        email = session['email']
        schedule = email_scheduler.get_user_schedule(email)
        
        if schedule:
            return jsonify({
                'status': 'success',
                'schedule': schedule
            })
        else:
            return jsonify({
                'status': 'success',
                'schedule': None,
                'message': 'No scheduled scans found'
            })
    except Exception as e:
        logger.error(f"Get scheduled scans error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """API endpoint to get subscription analytics"""
    if 'email' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        # We need subscription data to generate analytics
        if 'last_scan_data' not in session:
            return jsonify({
                'status': 'error',
                'message': 'No scan data available. Please scan your inbox first.'
            }), 404
        
        subscription_data = session['last_scan_data']
        email = session['email']
        
        # Generate analytics
        analytics = subscription_analytics.analyze_subscriptions(subscription_data, email)
        
        return jsonify({
            'status': 'success',
            'analytics': analytics
        })
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/category_feedback', methods=['POST'])
def category_feedback():
    """API endpoint to provide category feedback for the ML categorizer"""
    if 'email' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        email_id = data.get('email_id')
        original_category = data.get('original_category')
        correct_category = data.get('correct_category')
        
        if not email_id or not correct_category:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields'
            }), 400
        
        # Find the email in the scan data
        if 'last_scan_data' not in session:
            return jsonify({
                'status': 'error',
                'message': 'No scan data available'
            }), 404
        
        scan_data = session['last_scan_data']
        target_email = None
        
        for email in scan_data:
            if email.get('email_id') == email_id:
                target_email = email
                break
        
        if not target_email:
            return jsonify({
                'status': 'error',
                'message': 'Email not found in scan data'
            }), 404
        
        # Update the model with this feedback
        success = email_categorizer.update_with_feedback(target_email, correct_category)
        
        if success:
            # Update the category in the scan data
            target_email['category'] = correct_category
            session['last_scan_data'] = scan_data
            
            return jsonify({
                'status': 'success',
                'message': f'Updated category from {original_category} to {correct_category}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update category'
            }), 400
    except Exception as e:
        logger.error(f"Category feedback error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/logout', methods=['POST'])
def logout():
    """API endpoint to log out"""
    try:
        # Revoke OAuth access if using OAuth
        if session.get('oauth_authenticated') and 'oauth_provider' in session:
            oauth_handler.revoke_access(session['oauth_provider'])
        
        # Clear the session
        session.clear()
        
        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        })
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

# API route for CSV export
@app.route('/api/export_csv', methods=['GET'])
def export_csv():
    """Export subscription data as CSV"""
    if 'email' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        if 'last_scan_data' not in session:
            return jsonify({
                'status': 'error',
                'message': 'No scan data available'
            }), 404
        
        # Create CSV in memory
        csv_output = StringIO()
        fieldnames = ['sender', 'category', 'last_received', 'unsubscribe_link']
        writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
        
        writer.writeheader()
        for item in session['last_scan_data']:
            writer.writerow({
                'sender': item.get('sender', 'Unknown'),
                'category': item.get('category', 'Unknown'),
                'last_received': item.get('last_received', 'N/A'),
                'unsubscribe_link': item.get('unsubscribe_link', '')
            })
        
        # Create response with CSV
        response = Response(
            csv_output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=subscriptions.csv'}
        )
        
        return response
    except Exception as e:
        logger.error(f"CSV export error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    
# Add this to your app.py file

@app.route('/debug_dashboard')
def debug_dashboard():
    """Debug endpoint to troubleshoot dashboard issues"""
    # Log session info
    logger.info(f"Session contains keys: {list(session.keys())}")
    
    # Create debug response
    debug_info = {
        'session': {
            'has_email': 'email' in session,
            'email': session.get('email', 'Not set'),
            'has_password': 'password' in session,
            'provider': session.get('provider', 'Not set'),
            'oauth_authenticated': session.get('oauth_authenticated', False),
            'has_scan_data': 'last_scan_data' in session,
            'scan_time': session.get('last_scan_time', 'Not set'),
            'total_found': session.get('total_found', 0),
            'total_unsubscribed': session.get('total_unsubscribed', 0)
        },
        'dashboard_rendering': {
            'can_render': 'email' in session and ('oauth_authenticated' in session or 'password' in session),
            'data_available': 'last_scan_data' in session and session.get('last_scan_data') is not None
        }
    }
    
    # Check if we have last_scan_data and it's valid
    if 'last_scan_data' in session and session['last_scan_data']:
        data_sample = session['last_scan_data'][:2] if len(session['last_scan_data']) > 2 else session['last_scan_data']
        debug_info['data_sample'] = data_sample
        debug_info['data_count'] = len(session['last_scan_data'])
    
    # Try to analyze the data and catch any errors
    if 'last_scan_data' in session and session['last_scan_data']:
        try:
            analytics = subscription_analytics.analyze_subscriptions(session['last_scan_data'], session.get('email'))
            debug_info['analytics'] = {
                'success': True,
                'categories': analytics.get('categories', {}),
                'recommendations_count': len(analytics.get('recommendations', []))
            }
        except Exception as e:
            debug_info['analytics'] = {
                'success': False,
                'error': str(e)
            }
    
    return jsonify(debug_info)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# Shutdown hook to clean up resources
@app.teardown_appcontext
def shutdown_scheduler(exception=None):
    """Shutdown the scheduler when the app context tears down"""
    email_scheduler.stop()

if __name__ == '__main__':
    try:
        app.run(debug=True, port=5002)
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
    finally:
        with app.app_context():
            if email_scheduler:
                logger.info("Application shut down, scheduler stopped")
                email_scheduler.stop()