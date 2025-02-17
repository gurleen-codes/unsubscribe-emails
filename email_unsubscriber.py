import imaplib
import email
import re
from typing import List, Dict
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

class EmailUnsubscriber:
    def __init__(self, email_address: str, app_password: str):
        self.email_address = email_address
        self.app_password = app_password
        
        # Verify it's a Gmail address
        if not email_address.endswith('@gmail.com'):
            raise ValueError("Currently only Gmail addresses are supported")
    
    def connect_to_email(self) -> imaplib.IMAP4_SSL:
        """Establish connection to Gmail"""
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.email_address, self.app_password)
            return mail
        except imaplib.IMAP4.error as e:
            if "Invalid credentials" in str(e):
                raise ConnectionError(
                    "Login failed. If using Gmail, make sure you're using an App Password. "
                    "Go to Google Account → Security → App Passwords to generate one."
                )
            raise ConnectionError(f"Failed to connect to Gmail: {str(e)}")

    def find_unsubscribe_links(self, num_emails: int = 50) -> List[Dict]:
        # Establish connection to Gmail
        mail = self.connect_to_email()  # This line defines the 'mail' variable
        mail.select("INBOX")

        # Use a more general search command
        _, message_numbers = mail.search(None, 'ALL')  # Change this line

        # Initialize the unsubscribe_data list
        unsubscribe_data = []

        # Process the message numbers
        message_numbers = message_numbers[0].split()  # Split the response into individual message IDs

        # Limit the number of emails processed
        for num in message_numbers[-num_emails:]:  # Get the last 'num_emails' emails
            # Fetch the email by ID
            _, msg_data = mail.fetch(num, '(RFC822)')
            message = email.message_from_bytes(msg_data[0][1])

            # Logic to find unsubscribe links in the email
            unsubscribe_link = self._find_body_unsubscribe(message)  # Example method to find unsubscribe link
            if unsubscribe_link:
                unsubscribe_data.append({
                'sender': message['From'],
                'unsubscribe_link': unsubscribe_link,
                'method': 'body',  # or 'header' based on your logic
                'provider': 'Gmail',
                'category': 'Promotions'  # or other categories based on your logic
                })
        print("Raw email content:", message.get_payload(decode=True))
        return unsubscribe_data

    def get_subscription_stats(self) -> Dict:
        """Get statistics about your newsletter subscriptions"""
        mail = self.connect_to_email()
        mail.select("INBOX")
        
        stats = {
            'total_promotional': 0,
            'frequent_senders': {},
            'categories': {
                'Promotions': 0,
                'Updates': 0,
                'Social': 0
            }
        }
        
        # Count promotional emails
        _, messages = mail.search(None, 'CATEGORY "PROMOTIONS"')
        stats['total_promotional'] = len(messages[0].split())
        
        return stats

    def _extract_url_from_header(self, header_unsubscribe: str) -> str:
        """Extract URL from List-Unsubscribe header"""
        urls = re.findall(r'<(https?://[^>]+)>', header_unsubscribe)
        return urls[0] if urls else None

    def _find_body_unsubscribe(self, message) -> str:
        """Find unsubscribe link in email body"""
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    return self._extract_unsubscribe_from_html(part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8'))
        else:
            if message.get_content_type() == "text/html":
                return self._extract_unsubscribe_from_html(message.get_payload(decode=True).decode(message.get_content_charset() or 'utf-8'))
        return None

    def _extract_unsubscribe_from_html(self, html_content: str) -> str:
        """Extract unsubscribe link from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        unsubscribe_keywords = ['unsubscribe', 'opt out', 'opt-out', 'remove me']
        
        for keyword in unsubscribe_keywords:
            links = soup.find_all('a', text=re.compile(keyword, re.IGNORECASE))
            if links:
                return links[0].get('href')
        return None

    def unsubscribe(self, link: str) -> bool:
        """
        Attempt to unsubscribe using the provided link
        Returns True if successful, False otherwise
        """
        try:
            response = requests.get(link)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to unsubscribe: {str(e)}")
            return False

# Example usage
if __name__ == "__main__":
    # Replace with actual email and password
    unsubscriber = EmailUnsubscriber("your_email@gmail.com", "your_password")
    
    # Find unsubscribe links
    unsubscribe_links = unsubscriber.find_unsubscribe_links(10)  # Scan last 10 emails
    
    # Print found unsubscribe opportunities
    for data in unsubscribe_links:
        print(f"\nSender: {data['sender']}")
        print(f"Unsubscribe Link: {data['unsubscribe_link']}")
        print(f"Method: {data['method']}")
