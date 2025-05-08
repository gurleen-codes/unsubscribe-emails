import React, { useState } from 'react';

const ModernLogin = () => {
  const [activeTab, setActiveTab] = useState('password');
  const [provider, setProvider] = useState('gmail');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showCustomFields, setShowCustomFields] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    num_emails: 100,
    custom_server: '',
    custom_port: 993
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: name === 'num_emails' || name === 'custom_port' ? parseInt(value) : value
    });
  };

  const handleProviderSelect = (selectedProvider) => {
    setProvider(selectedProvider);
    setShowCustomFields(selectedProvider === 'custom');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Determine if we're using OAuth or password authentication
      const isOAuth = activeTab === 'oauth';
      
      // Prepare data for the request
      const requestData = {
        email: formData.email,
        provider,
        num_emails: formData.num_emails,
        use_oauth: isOAuth
      };
      
      // Add password for non-OAuth authentication
      if (!isOAuth) {
        requestData.password = formData.password;
      }
      
      // Add custom server settings if selected
      if (provider === 'custom') {
        requestData.custom_server = formData.custom_server;
        requestData.custom_port = formData.custom_port;
      }
      
      // Submit the form
      const response = await fetch('/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        // Redirect to dashboard
        window.location.href = '/dashboard';
      } else if (data.status === 'oauth_redirect') {
        // Redirect to OAuth provider
        window.location.href = data.redirect_url;
      } else {
        // Handle error
        setError(data.message || 'An error occurred');
      }
    } catch (error) {
      setError('Failed to connect. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Provider configurations
  const providers = [
    { id: 'gmail', name: 'Gmail', logo: '/static/images/gmail.svg', supportsOAuth: true },
    { id: 'outlook', name: 'Outlook', logo: '/static/images/outlook.svg', supportsOAuth: true },
    { id: 'yahoo', name: 'Yahoo', logo: '/static/images/yahoo.svg', supportsOAuth: false },
    { id: 'icloud', name: 'iCloud', logo: '/static/images/icloud.svg', supportsOAuth: false },
    { id: 'aol', name: 'AOL', logo: '/static/images/aol.svg', supportsOAuth: false },
    { id: 'custom', name: 'Other', logo: '/static/images/email_generic.svg', supportsOAuth: false }
  ];

  return (
    <div className="mx-auto max-w-md px-4 sm:px-6 lg:px-8">
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-8 sm:p-10">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-extrabold text-gray-900">Connect Your Email</h2>
            <p className="mt-2 text-sm text-gray-600">
              CleanInbox helps you bulk unsubscribe from unwanted email newsletters.
            </p>
          </div>

          {/* Authentication Method Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <nav className="-mb-px flex" aria-label="Tabs">
              <button
                className={`w-1/2 py-4 px-1 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'password'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('password')}
              >
                Password
              </button>
              <button
                className={`w-1/2 py-4 px-1 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'oauth'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('oauth')}
              >
                OAuth 2.0
              </button>
            </nav>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-6 bg-red-50 border-l-4 border-red-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit}>
            {/* Email Provider Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Email Provider</label>
              <div className="grid grid-cols-3 gap-3">
                {providers.map((p) => (
                  <div
                    key={p.id}
                    className={`
                      border rounded-lg p-3 flex flex-col items-center cursor-pointer transition-all
                      ${provider === p.id ? 'bg-blue-50 border-blue-500' : 'border-gray-300 hover:border-gray-400'}
                      ${activeTab === 'oauth' && !p.supportsOAuth ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                    onClick={() => {
                      if (!(activeTab === 'oauth' && !p.supportsOAuth)) {
                        handleProviderSelect(p.id);
                      }
                    }}
                  >
                    <img src={p.logo} alt={p.name} className="h-8 w-8 mb-2" />
                    <span className="text-xs">{p.name}</span>
                    {activeTab === 'oauth' && !p.supportsOAuth && (
                      <span className="text-xs text-red-500 mt-1">No OAuth</span>
                    )}
                  </div>
                ))}
              </div>
              
              {activeTab === 'oauth' && provider !== 'gmail' && provider !== 'outlook' && (
                <p className="mt-2 text-xs text-gray-500">
                  Note: OAuth is currently only supported for Gmail and Outlook accounts.
                </p>
              )}
            </div>

            {/* Email Field */}
            <div className="mb-6">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                name="email"
                required
                value={formData.email}
                onChange={handleInputChange}
                className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
            </div>

            {/* Password Field - Only shown for password auth */}
            {activeTab === 'password' && (
              <div className="mb-6">
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  App Password
                </label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                />
                <p className="mt-1 text-xs text-gray-500">
                  {provider === 'gmail' ? (
                    <span>Use an <a href="https://support.google.com/mail/answer/185833" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">App Password</a> for Gmail accounts with 2FA.</span>
                  ) : provider === 'outlook' ? (
                    <span>Use an <a href="https://support.microsoft.com/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">App Password</a> for Outlook accounts with 2FA.</span>
                  ) : provider === 'yahoo' ? (
                    <span>Use an <a href="https://help.yahoo.com/kb/SLN15241.html" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">App Password</a> for Yahoo accounts.</span>
                  ) : provider === 'icloud' ? (
                    <span>Use an <a href="https://support.apple.com/en-us/HT204397" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">App-Specific Password</a> for iCloud accounts.</span>
                  ) : (
                    <span>Use your email password or an app-specific password if required.</span>
                  )}
                </p>
              </div>
            )}

            {/* Custom IMAP Settings - Only shown for custom provider */}
            {showCustomFields && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Custom IMAP Settings</h3>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="custom_server" className="block text-sm font-medium text-gray-700 mb-1">
                      IMAP Server
                    </label>
                    <input
                      type="text"
                      id="custom_server"
                      name="custom_server"
                      placeholder="imap.example.com"
                      required
                      value={formData.custom_server}
                      onChange={handleInputChange}
                      className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    />
                  </div>
                  <div>
                    <label htmlFor="custom_port" className="block text-sm font-medium text-gray-700 mb-1">
                      IMAP Port
                    </label>
                    <input
                      type="number"
                      id="custom_port"
                      name="custom_port"
                      placeholder="993"
                      required
                      value={formData.custom_port}
                      onChange={handleInputChange}
                      className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Number of Emails to Scan */}
            <div className="mb-6">
              <label htmlFor="num_emails" className="block text-sm font-medium text-gray-700 mb-1">
                Number of Emails to Scan
              </label>
              <select
                id="num_emails"
                name="num_emails"
                value={formData.num_emails}
                onChange={handleInputChange}
                className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
              >
                <option value={50}>50 emails</option>
                <option value={100}>100 emails</option>
                <option value={200}>200 emails</option>
                <option value={500}>500 emails</option>
              </select>
            </div>

            {/* Security Notice */}
            <div className="mb-6 p-4 bg-blue-50 rounded-lg">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">Security Information</h3>
                  <div className="mt-2 text-sm text-blue-700">
                    <p>
                      {activeTab === 'oauth' ? (
                        <>
                          OAuth 2.0 is the most secure way to connect. We never see or store your password.
                        </>
                      ) : (
                        <>
                          Your credentials are only stored in your session and are never saved to our database.
                          For enhanced security, please use app-specific passwords when available.
                        </>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <div>
              <button
                type="submit"
                disabled={loading || (activeTab === 'oauth' && !(provider === 'gmail' || provider === 'outlook'))}
                className={`w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                  loading || (activeTab === 'oauth' && !(provider === 'gmail' || provider === 'outlook'))
                    ? 'bg-blue-300 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                }`}
              >
                {loading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                  </>
                ) : activeTab === 'oauth' ? (
                  'Connect with OAuth'
                ) : (
                  'Scan My Inbox'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ModernLogin;