from flask import Flask, render_template, request, jsonify, session, redirect, send_from_directory
from email_unsubscriber import EmailUnsubscriber
import os
from datetime import datetime

app = Flask(__name__, static_folder="static")
app.secret_key = os.urandom(24)  # For session management

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_emails():
    try:
        data = request.json
        email_address = data['email']
        password = data['password']
        provider = data['provider']
        
        # Store credentials in session for future API calls
        session['email'] = email_address
        session['password'] = password
        session['provider'] = provider
        
        # Store custom IMAP settings if provided
        if provider == "custom":
            session['custom_server'] = data['custom_server']
            session['custom_port'] = data['custom_port']
        
        unsubscriber = EmailUnsubscriber(email_address, password)
        
        # If user selects "Custom Provider", use their custom IMAP settings
        if provider == "custom":
            unsubscriber.set_custom_imap(data['custom_server'], int(data['custom_port']))
        
        unsubscribe_data = unsubscriber.find_unsubscribe_links(num_emails=int(data.get('num_emails', 50)))
        
        # Process the data to match dashboard expectations
        processed_data = []
        for item in unsubscribe_data:
            # Ensure each item has expected fields or default values
            processed_item = {
                'sender': item.get('sender', 'Unknown Sender'),
                'category': item.get('category', 'Unknown'),
                'last_received': item.get('date', 'N/A'),
                'unsubscribe_link': item.get('unsubscribe_link', '')
            }
            processed_data.append(processed_item)
        
        # Include redirect information and additional stats
        return jsonify({
            'status': 'success',
            'data': processed_data,
            'redirect': '/dashboard',
            'totalUnsubscribed': 0,  # Initial value, will be updated as user unsubscribes
            'timeSaved': calculate_time_saved(len(processed_data))  # You'll need to implement this function
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Helper function to estimate time saved based on number of subscriptions
def calculate_time_saved(num_subscriptions):
    # Assuming each email takes ~30 seconds to process manually
    return num_subscriptions * 0.5  # Return time in minutes

@app.route('/store_credentials', methods=['POST'])
def store_credentials():
    data = request.get_json()
    session['email'] = data.get('email')
    session['password'] = data.get('password')
    return jsonify({'status': 'success'})

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    # Change to get JSON data instead of form data
    data = request.get_json()
    link = data.get('link')
    sender = data.get('sender')
    
    try:
        unsubscriber = EmailUnsubscriber(session.get('email'), session.get('password'))
        success = unsubscriber.unsubscribe(link)
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': f'Successfully unsubscribed from {sender}' if success else f'Failed to unsubscribe from {sender}'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Redirect to login if not authenticated
    if 'email' not in session or 'password' not in session:
        return redirect('/')
    
    # Pass the email to the template
    return render_template('dashboard.html', email=session.get('email'))

@app.route('/api/subscription_data', methods=['GET'])
def get_subscription_data():
    # Only proceed if user is logged in
    if 'email' not in session or 'password' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
    try:
        unsubscriber = EmailUnsubscriber(session.get('email'), session.get('password'))
        # Get unsubscribe links (this reuses your existing function)
        unsubscribe_links = unsubscriber.find_unsubscribe_links()
        
        # Get basic stats
        stats = {
            'total_found': len(unsubscribe_links),
            'categories': {}
        }
        
        # Count by category
        for item in unsubscribe_links:
            category = item.get('category', 'Other')
            if category in stats['categories']:
                stats['categories'][category] += 1
            else:
                stats['categories'][category] = 1
        
        return jsonify({
            'status': 'success',
            'subscriptions': unsubscribe_links,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/bulk_unsubscribe', methods=['POST'])
def bulk_unsubscribe():
    if 'email' not in session or 'password' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    links = data.get('links', [])
    
    try:
        unsubscriber = EmailUnsubscriber(session.get('email'), session.get('password'))
        results = []
        
        for link_info in links:
            success = unsubscriber.unsubscribe(link_info['link'])
            results.append({
                'sender': link_info['sender'],
                'success': success
            })
        
        return jsonify({
            'status': 'success',
            'results': results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001) 