# Email Unsubscriber

A Python-based tool that helps you bulk unsubscribe from unwanted email newsletters and subscriptions. Currently optimized for Gmail accounts.

## Features

- 🔍 Automatically scans your Gmail inbox for newsletter subscriptions
- 📊 Provides statistics about your newsletter subscriptions
- 🔐 Secure authentication using Gmail App Passwords
- 🗑️ One-click unsubscribe from multiple newsletters
- 📁 Focuses on promotional emails in Gmail
- 🔄 Supports both header-based and in-body unsubscribe links
- 🖥️ **New:** Interactive dashboard for managing subscriptions visually

## Prerequisites

- Python 3.7 or higher
- A Gmail account
- Gmail App Password (2FA must be enabled)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/email-unsubscriber.git
cd email-unsubscriber
```

2. Install required packages:

```bash
pip install flask requests beautifulsoup4 email-validator
```

## Gmail Setup

Before using the tool, you need to set up Gmail App Password:

1. Go to your [Google Account Settings](https://myaccount.google.com/)
2. Navigate to Security
3. Enable 2-Step Verification if not already enabled
4. Under "App passwords":
   - Select "Mail" as the app
   - Select "Other" as the device
   - Give it a name (e.g., "Email Unsubscriber")
   - Click "Generate"
5. Save the 16-character password generated

## Usage

1. Start the web interface:
```bash
python app.py
```

2. Open your browser and go to:
```
http://127.0.0.1:5001
```

3. Enter your Gmail address and the App Password you generated
4. Click "Scan Emails" to start scanning for newsletters

## **Dashboard Feature**

The tool now includes an **interactive dashboard** that provides a user-friendly way to manage your subscriptions.

### **How to Use the Dashboard**
1. After scanning, the dashboard displays:
   - **Total subscriptions found**
   - **Successfully unsubscribed emails**
   - **Estimated time saved**
2. You can select emails and click **Unsubscribe** to remove them from mailing lists.
3. The dashboard dynamically updates as new emails are scanned.

## API Documentation

### EmailUnsubscriber Class

#### Initialization
```python
unsubscriber = EmailUnsubscriber(email_address: str, app_password: str)
```
- `email_address`: Gmail address (must end with @gmail.com)
- `app_password`: 16-character App Password from Google Account

#### Methods

1. `connect_to_email() -> imaplib.IMAP4_SSL`
```python
def connect_to_email(self) -> imaplib.IMAP4_SSL:
    """
    Establishes connection to Gmail's IMAP server
    
    Returns:
        IMAP4_SSL: Connected mail object
    
    Raises:
        ConnectionError: If connection or authentication fails
        ValueError: If email is not a Gmail address
    """
```

2. `find_unsubscribe_links(num_emails: int = 50) -> List[Dict]`
```python
def find_unsubscribe_links(self, num_emails: int = 50) -> List[Dict]:
    """
    Scans Gmail inbox for newsletter subscriptions
    
    Args:
        num_emails (int): Number of recent emails to scan
    
    Returns:
        List[Dict]: List of dictionaries containing:
            {
                'sender': str,           # Email address of sender
                'unsubscribe_link': str, # URL to unsubscribe
                'method': str,           # 'header' or 'body'
                'provider': str,         # Always 'Gmail'
                'category': str          # Gmail category (e.g., 'Promotions')
            }
    """
```

3. `get_subscription_stats() -> Dict`
```python
def get_subscription_stats(self) -> Dict:
    """
    Retrieves statistics about newsletter subscriptions
    
    Returns:
        Dict: Statistics containing:
            {
                'total_promotional': int,    # Total promotional emails
                'frequent_senders': Dict,    # Sender frequency count
                'categories': {              # Emails by Gmail category
                    'Promotions': int,
                    'Updates': int,
                    'Social': int
                }
            }
    """
```

4. `unsubscribe(link: str) -> bool`
```python
def unsubscribe(self, link: str) -> bool:
    """
    Attempts to unsubscribe using provided link
    
    Args:
        link (str): Unsubscribe URL from find_unsubscribe_links()
    
    Returns:
        bool: True if unsubscribe request was successful (HTTP 200)
    """
```

## Security Notes

- Never share your Gmail App Password
- The tool stores credentials only in session memory
- Always use App Passwords instead of your main Gmail password
- The web interface is for development use only; additional security measures are needed for production

## Limitations

- Currently supports Gmail accounts only
- Requires IMAP access to be enabled in Gmail
- Some unsubscribe links may require manual intervention
- Success rate depends on how newsletters implement their unsubscribe functionality

## Future Improvements

- [ ] OAuth2 authentication support
- [ ] Support for other email providers
- [ ] Batch unsubscribe operations
- [ ] Email provider selection
- [ ] Progress tracking for long operations
- [ ] Subscription analytics and reporting
- [ ] Browser extension integration

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository.
