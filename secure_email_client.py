import imaplib
import ssl
import logging
import base64
from email_unsubscriber import EmailUnsubscriber

# Setup logging
client_logger = logging.getLogger('SecureEmailClient')

class SecureEmailClient:
    """
    Enhanced email client that supports both password and OAuth authentication.
    This class serves as a wrapper around EmailUnsubscriber with improved security features.
    """
    def __init__(self, email, provider, oauth_handler=None):
        """
        Initialize the secure email client
        
        Args:
            email: User's email address
            provider: Email provider (gmail, outlook, etc.)
            oauth_handler: OAuthHandler instance for token-based authentication
        """
        self.email = email
        self.provider = provider
        self.oauth_handler = oauth_handler
        self.password = None
        self.unsubscriber = None
        self.is_oauth = False
        self.custom_server = None
        self.custom_port = None
    
    def set_password(self, password):
        """Set password for password-based authentication"""
        self.password = password
        self.is_oauth = False
    
    def set_custom_imap(self, server, port):
        """Set custom IMAP server details"""
        self.custom_server = server
        self.custom_port = port
    
    def authenticate(self):
        """
        Authenticate with the email provider
        
        Returns:
            bool: True if authentication was successful
        """
        try:
            # Initialize the unsubscriber
            if self.is_oauth and self.oauth_handler:
                # For OAuth, we need to get the token
                access_token = self._get_oauth_token()
                if not access_token:
                    return False
                
                # Create unsubscriber with email only
                self.unsubscriber = EmailUnsubscriber(self.email, None)
                
                # Override the connect_to_email method to use OAuth
                self._setup_oauth_connection(access_token)
            else:
                # For password auth, use the standard EmailUnsubscriber
                if not self.password:
                    client_logger.error("No password provided for password authentication")
                    return False
                
                self.unsubscriber = EmailUnsubscriber(self.email, self.password)
                
                # Set custom IMAP if provided
                if self.custom_server and self.custom_port:
                    self.unsubscriber.set_custom_imap(self.custom_server, self.custom_port)
            
            # Test connection by connecting to the email server
            mail = self.unsubscriber.connect_to_email()
            mail.logout()
            return True
        except Exception as e:
            client_logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def _get_oauth_token(self):
        """
        Get OAuth access token, refreshing if necessary
        
        Returns:
            str: Access token or None if not available
        """
        if not self.oauth_handler:
            return None
        
        # Check if we need to refresh the token
        from flask import session
        tokens = session.get('oauth_tokens', {})
        
        if 'access_token' not in tokens:
            client_logger.error("No access token available")
            return None
        
        import time
        if 'expires_at' in tokens and tokens['expires_at'] < time.time() + 60:
            # Token is about to expire, refresh it
            if not self.oauth_handler.refresh_token(self.provider):
                return None
            
            # Get the updated tokens
            tokens = session.get('oauth_tokens', {})
        
        return tokens.get('access_token')
    
    def _setup_oauth_connection(self, access_token):
        """
        Override the connect_to_email method in EmailUnsubscriber to use OAuth
        
        Args:
            access_token: OAuth access token
        """
        original_connect = self.unsubscriber.connect_to_email
        
        def oauth_connect():
            domain = self.email.split('@')[-1].lower()
            
            # Configure server settings based on email provider
            if domain == 'gmail.com':
                server = "imap.gmail.com"
                port = 993
            elif domain in ['outlook.com', 'hotmail.com', 'live.com', 'msn.com']:
                server = "outlook.office365.com"
                port = 993
            elif self.custom_server and self.custom_port:
                server = self.custom_server
                port = self.custom_port
            else:
                # Fall back to original connection method for other providers
                return original_connect()
            
            try:
                # Connect to server with SSL
                mail = imaplib.IMAP4_SSL(server, port)
                
                # Authenticate with OAuth2
                auth_string = f'user={self.email}\1auth=Bearer {access_token}\1\1'
                auth_string_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
                
                mail.authenticate('XOAUTH2', lambda x: auth_string_b64)
                
                return mail
            except imaplib.IMAP4.error as e:
                client_logger.error(f"IMAP error during OAuth connection: {str(e)}")
                raise ConnectionError(f"Failed to connect with OAuth: {str(e)}")
            except Exception as e:
                client_logger.error(f"Unexpected error during OAuth connection: {str(e)}")
                raise ConnectionError(f"Unexpected error connecting with OAuth: {str(e)}")
        
        # Replace the connect method
        self.unsubscriber.connect_to_email = oauth_connect
    
    def find_unsubscribe_links(self, num_emails=50, folder="INBOX"):
        """Find unsubscribe links in emails"""
        if not self.unsubscriber:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        return self.unsubscriber.find_unsubscribe_links(num_emails, folder)
    
    def unsubscribe(self, link):
        """Attempt to unsubscribe using provided link"""
        if not self.unsubscriber:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        return self.unsubscriber.unsubscribe(link)
    
    def bulk_unsubscribe(self, links):
        """Attempt to unsubscribe from multiple links"""
        if not self.unsubscriber:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        return self.unsubscriber.bulk_unsubscribe(links)
    
    def get_subscription_stats(self):
        """Get statistics about subscriptions"""
        if not self.unsubscriber:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        return self.unsubscriber.get_subscription_stats()
    
    def use_oauth(self):
        """Switch to OAuth authentication"""
        self.is_oauth = True
        self.password = None
        
    def use_password(self):
        """Switch to password authentication"""
        self.is_oauth = False