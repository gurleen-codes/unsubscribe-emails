import os
import json
import requests
import base64
import secrets
from flask import redirect, request, url_for, session
import logging
from oauthlib.oauth2 import WebApplicationClient
from urllib.parse import urlencode

# Setup logging
auth_logger = logging.getLogger('OAuthHandler')

class OAuthHandler:
    """
    Class to handle OAuth 2.0 authentication with various email providers
    """
    def __init__(self, app):
        self.app = app
        self.clients = {}
        self.provider_configs = {
            'gmail': {
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'userinfo_uri': 'https://www.googleapis.com/oauth2/v1/userinfo',
                'scopes': ['https://mail.google.com/'],
                'required_config': ['client_id', 'client_secret', 'redirect_uri']
            },
            'outlook': {
                'auth_uri': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                'token_uri': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                'userinfo_uri': 'https://graph.microsoft.com/v1.0/me',
                'scopes': ['https://outlook.office.com/IMAP.AccessAsUser.All', 'offline_access', 'user.read'],
                'required_config': ['client_id', 'client_secret', 'redirect_uri']
            }
        }
        
        # Load OAuth config from environment variables or config file
        self.load_config()
        
    def load_config(self):
        """Load OAuth configuration from environment or config file"""
        try:
            # Try to load from environment variables first
            for provider in self.provider_configs:
                client_id = os.environ.get(f'{provider.upper()}_CLIENT_ID')
                client_secret = os.environ.get(f'{provider.upper()}_CLIENT_SECRET')
                redirect_uri = os.environ.get(f'{provider.upper()}_REDIRECT_URI')
                
                if client_id and client_secret and redirect_uri:
                    self.provider_configs[provider]['client_id'] = client_id
                    self.provider_configs[provider]['client_secret'] = client_secret
                    self.provider_configs[provider]['redirect_uri'] = redirect_uri
                    
                    # Create OAuth client for this provider
                    self.clients[provider] = WebApplicationClient(client_id)
                    auth_logger.info(f"Configured OAuth for {provider} from environment")
            
            # If any providers are still missing configuration, try loading from config file
            config_file = os.environ.get('OAUTH_CONFIG_FILE', 'oauth_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    
                for provider, config in file_config.items():
                    if provider in self.provider_configs and provider not in self.clients:
                        # Check if all required config is present
                        required_config = self.provider_configs[provider]['required_config']
                        if all(key in config for key in required_config):
                            # Update provider config
                            for key, value in config.items():
                                self.provider_configs[provider][key] = value
                            
                            # Create OAuth client
                            self.clients[provider] = WebApplicationClient(config['client_id'])
                            auth_logger.info(f"Configured OAuth for {provider} from config file")
        except Exception as e:
            auth_logger.error(f"Error loading OAuth configuration: {str(e)}")
    
    def get_auth_url(self, provider):
        """
        Get the authorization URL for the specified provider
        
        Args:
            provider: Name of the provider (e.g., 'gmail', 'outlook')
            
        Returns:
            str: Authorization URL or None if provider is not configured
        """
        if provider not in self.clients:
            auth_logger.error(f"OAuth not configured for provider: {provider}")
            return None
        
        # Generate state token for CSRF protection
        state = secrets.token_urlsafe(16)
        session['oauth_state'] = state
        session['oauth_provider'] = provider
        
        # Get provider configuration
        provider_config = self.provider_configs[provider]
        client = self.clients[provider]
        
        # Create request URI
        try:
            request_uri = client.prepare_request_uri(
                provider_config['auth_uri'],
                redirect_uri=provider_config['redirect_uri'],
                scope=provider_config['scopes'],
                state=state
            )
            return request_uri
        except Exception as e:
            auth_logger.error(f"Error generating auth URL for {provider}: {str(e)}")
            return None
    
    def handle_callback(self, request):
        """
        Handle the OAuth callback
        
        Args:
            request: Flask request object
            
        Returns:
            dict: Authentication result with tokens and user info
        """
        # Get state and provider from session
        state = session.get('oauth_state')
        provider = session.get('oauth_provider')
        
        if not state or not provider:
            auth_logger.error("No OAuth state or provider in session")
            return {'success': False, 'error': 'No OAuth state or provider in session'}
        
        # Verify state matches
        if request.args.get('state') != state:
            auth_logger.error("State mismatch in OAuth callback")
            return {'success': False, 'error': 'Invalid state parameter'}
        
        # Check if provider is configured
        if provider not in self.clients:
            auth_logger.error(f"OAuth not configured for provider: {provider}")
            return {'success': False, 'error': f'OAuth not configured for provider: {provider}'}
        
        # Get provider configuration and client
        provider_config = self.provider_configs[provider]
        client = self.clients[provider]
        
        # Get authorization code from request
        code = request.args.get('code')
        if not code:
            auth_logger.error("No authorization code in callback")
            return {'success': False, 'error': 'No authorization code received'}
        
        # Prepare token request
        try:
            token_url, headers, body = client.prepare_token_request(
                provider_config['token_uri'],
                authorization_response=request.url,
                redirect_url=request.base_url,
                code=code
            )
            
            # Add client authentication
            basic_auth = base64.b64encode(
                f"{provider_config['client_id']}:{provider_config['client_secret']}".encode()
            ).decode()
            headers['Authorization'] = f'Basic {basic_auth}'
            
            # Exchange authorization code for tokens
            token_response = requests.post(
                token_url,
                headers=headers,
                data=body,
                timeout=10
            )
            
            # Parse token response
            client.parse_request_body_response(token_response.text)
            
            # Get user info
            userinfo_uri = provider_config['userinfo_uri']
            uri, headers, body = client.add_token(userinfo_uri)
            userinfo_response = requests.get(uri, headers=headers, data=body)
            userinfo = userinfo_response.json()
            
            # Store tokens in session
            session['oauth_tokens'] = {
                'access_token': client.token['access_token'],
                'refresh_token': client.token.get('refresh_token'),
                'expires_at': client.token['expires_at']
            }
            
            # Store user info in session
            session['oauth_userinfo'] = userinfo
            
            # For email providers, get email address
            email = None
            if provider == 'gmail':
                email = userinfo.get('email')
            elif provider == 'outlook':
                email = userinfo.get('mail') or userinfo.get('userPrincipalName')
            
            if email:
                session['email'] = email
                session['oauth_authenticated'] = True
                session['oauth_provider'] = provider
            
            return {
                'success': True,
                'provider': provider,
                'email': email,
                'userinfo': userinfo,
                'access_token': client.token['access_token']
            }
        except Exception as e:
            auth_logger.error(f"Error in OAuth callback: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def refresh_token(self, provider):
        """
        Refresh the access token if a refresh token is available
        
        Args:
            provider: Provider name
            
        Returns:
            bool: True if token was refreshed successfully
        """
        # Check if we have tokens in session
        tokens = session.get('oauth_tokens')
        if not tokens or 'refresh_token' not in tokens:
            auth_logger.error(f"No refresh token available for {provider}")
            return False
        
        # Check if provider is configured
        if provider not in self.clients:
            auth_logger.error(f"OAuth not configured for provider: {provider}")
            return False
        
        # Get provider configuration and client
        provider_config = self.provider_configs[provider]
        client = self.clients[provider]
        
        try:
            # Prepare refresh token request
            refresh_url, headers, body = client.prepare_refresh_token_request(
                provider_config['token_uri'],
                refresh_token=tokens['refresh_token'],
                client_id=provider_config['client_id'],
                client_secret=provider_config['client_secret']
            )
            
            # Make refresh token request
            response = requests.post(
                refresh_url,
                headers=headers,
                data=body,
                timeout=10
            )
            
            # Parse response
            client.parse_request_body_response(response.text)
            
            # Update session with new tokens
            session['oauth_tokens'] = {
                'access_token': client.token['access_token'],
                'refresh_token': client.token.get('refresh_token', tokens['refresh_token']),
                'expires_at': client.token['expires_at']
            }
            
            auth_logger.info(f"Successfully refreshed token for {provider}")
            return True
        except Exception as e:
            auth_logger.error(f"Error refreshing token for {provider}: {str(e)}")
            return False
    
    def revoke_access(self, provider):
        """
        Revoke OAuth access (logout)
        
        Args:
            provider: Provider name
            
        Returns:
            bool: True if access was revoked successfully
        """
        # Check if we have tokens in session
        tokens = session.get('oauth_tokens')
        if not tokens or 'access_token' not in tokens:
            # No tokens to revoke, just clear session
            if 'oauth_tokens' in session:
                del session['oauth_tokens']
            if 'oauth_userinfo' in session:
                del session['oauth_userinfo']
            if 'oauth_authenticated' in session:
                del session['oauth_authenticated']
            return True
        
        # Different revocation endpoints for different providers
        revocation_endpoints = {
            'gmail': 'https://oauth2.googleapis.com/revoke',
            'outlook': 'https://login.microsoftonline.com/common/oauth2/v2.0/logout'
        }
        
        if provider not in revocation_endpoints:
            auth_logger.error(f"No revocation endpoint for provider: {provider}")
            return False
        
        try:
            # Revoke the token
            response = requests.post(
                revocation_endpoints[provider],
                params={'token': tokens['access_token']},
                timeout=10
            )
            
            # Clear session
            if 'oauth_tokens' in session:
                del session['oauth_tokens']
            if 'oauth_userinfo' in session:
                del session['oauth_userinfo']
            if 'oauth_authenticated' in session:
                del session['oauth_authenticated']
            
            auth_logger.info(f"Successfully revoked access for {provider}")
            return True
        except Exception as e:
            auth_logger.error(f"Error revoking access for {provider}: {str(e)}")
            return False