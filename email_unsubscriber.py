import imaplib
import email
import re
import time
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('EmailUnsubscriber')

class EmailUnsubscriber:
    def __init__(self, email_address: str, app_password: str, cache_file: str = None):
        self.email_address = email_address
        self.app_password = app_password
        self.email_provider = None
        self.custom_imap_server = None
        self.custom_imap_port = None
        self.cache_file = cache_file
        self.processed_emails = self._load_cache() if cache_file else set()

    def create_cache_key(self, email_address, num_emails):
        """Create a unique cache key for this email and scan parameters"""
        return f"{email_address}_{num_emails}"
        
    def _load_cache(self) -> set:
        """Load previously processed email IDs from cache file"""
        try:
            with open(self.cache_file, 'r') as f:
                return set(line.strip() for line in f)
        except (FileNotFoundError, IOError):
            return set()
            
    def _save_cache(self):
        """Save processed email IDs to cache file"""
        if not self.cache_file:
            return
            
        try:
            with open(self.cache_file, 'w') as f:
                for email_id in self.processed_emails:
                    f.write(f"{email_id}\n")
        except IOError as e:
            logger.error(f"Failed to save cache: {str(e)}")
    
    def connect_to_email(self) -> imaplib.IMAP4_SSL:
        """
        Establishes connection to email provider's IMAP server
        
        Returns:
        IMAP4_SSL: Connected mail object
        
        Raises:
        ConnectionError: If connection or authentication fails
        ValueError: If email provider is not supported
        """
        # Extract domain from email address
        domain = self.email_address.split('@')[-1].lower()
        
        # Configure server settings based on email provider
        if domain == 'gmail.com':
            server = "imap.gmail.com"
            port = 993
            error_help = ("Login failed. Make sure you're using an App Password. "
                        "Go to Google Account → Security → App Passwords to generate one.")
        elif domain in ['outlook.com', 'hotmail.com', 'live.com', 'msn.com']:
            server = "outlook.office365.com"
            port = 993
            error_help = ("Login failed. For Outlook, you may need to generate an app password. "
                        "Go to Account settings → Security → App passwords.")
        elif domain == 'yahoo.com':
            server = "imap.mail.yahoo.com"
            port = 993
            error_help = ("Login failed. For Yahoo Mail, you may need to generate an app password. "
                        "Go to Account Info → Account Security → Generate app password.")
        elif domain in ['aol.com', 'aim.com']:
            server = "imap.aol.com"
            port = 993
            error_help = ("Login failed. For AOL, you may need to generate an app password. "
                        "Go to Account Security → Generate app password.")
        elif domain in ['icloud.com', 'me.com', 'mac.com']:
            server = "imap.mail.me.com"
            port = 993
            error_help = ("Login failed. For iCloud, you need to generate an app-specific password. "
                        "Go to appleid.apple.com → Security → Generate Password.")
        elif domain == 'protonmail.com':
            server = "imap.protonmail.ch"
            port = 993
            error_help = ("Login failed. For ProtonMail, you need to set up the ProtonMail Bridge "
                        "application first and use those credentials.")
        elif domain == 'zoho.com':
            server = "imap.zoho.com"
            port = 993
            error_help = "Login failed. Check your Zoho Mail settings to ensure IMAP access is enabled."
        else:
            # Allow custom server configuration
            if hasattr(self, 'custom_imap_server') and hasattr(self, 'custom_imap_port'):
                server = self.custom_imap_server
                port = self.custom_imap_port
                error_help = "Login failed. Check your email provider's IMAP settings."
            else:
                raise ValueError(
                    f"Unsupported email provider: {domain}. "
                    "Please use a supported email provider or configure custom IMAP settings."
                )
        
        try:
            # Connect to server with appropriate settings
            mail = imaplib.IMAP4_SSL(server, port)
            mail.login(self.email_address, self.app_password)
            
            # Store provider info for later use
            self.email_provider = domain
            
            return mail
        except imaplib.IMAP4.error as e:
            if any(phrase in str(e).lower() for phrase in ["invalid credentials", "authentication failed"]):
                raise ConnectionError(f"{error_help}")
            raise ConnectionError(f"Failed to connect to email server: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Unexpected error connecting to email server: {str(e)}")

    def find_unsubscribe_links(self, num_emails: int = 50, folder: str = "INBOX") -> List[Dict]:
        """Find unsubscribe links in emails

        Args:
            num_emails: Number of recent emails to process
            folder: Email folder to search in

        Returns:
            List of dictionaries containing unsubscribe information
        """
        # Establish connection to email provider
        mail = self.connect_to_email()
        mail.select(folder)

        # Get total number of emails in folder
        status, data = mail.search(None, 'ALL')
        all_emails = data[0].split()
        total_emails = len(all_emails)
        
        # Process only the newest num_emails
        emails_to_process = min(num_emails, total_emails)
        message_numbers = all_emails[-emails_to_process:]
        
        # Initialize the unsubscribe_data list
        unsubscribe_data = []
        processed_count = 0
        skipped_count = 0

        # Process the message numbers
        for num in message_numbers:
            try:
                # Skip if already processed
                email_id = num.decode('utf-8')
                if email_id in self.processed_emails:
                    skipped_count += 1
                    continue
                    
                # Fetch the email by ID
                _, msg_data = mail.fetch(num, '(RFC822)')
                message = email.message_from_bytes(msg_data[0][1])

                # Get sender info
                from_header = message['From']
                sender_name = self._extract_sender_name(from_header)
                received_date = self._extract_date(message)

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
                        'email': from_header if '@' in from_header else None,
                        'unsubscribe_link': unsubscribe_link,
                        'method': method,
                        'provider': self.email_provider,
                        'category': self._determine_category(message),
                        'last_received': received_date,
                        'email_id': email_id
                    })
                
                # Mark as processed
                self.processed_emails.add(email_id)
                processed_count += 1
                
                # Update cache periodically
                if processed_count % 10 == 0:
                    self._save_cache()
            except Exception as e:
                logger.error(f"Error processing email {num}: {str(e)}")
                continue

        # Final cache update
        self._save_cache()
        
        logger.info(f"Processed {processed_count} emails, skipped {skipped_count} previously processed emails")
        logger.info(f"Found {len(unsubscribe_data)} unsubscribe links")
        
        return unsubscribe_data

    def _extract_date(self, message) -> str:
        """Extract and format the date from email"""
        date_str = message.get('Date')
        if not date_str:
            return "Unknown"
        
        try:
            # Parse the email date format
            for date_format in [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S'
            ]:
                try:
                    date_obj = datetime.strptime(date_str.strip(), date_format)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
                    
            # If all parsing attempts fail
            return date_str.split('+')[0].strip()
        except Exception:
            return date_str

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
        
        # Try to determine category from common senders or keywords
        from_header = message.get('From', '').lower()
        subject = message.get('Subject', '').lower()
        
        # Check for shopping/retail
        retail_keywords = ['shop', 'store', 'discount', 'sale', 'order', 'purchase', 'buy']
        if any(keyword in from_header or keyword in subject for keyword in retail_keywords):
            return 'Shopping'
            
        # Check for social
        social_keywords = ['friend', 'connect', 'network', 'social', 'follow', 'like', 'share']
        if any(keyword in from_header or keyword in subject for keyword in social_keywords):
            return 'Social'
            
        # Check for finance
        finance_keywords = ['bank', 'finance', 'credit', 'payment', 'account', 'statement', 'invest']
        if any(keyword in from_header or keyword in subject for keyword in finance_keywords):
            return 'Finance'
            
        # Check for travel
        travel_keywords = ['travel', 'flight', 'trip', 'vacation', 'hotel', 'booking']
        if any(keyword in from_header or keyword in subject for keyword in travel_keywords):
            return 'Travel'
            
        # Check for forums/communities
        forum_keywords = ['forum', 'community', 'discussion', 'member', 'group']
        if any(keyword in from_header or keyword in subject for keyword in forum_keywords):
            return 'Forums'
            
        # Check for updates/notifications
        update_keywords = ['update', 'alert', 'notification', 'confirm', 'verify', 'security']
        if any(keyword in from_header or keyword in subject for keyword in update_keywords):
            return 'Updates'
        
        # Default to Promotions if we can't determine
        return 'Promotions'

    def get_subscription_stats(self) -> Dict:
        """Get statistics about your newsletter subscriptions"""
        mail = self.connect_to_email()
        mail.select("INBOX")
        
        # Get total email count
        status, data = mail.search(None, 'ALL')
        total_emails = len(data[0].split())
    
        stats = {
            'total_emails': total_emails,
            'total_promotional': 0,
            'emails_per_day': {},
            'frequent_senders': {},
            'categories': {
                'Promotions': 0,
                'Updates': 0,
                'Social': 0,
                'Shopping': 0,
                'Finance': 0,
                'Travel': 0,
                'Forums': 0,
                'Unknown': 0
            }
        }

        # Generic search filter for newsletters (last 90 days)
        _, messages = mail.search(None, '(SINCE "90-days-ago") (FROM "newsletter" OR SUBJECT "unsubscribe" OR SUBJECT "offer" OR SUBJECT "deal")')
        message_ids = messages[0].split()
        stats['total_promotional'] = len(message_ids)
        
        # Sample a subset of promotional emails to analyze patterns
        sample_size = min(100, len(message_ids))
        if sample_size > 0:
            for msg_id in message_ids[:sample_size]:
                try:
                    # Fetch email data
                    _, msg_data = mail.fetch(msg_id, '(RFC822)')
                    message = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract sender
                    from_header = message.get('From', '')
                    sender = self._extract_sender_name(from_header)
                    
                    # Count frequency
                    if sender in stats['frequent_senders']:
                        stats['frequent_senders'][sender] += 1
                    else:
                        stats['frequent_senders'][sender] = 1
                        
                    # Categorize
                    category = self._determine_category(message)
                    if category in stats['categories']:
                        stats['categories'][category] += 1
                    else:
                        stats['categories']['Unknown'] += 1
                        
                    # Track by date
                    date = self._extract_date(message)
                    if date != "Unknown":
                        if date in stats['emails_per_day']:
                            stats['emails_per_day'][date] += 1
                        else:
                            stats['emails_per_day'][date] = 1
                except Exception as e:
                    logger.error(f"Error analyzing email {msg_id}: {str(e)}")
        
        # Sort frequent senders
        stats['frequent_senders'] = dict(sorted(stats['frequent_senders'].items(), 
                                               key=lambda item: item[1], 
                                               reverse=True)[:10])
        
        # Calculate time saved estimate (assuming 10 seconds per email)
        monthly_promotional = stats['total_promotional'] * 30 / 90  # Extrapolate to monthly
        stats['estimated_time_saved'] = round(monthly_promotional * 10 / 60)  # Convert to minutes
        
        return stats

    def _extract_url_from_header(self, header_unsubscribe: str) -> str:
        """Extract URL from List-Unsubscribe header"""
        urls = re.findall(r'<(https?://[^>]+)>', header_unsubscribe)
        if urls:
            return urls[0]
            
        # Check for mailto: links as fallback
        mailto = re.findall(r'<mailto:([^>]+)>', header_unsubscribe)
        if mailto:
            return f"mailto:{mailto[0]}"
            
        return None

    def set_custom_imap(self, server: str, port: int):
        """Set custom IMAP server for unsupported providers"""
        self.custom_imap_server = server
        self.custom_imap_port = port

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
                            logger.error(f"Error decoding HTML: {str(e)}")
        else:
            if message.get_content_type() == "text/html":
                html_content = message.get_payload(decode=True)
                if html_content:
                    try:
                        decoded = html_content.decode(message.get_content_charset() or 'utf-8', errors='replace')
                        return self._extract_unsubscribe_from_html(decoded)
                    except Exception as e:
                        logger.error(f"Error decoding HTML: {str(e)}")
        return None

    def _extract_unsubscribe_from_html(self, html_content: str) -> str:
        """Extract unsubscribe link from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        unsubscribe_keywords = ['unsubscribe', 'opt out', 'opt-out', 'remove me', 'cancel subscription', 
                               'stop receiving', 'manage preferences', 'email preferences']
        
        # Method 1: Find links with unsubscribe text
        for keyword in unsubscribe_keywords:
            # Look for links containing the keyword in their text
            links = soup.find_all('a', string=lambda text: text and keyword.lower() in text.lower() if text else False)
            if links and links[0].get('href'):
                return links[0].get('href')
            
            # Also look for links with the keyword in their href
            links = soup.find_all('a', href=lambda href: href and keyword.lower() in href.lower() if href else False)
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
        if not link:
            return False
            
        if link.startswith('mailto:'):
            logger.info(f"Manual unsubscribe required via email: {link}")
            return False
            
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # First check if the URL is valid
            parsed_url = urlparse(link)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                logger.error(f"Invalid URL: {link}")
                return False
                
            # Add rate limiting to avoid overwhelming servers
            time.sleep(1)
            
            # Make the request
            response = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
            
            # Log more details about the response
            logger.info(f"Unsubscribe request to {link}: Status {response.status_code}")
            
            return response.status_code < 400  # Anything below 400 is considered successful
        except requests.exceptions.Timeout:
            logger.error(f"Timeout when accessing {link}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error when accessing {link}")
            return False
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {str(e)}")
            return False
            
    def bulk_unsubscribe(self, links: List[str]) -> Dict[str, bool]:
        """
        Attempt to unsubscribe from multiple links
        Returns a dictionary with results for each link
        """
        results = {}
        for link in links:
            success = self.unsubscribe(link)
            results[link] = success
            # Add delay between requests
            time.sleep(2)
        return results