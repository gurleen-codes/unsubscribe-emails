# CleanInbox (formerly Email Unsubscriber)

A Python-based tool that helps you bulk unsubscribe from unwanted email newsletters and subscriptions. Now supports multiple email providers, including Gmail, Outlook, Yahoo, iCloud, AOL, and custom IMAP providers.
> **Note:** This project has been renamed from "Email Unsubscriber" to "CleanInbox", but the repository URL remains unchanged for compatibility purposes.

## Features

- 🔍 Automatically scans your email inbox for newsletter subscriptions
- 📊 Provides statistics about your newsletter subscriptions
- 🔐 Secure authentication using App Passwords for supported providers
- 🗑️ One-click unsubscribe from multiple newsletters
- 📁 Focuses on promotional emails across providers
- 🔄 Supports both header-based and in-body unsubscribe links
- 🖥️ Interactive dashboard for managing subscriptions visually
- 🌍 Support for multiple email providers beyond Gmail
- 📈 **New:** Categorized subscription analytics and statistics
- 🧹 **New:** Bulk unsubscribe feature for faster inbox cleaning

## Prerequisites

- Python 3.7 or higher
- A valid email account (Gmail, Outlook, Yahoo, iCloud, AOL, etc.)
- Some providers require an **App Password** (Gmail, Yahoo, iCloud, AOL)

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

## Email Provider Setup

Depending on your email provider, you may need to enable IMAP access and generate an **App Password**:

- **Gmail**: Go to your [Google Account Security](https://myaccount.google.com/) → App Passwords.
- **Yahoo**: Visit [Yahoo Account Security](https://login.yahoo.com/account/security) → Generate App Password.
- **Outlook/Hotmail**: Go to [Microsoft Account Security](https://account.live.com/proofs/AppPassword) → Create App Password.
- **iCloud**: Visit [Apple ID Security](https://appleid.apple.com/) → Generate App Password.
- **AOL**: Enable App Passwords in [AOL Account Security](https://login.aol.com/account/security).

If your email provider is not listed, you can **manually set the IMAP server**:
```python
unsubscriber = EmailUnsubscriber("user@custommail.com", "password")
unsubscriber.set_custom_imap("imap.custommail.com", 993)
```

## Usage

1. Start the web interface:
```bash
python app.py
```

2. Open your browser and go to:
```
http://127.0.0.1:5001
```

3. Enter your email address, select your provider, and enter the App Password.
4. Click **Scan Emails** to start scanning for newsletters.
5. You'll be redirected to the dashboard where you can manage and unsubscribe from your subscriptions.

## **Dashboard Feature**

The tool includes a comprehensive **interactive dashboard** that provides a user-friendly way to manage your subscriptions.

### **How to Use the Dashboard**
1. After scanning, the dashboard displays:
   - **Total subscriptions found**
   - **Categories of subscriptions**
   - **Successfully unsubscribed emails**
   - **Subscription statistics**
2. You can select multiple emails and use the bulk unsubscribe feature to remove them from mailing lists.
3. The dashboard dynamically updates as new emails are scanned or unsubscribed.
4. View categorized statistics to understand your email subscription patterns.

## API Documentation

### EmailUnsubscriber Class

#### Initialization
```python
unsubscriber = EmailUnsubscriber(email_address: str, app_password: str)
```
- `email_address`: Valid email address
- `app_password`: App Password from the provider (if required)

#### Methods

1. `connect_to_email() -> imaplib.IMAP4_SSL`
```python
def connect_to_email(self) -> imaplib.IMAP4_SSL:
    """
    Establishes connection to the email provider's IMAP server
    Returns:
        IMAP4_SSL: Connected mail object
    Raises:
        ConnectionError: If connection or authentication fails
    """
```

2. `find_unsubscribe_links(num_emails: int = 50) -> List[Dict]`
```python
def find_unsubscribe_links(self, num_emails: int = 50) -> List[Dict]:
    """
    Scans inbox for newsletter subscriptions
    """
```

3. `get_subscription_stats() -> Dict`
```python
def get_subscription_stats(self) -> Dict:
    """
    Retrieves statistics about newsletter subscriptions
    """
```

4. `unsubscribe(link: str) -> bool`
```python
def unsubscribe(self, link: str) -> bool:
    """
    Attempts to unsubscribe using provided link
    """
```

## Security Notes

- Never share your App Password
- The tool stores credentials only in session memory
- The web interface is for development use only; additional security measures are needed for production

## Limitations

- Success rate depends on how newsletters implement their unsubscribe functionality

## 🔧 Troubleshooting

### ❌ `TypeError: bad operand type for unary -: 'str'`
✅ **Fix:** Ensure `num_emails` is an integer in both frontend and backend.

### ❌ `500 Internal Server Error`
✅ **Fix:** Check Flask logs (`flask run --debug`) for the exact error.

### ❌ `200 OK but "An error occurred" in UI`
✅ **Fix:** The backend response format has changed. Ensure `data.data` is checked instead of `data.status`.

### ❌ `"Failed to load resource: 404 NOT FOUND"`
✅ **Fix:** Ensure static assets (SVG files) are inside `static/images/` and referenced correctly.


## Future Improvements

- [ ] OAuth2 authentication support for secure login
- [ ] Improved handling of provider-specific email categories
- [x] Batch unsubscribe operations
- [ ] Progress tracking for long operations
- [x] Subscription analytics and reporting
- [ ] Browser extension integration
- [ ] Email categorization machine learning model
- [ ] Scheduled re-scanning of the inbox

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository.



