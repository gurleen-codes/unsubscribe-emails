from flask import Flask, render_template, request, jsonify, session, redirect
from email_unsubscriber import EmailUnsubscriber
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_emails():
    # Change to get JSON data instead of form data
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    num_emails = int(data.get('num_emails', 50))
    
    try:
        unsubscriber = EmailUnsubscriber(email, password)
        unsubscribe_links = unsubscriber.find_unsubscribe_links(num_emails)
        
        # Store credentials in session for later use
        session['email'] = email
        session['password'] = password
        
        return jsonify({
            'status': 'success',
            'data': unsubscribe_links,
            'redirect': '/dashboard'  # Add this line to tell the frontend to redirect
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

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