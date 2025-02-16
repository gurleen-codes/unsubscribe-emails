from flask import Flask, render_template, request, jsonify, session
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
            'data': unsubscribe_links
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

if __name__ == '__main__':
    app.run(debug=True) 