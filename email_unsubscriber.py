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
        mail = self.connect_to_email()
        mail.select("INBOX")

        # Use a more general search command
        _, message_numbers = mail.search(None, 'ALL')

        # Initialize the unsubscribe_data list
        unsubscribe_data = []

        # Process the message numbers
        message_numbers = message_numbers[0].split()  # Split the response into individual message IDs

        # Limit the number of emails processed
        for num in message_numbers[-num_emails:]:  # Get the last 'num_emails' emails
            try:
                # Fetch the email by ID
                _, msg_data = mail.fetch(num, '(RFC822)')
                message = email.message_from_bytes(msg_data[0][1])

                # Get sender info
                from_header = message['From']
                sender_name = self._extract_sender_name(from_header)

                # Check for header unsubscribe first
                header_unsubscribe = message.get('List-Unsubscribe')
                if header_unsubscribe:
                    unsubscribe_link = self._extract_url_from_header(header_unsubscribe)
                    method = 'header'
                else:
                    # Fall back to body unsubscribe
                    unsubscribe_link = self._find_body_unsubscribe(message)
                    method = 'body'

                if unsubscribe_link:
                    unsubscribe_data.append({
                        'sender': sender_name or from_header,
                        'unsubscribe_link': unsubscribe_link,
                        'method': method,
                        'provider': 'Gmail',
                        'category': self._determine_category(message)
                    })
            except Exception as e:
                print(f"Error processing email {num}: {str(e)}")
                continue

        return unsubscribe_data

    def _extract_sender_name(self, from_header: str) -> str:
        """Extract a clean sender name from the From header"""
        # Try to extract name from format "Name <email@example.com>"
        match = re.search(r'"?([^"<]+)"?\s*<', from_header)
        if match:
            return match.group(1).strip()
        
        # If no name format, use the domain part of the email
        match = re.search(r'@([^.]+)', from_header)
        if match:
            return match.group(1).capitalize()
            
        return from_header.split('@')[0] if '@' in from_header else from_header

    def _determine_category(self, message) -> str:
        """Determine email category based on headers or content"""
        # Use Gmail categories if available
        headers = message.items()
        for name, value in headers:
            if name.lower() == 'x-gmail-labels' and 'category:' in value.lower():
                category_match = re.search(r'category:(\w+)', value, re.IGNORECASE)
                if category_match:
                    return category_match.group(1)
        
        # Default to Promotions if we can't determine
        return 'Promotions'

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
                    html_content = part.get_payload(decode=True)
                    if html_content:
                        try:
                            decoded = html_content.decode(part.get_content_charset() or 'utf-8', errors='replace')
                            return self._extract_unsubscribe_from_html(decoded)
                        except Exception as e:
                            print(f"Error decoding HTML: {str(e)}")
        else:
            if message.get_content_type() == "text/html":
                html_content = message.get_payload(decode=True)
                if html_content:
                    try:
                        decoded = html_content.decode(message.get_content_charset() or 'utf-8', errors='replace')
                        return self._extract_unsubscribe_from_html(decoded)
                    except Exception as e:
                        print(f"Error decoding HTML: {str(e)}")
        return None

    def _extract_unsubscribe_from_html(self, html_content: str) -> str:
        """Extract unsubscribe link from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        unsubscribe_keywords = ['unsubscribe', 'opt out', 'opt-out', 'remove me', 'cancel subscription']
        
        # Method 1: Find links with unsubscribe text
        for keyword in unsubscribe_keywords:
            # Look for links containing the keyword in their text
            links = soup.find_all('a', string=lambda text: text and keyword in text.lower())
            if links and links[0].get('href'):
                return links[0].get('href')
            
            # Also look for links with the keyword in their href
            links = soup.find_all('a', href=lambda href: href and keyword in href.lower())
            if links and links[0].get('href'):
                return links[0].get('href')
        
        # Method 2: Find buttons/links with class names or ids suggesting unsubscribe functionality
        potential_elements = soup.find_all(['a', 'button'], 
                                          attrs={'class': lambda x: x and any(keyword in x.lower() for keyword in unsubscribe_keywords) if x else False})
        if potential_elements:
            # For buttons, try to find the parent form's action
            for elem in potential_elements:
                if elem.name == 'button':
                    parent_form = elem.find_parent('form')
                    if parent_form and parent_form.get('action'):
                        return parent_form.get('action')
                elif elem.name == 'a' and elem.get('href'):
                    return elem.get('href')
        
        # Method 3: Look for text near the bottom that might contain "unsubscribe"
        footer_elements = soup.find_all(['footer', 'div'], class_=lambda x: x and ('footer' in x.lower() or 'bottom' in x.lower()) if x else False)
        for footer in footer_elements:
            links = footer.find_all('a')
            for link in links:
                if link.text and any(keyword in link.text.lower() for keyword in unsubscribe_keywords):
                    return link.get('href')
        
        # If all else fails, search the entire document for any link with unsubscribe text
        all_links = soup.find_all('a')
        for link in all_links:
            if link.text and any(keyword in link.text.lower() for keyword in unsubscribe_keywords):
                return link.get('href')
            
        return None

    def unsubscribe(self, link: str) -> bool:
        """
        Attempt to unsubscribe using the provided link
        Returns True if successful, False otherwise
        """
        if not link or link == 'manual_unsubscribe':
            return False
            
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(link, headers=headers, timeout=10)
            return response.status_code < 400  # Anything below 400 is considered successful
        except Exception as e:
            print(f"Failed to unsubscribe: {str(e)}")
            return False