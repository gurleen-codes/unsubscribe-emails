import React, { useState, useEffect } from 'react';
import { LineChart, BarChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const SubscriptionDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({
    subscriptions: [],
    stats: { categories: {} },
    analytics: { time_trends: {}, top_senders: {} },
    totalUnsubscribed: 0,
    timeSaved: 0
  });
  const [selectedTab, setSelectedTab] = useState('overview');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [bulkSelection, setBulkSelection] = useState([]);
  const [bulkUnsubscribing, setBulkUnsubscribing] = useState(false);
  const [scheduledScan, setScheduledScan] = useState(null);
  const [scheduleScanOpen, setScheduleScanOpen] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    frequency: 'weekly',
    num_emails: 100
  });

  // CHART COLORS
  const COLORS = [
    '#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088fe', 
    '#00C49F', '#FFBB28', '#FF8042', '#a4de6c', '#d0ed57', 
    '#83a6ed', '#8dd1e1', '#6b486b', '#a05d56', '#d0743c'
  ];

  // Load subscription data on component mount
  useEffect(() => {
    fetchSubscriptionData();
    fetchScheduledScans();
  }, []);

  const fetchSubscriptionData = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/subscription_data');
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      const jsonData = await response.json();
      
      if (jsonData.status === 'success') {
        setData(jsonData);
      } else {
        setError(jsonData.message || 'Failed to load subscription data');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchScheduledScans = async () => {
    try {
      const response = await fetch('/api/get_scheduled_scans');
      if (response.ok) {
        const jsonData = await response.json();
        if (jsonData.status === 'success' && jsonData.schedule) {
          setScheduledScan(jsonData.schedule);
        }
      }
    } catch (error) {
      console.error("Error fetching scheduled scans:", error);
    }
  };

  const handleBulkSelection = (emailId) => {
    const newSelection = [...bulkSelection];
    
    if (newSelection.includes(emailId)) {
      // Remove if already selected
      const index = newSelection.indexOf(emailId);
      newSelection.splice(index, 1);
    } else {
      // Add if not selected
      newSelection.push(emailId);
    }
    
    setBulkSelection(newSelection);
  };

  const handleSelectAll = () => {
    if (bulkSelection.length === filteredSubscriptions.length) {
      // Deselect all if all are selected
      setBulkSelection([]);
    } else {
      // Select all if some or none are selected
      setBulkSelection(filteredSubscriptions.map(sub => sub.email_id));
    }
  };

  const handleCategoryFilter = (category) => {
    setSelectedCategory(category);
  };

  const handleRefresh = () => {
    fetchSubscriptionData();
  };

  const handleExportCSV = () => {
    window.location.href = '/api/export_csv';
  };

  const handleUnsubscribe = async (link, sender) => {
    try {
      const response = await fetch('/unsubscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ link, sender }),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        // Update local state to reflect the unsubscription
        fetchSubscriptionData();
        return true;
      } else {
        alert(`Failed to unsubscribe: ${result.message}`);
        return false;
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
      return false;
    }
  };

  const handleBulkUnsubscribe = async () => {
    if (bulkSelection.length === 0) return;
    
    setBulkUnsubscribing(true);
    
    // Create array of links for bulk unsubscribe
    const links = bulkSelection.map(id => {
      const subscription = data.subscriptions.find(sub => sub.email_id === id);
      return {
        link: subscription.unsubscribe_link,
        sender: subscription.sender,
        email_id: id
      };
    });
    
    try {
      const response = await fetch('/api/bulk_unsubscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ links }),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        // Show success/failure summary
        const { succeeded, failed } = result.summary;
        alert(`Unsubscribe summary:\n- Successfully unsubscribed: ${succeeded}\n- Failed: ${failed}`);
        
        // Clear selection and refresh data
        setBulkSelection([]);
        fetchSubscriptionData();
      } else {
        alert(`Bulk unsubscribe failed: ${result.message}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setBulkUnsubscribing(false);
    }
  };

  const handleScheduleScan = async () => {
    try {
      const response = await fetch('/api/schedule_scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scheduleForm),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        setScheduledScan(result.schedule);
        setScheduleScanOpen(false);
        alert(`Successfully scheduled ${scheduleForm.frequency} scan`);
      } else {
        alert(`Failed to schedule scan: ${result.message}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  const handleCancelScheduledScan = async () => {
    try {
      const response = await fetch('/api/cancel_scheduled_scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        setScheduledScan(null);
        alert('Scheduled scan canceled');
      } else {
        alert(`Failed to cancel scan: ${result.message}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  // Filter subscriptions based on selected category
  const filteredSubscriptions = data.subscriptions.filter(sub => 
    selectedCategory === 'all' || sub.category === selectedCategory
  );

  // Prepare data for category chart
  const categoryData = Object.entries(data.stats.categories || {}).map(([name, count]) => ({
    name,
    value: count
  }));

  // Prepare time trends data
  const trendData = data.analytics?.time_trends?.months?.map((month, index) => ({
    month,
    count: data.analytics.time_trends.counts[index]
  })) || [];

  // If loading, show spinner
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // If error, show error message
  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
        <p className="font-bold">Error loading subscription data</p>
        <p>{error}</p>
        <button 
          onClick={fetchSubscriptionData}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      {/* DASHBOARD TABS */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              className={`${
                selectedTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              onClick={() => setSelectedTab('overview')}
            >
              Overview
            </button>
            <button
              className={`${
                selectedTab === 'subscriptions'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ml-8`}
              onClick={() => setSelectedTab('subscriptions')}
            >
              Manage Subscriptions
            </button>
            <button
              className={`${
                selectedTab === 'analytics'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ml-8`}
              onClick={() => setSelectedTab('analytics')}
            >
              Analytics
            </button>
            <button
              className={`${
                selectedTab === 'settings'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ml-8`}
              onClick={() => setSelectedTab('settings')}
            >
              Settings
            </button>
          </nav>
        </div>
      </div>

      {/* OVERVIEW TAB */}
      {selectedTab === 'overview' && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Total Subscriptions</h3>
              <p className="text-3xl font-bold text-blue-600">{data.stats?.total_found || 0}</p>
              <p className="text-sm text-gray-500">newsletters found in your inbox</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Unsubscribed</h3>
              <p className="text-3xl font-bold text-green-600">{data.totalUnsubscribed || 0}</p>
              <p className="text-sm text-gray-500">emails you've cleaned up</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Time Saved</h3>
              <p className="text-3xl font-bold text-purple-600">{data.timeSaved || 0} min</p>
              <p className="text-sm text-gray-500">per month</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Subscription Categories</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    >
                      {categoryData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [`${value} subscriptions`, 'Count']} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Subscription Trends</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={trendData}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="count" stroke="#8884d8" activeDot={{ r: 8 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {data.analytics?.recommendations && (
            <div className="bg-white p-6 rounded-lg shadow-md mb-8">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Recommendations</h3>
              <ul className="space-y-3">
                {data.analytics.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start">
                    <div className="flex-shrink-0 h-5 w-5 text-blue-500">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2h-1V9a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <p className="ml-2 text-gray-700">{rec.message}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scheduledScan && (
            <div className="bg-blue-50 p-4 rounded-lg mb-8">
              <div className="flex items-center">
                <div className="flex-shrink-0 h-5 w-5 text-blue-500">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                  </svg>
                </div>
                <p className="ml-2 text-blue-700">
                  You have a {scheduledScan.frequency} scan scheduled (scanning {scheduledScan.num_emails} emails)
                </p>
                <button
                  onClick={handleCancelScheduledScan}
                  className="ml-auto text-blue-700 hover:text-blue-800 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {data.analytics?.potential_spam && data.analytics.potential_spam.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Potential Spam/Promotional Emails</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sender</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reasons</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {data.analytics.potential_spam.slice(0, 5).map((item, index) => {
                      // Find the subscription for this sender
                      const subscription = data.subscriptions.find(sub => sub.sender === item.sender);
                      
                      return (
                        <tr key={index}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.reasons.join(", ")}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {subscription && subscription.unsubscribe_link ? (
                              <button
                                onClick={() => handleUnsubscribe(subscription.unsubscribe_link, subscription.sender)}
                                className="text-red-600 hover:text-red-900"
                              >
                                Unsubscribe
                              </button>
                            ) : (
                              <span className="text-gray-400">No link found</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBSCRIPTIONS TAB */}
      {selectedTab === 'subscriptions' && (
        <div>
          <div className="mb-6 flex flex-wrap justify-between items-center">
            <div className="flex flex-wrap items-center space-x-2 mb-4 md:mb-0">
              <button
                onClick={() => handleCategoryFilter('all')}
                className={`px-3 py-1 rounded text-sm ${
                  selectedCategory === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
                }`}
              >
                All
              </button>
              {Object.keys(data.stats.categories || {}).map(category => (
                <button
                  key={category}
                  onClick={() => handleCategoryFilter(category)}
                  className={`px-3 py-1 rounded text-sm ${
                    selectedCategory === category ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleRefresh}
                className="flex items-center px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                </svg>
                Refresh
              </button>
              {bulkSelection.length > 0 && (
                <button
                  onClick={handleBulkUnsubscribe}
                  disabled={bulkUnsubscribing}
                  className={`flex items-center px-4 py-2 bg-red-600 text-white rounded ${
                    bulkUnsubscribing ? 'opacity-50 cursor-not-allowed' : 'hover:bg-red-700'
                  }`}
                >
                  {bulkUnsubscribing ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing...
                    </>
                  ) : (
                    <>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      Unsubscribe ({bulkSelection.length})
                    </>
                  )}
                </button>
              )}
              <button
                onClick={handleExportCSV}
                className="flex items-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
                Export CSV
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      <input
                        type="checkbox"
                        checked={bulkSelection.length === filteredSubscriptions.length && filteredSubscriptions.length > 0}
                        onChange={handleSelectAll}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sender</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Received</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredSubscriptions.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="px-6 py-4 text-center text-gray-500">
                        No subscriptions found. Try selecting a different category or refreshing the data.
                      </td>
                    </tr>
                  ) : (
                    filteredSubscriptions.map((subscription, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <input
                            type="checkbox"
                            checked={bulkSelection.includes(subscription.email_id)}
                            onChange={() => handleBulkSelection(subscription.email_id)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{subscription.sender}</div>
                          {subscription.email && (
                            <div className="text-sm text-gray-500">{subscription.email}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                            {subscription.category}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {subscription.last_received}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {subscription.unsubscribe_link ? (
                            <button
                              onClick={() => handleUnsubscribe(subscription.unsubscribe_link, subscription.sender)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Unsubscribe
                            </button>
                          ) : (
                            <span className="text-gray-400">No link found</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ANALYTICS TAB */}
      {selectedTab === 'analytics' && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Estimated Email Volume Impact */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Email Volume Impact</h3>
              <div className="mb-4">
                <p className="text-gray-700">
                  By unsubscribing from all newsletters, you could reduce your monthly email volume by approximately:
                </p>
                <p className="text-3xl font-bold text-blue-600 mt-2">
                  {data.analytics?.volume_impact?.estimated_monthly_reduction || 0} emails/month
                </p>
              </div>
              
              {data.analytics?.volume_impact?.top_contributors && (
                <div>
                  <h4 className="text-md font-medium text-gray-700 mb-2">Top Email Contributors</h4>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={Object.entries(data.analytics.volume_impact.top_contributors).map(([sender, count]) => ({
                          name: sender.length > 20 ? sender.substring(0, 20) + "..." : sender,
                          count
                        }))}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis dataKey="name" type="category" width={150} />
                        <Tooltip formatter={(value) => [`${value} emails/month`, 'Volume']} />
                        <Bar dataKey="count" fill="#8884d8" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
            
            {/* Category Distribution */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Category Distribution</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    >
                      {categoryData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [`${value} subscriptions`, 'Count']} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Subscription Trends */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Subscription Trends</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={trendData}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="count" stroke="#8884d8" activeDot={{ r: 8 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            {/* Recent Activity by Category */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Recent Activity by Category</h3>
              {data.analytics?.recent_by_category ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Email</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Ago</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {Object.entries(data.analytics.recent_by_category).map(([category, info], index) => (
                        <tr key={index}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{category}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{info.most_recent_date}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{info.days_ago}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500">No recent activity data available.</p>
              )}
            </div>
          </div>
          
          {/* Recommendations */}
          {data.analytics?.recommendations && (
            <div className="bg-white p-6 rounded-lg shadow-md mb-8">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Personalized Recommendations</h3>
              <ul className="space-y-3">
                {data.analytics.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start p-3 bg-blue-50 rounded-lg">
                    <div className="flex-shrink-0 h-5 w-5 text-blue-500">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2h-1V9a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <p className="ml-2 text-blue-700">{rec.message}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* SETTINGS TAB */}
      {selectedTab === 'settings' && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Scheduled Scanning */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Automated Scanning</h3>
              
              {scheduledScan ? (
                <div>
                  <div className="mb-4 p-4 bg-blue-50 rounded-lg">
                    <p className="text-blue-700">
                      You have a <strong>{scheduledScan.frequency}</strong> scan scheduled
                    </p>
                    <p className="text-sm text-blue-600 mt-1">
                      Scanning {scheduledScan.num_emails} emails each time
                    </p>
                  </div>
                  
                  <button
                    onClick={handleCancelScheduledScan}
                    className="mt-2 px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200"
                  >
                    Cancel Scheduled Scan
                  </button>
                </div>
              ) : (
                <div>
                  {scheduleScanOpen ? (
                    <div>
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">Frequency</label>
                        <select
                          value={scheduleForm.frequency}
                          onChange={(e) => setScheduleForm({...scheduleForm, frequency: e.target.value})}
                          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                        >
                          <option value="daily">Daily</option>
                          <option value="weekly">Weekly</option>
                          <option value="monthly">Monthly</option>
                        </select>
                      </div>
                      
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">Emails to Scan</label>
                        <select
                          value={scheduleForm.num_emails}
                          onChange={(e) => setScheduleForm({...scheduleForm, num_emails: parseInt(e.target.value)})}
                          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                        >
                          <option value={50}>50 emails</option>
                          <option value={100}>100 emails</option>
                          <option value={200}>200 emails</option>
                          <option value={500}>500 emails</option>
                        </select>
                      </div>
                      
                      <div className="flex space-x-2 mt-4">
                        <button
                          onClick={handleScheduleScan}
                          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                          Schedule
                        </button>
                        <button
                          onClick={() => setScheduleScanOpen(false)}
                          className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-600 mb-4">
                        Set up automatic scanning of your inbox to discover and manage new subscriptions.
                      </p>
                      <button
                        onClick={() => setScheduleScanOpen(true)}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Schedule Automated Scan
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Data Management */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Data Management</h3>
              <div className="space-y-4">
                <div>
                  <button
                    onClick={handleExportCSV}
                    className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center justify-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                    Export Subscriptions as CSV
                  </button>
                </div>
                
                <div>
                  <button
                    onClick={handleRefresh}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center justify-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                    </svg>
                    Refresh Scan Data
                  </button>
                </div>
                
                <div>
                  <button
                    onClick={() => {
                      if (window.confirm("Are you sure you want to log out? This will clear all your session data.")) {
                        fetch('/api/logout', { method: 'POST' })
                          .then(() => window.location.href = '/');
                      }
                    }}
                    className="w-full px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 flex items-center justify-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" clipRule="evenodd" />
                    </svg>
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          {/* App Info */}
          <div className="mt-6 bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">About CleanInbox</h3>
            <div className="text-gray-600">
              <p className="mb-2">Version: 2.0.0</p>
              <p className="mb-2">Last Scan: {data.cached ? `${data.cache_age} minutes ago` : 'Just now'}</p>
              <p>
                CleanInbox helps you take control of your inbox by finding and managing your subscriptions.
                For support or feedback, please visit our GitHub repository.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SubscriptionDashboard;