from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import Counter
import logging
import json

# Setup logging
analytics_logger = logging.getLogger('SubscriptionAnalytics')

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

class SubscriptionAnalytics:
    """
    Class to analyze subscription data and provide insights
    """
    def __init__(self):
        self.pandas_available = PANDAS_AVAILABLE
        self.analytics_cache = {}  # Cache for analytics results
    
    def analyze_subscriptions(self, subscriptions, email=None):
        """
        Analyze subscription data to provide insights
        
        Args:
            subscriptions: List of subscription dictionaries from unsubscribe_links
            email: User's email for caching
            
        Returns:
            dict: Analysis results
        """
        # Check if pandas is available
        if not hasattr(self, 'pandas_available'):
            try:
                import pandas as pd
                self.pandas_available = True
            except ImportError:
                self.pandas_available = False
                analytics_logger.warning("pandas is not available, using simplified analytics")
        
        # If no subscriptions, return empty analysis
        if not subscriptions:
            return self._empty_analysis()
        
        # Create a cache key if email is provided
        cache_key = f"{email}_analytics" if email else None
        
        # Return cached results if available
        if cache_key and cache_key in self.analytics_cache:
            analytics_logger.info(f"Using cached analytics for {email}")
            return self.analytics_cache[cache_key]
        
        # If pandas is not available, use simple analysis
        if not self.pandas_available:
            return self._simple_analysis(subscriptions)
        
        # Full analysis with pandas
        try:
            import pandas as pd
            df = pd.DataFrame(subscriptions)
            
            # Ensure required columns exist
            required_columns = ['sender', 'category', 'last_received']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = 'Unknown'
            
            # Add last_received_date as datetime if possible
            df['last_received_date'] = pd.to_datetime(df['last_received'], errors='coerce')
            
            # Basic stats
            total_subscriptions = len(df)
            categories = df['category'].value_counts().to_dict()
            
            # Trend analysis - emails per month
            emails_by_time = self._analyze_time_trends(df)
            
            # Sender analysis - find most frequent senders
            top_senders = df['sender'].value_counts().head(10).to_dict()
            
            # Activity analysis - when was the last time you received from each category
            recent_by_category = self._analyze_recency_by_category(df)
            
            # Potential spam analysis - identify potential spam sources
            potential_spam = self._identify_potential_spam(df)
            
            # Email volume impact - estimate emails per month saved by unsubscribing
            volume_impact = self._estimate_volume_impact(df)
            
            # Put it all together
            analysis = {
                'total_subscriptions': total_subscriptions,
                'categories': categories,
                'time_trends': emails_by_time,
                'top_senders': top_senders,
                'recent_by_category': recent_by_category,
                'potential_spam': potential_spam,
                'volume_impact': volume_impact,
                'recommendations': self._generate_recommendations(df, categories, potential_spam),
                'generated_at': datetime.now().isoformat()
            }
            
            # Cache the results if email is provided
            if cache_key:
                self.analytics_cache[cache_key] = analysis
            
            return analysis
        except Exception as e:
            analytics_logger.error(f"Error during analysis: {str(e)}")
            return self._simple_analysis(subscriptions)

    def _simple_analysis(self, subscriptions):
        """Simple analysis without pandas dependency"""
        # Basic counting and categorization
        total = len(subscriptions)
        
        # Count categories
        categories = {}
        for sub in subscriptions:
            cat = sub.get('category', 'Unknown')
            if cat in categories:
                categories[cat] += 1
            else:
                categories[cat] = 1
        
        # Simple time saved estimate (30 seconds per email per month)
        estimated_monthly_reduction = total * 5 * 30 / 60  # 5 emails per month, 30 seconds each, convert to minutes
        
        # Return simplified analytics
        return {
            'total_subscriptions': total,
            'categories': categories,
            'time_trends': {'months': [], 'counts': []},  # Empty for simple analysis
            'top_senders': {},  # Empty for simple analysis
            'recent_by_category': {},  # Empty for simple analysis
            'potential_spam': [],  # Empty for simple analysis
            'volume_impact': {'estimated_monthly_reduction': round(estimated_monthly_reduction)},
            'recommendations': [
                {
                    'type': 'general',
                    'message': f"Unsubscribing from all {total} newsletters could save you approximately {round(estimated_monthly_reduction)} minutes per month."
                }
            ],
            'generated_at': datetime.now().isoformat()
        }
    
    def _empty_analysis(self):
        """Return empty analysis structure"""
        return {
            'total_subscriptions': 0,
            'categories': {},
            'time_trends': {},
            'top_senders': {},
            'recent_by_category': {},
            'potential_spam': [],
            'volume_impact': {'estimated_monthly_reduction': 0},
            'recommendations': [],
            'generated_at': datetime.now().isoformat()
        }
    
    def _analyze_time_trends(self, df):
        """Analyze email receiving trends over time"""
        if 'last_received_date' not in df.columns or df['last_received_date'].isna().all():
            return {'months': [], 'counts': []}
        
        # Filter out rows with invalid dates
        date_df = df.dropna(subset=['last_received_date'])
        if len(date_df) == 0:
            return {'months': [], 'counts': []}
        
        # Group by month and count
        date_df['month'] = date_df['last_received_date'].dt.strftime('%Y-%m')
        monthly_counts = date_df['month'].value_counts().sort_index()
        
        return {
            'months': monthly_counts.index.tolist(),
            'counts': monthly_counts.values.tolist()
        }
    
    def _analyze_recency_by_category(self, df):
        """Find most recent email for each category"""
        if 'last_received_date' not in df.columns or df['last_received_date'].isna().all():
            return {}
        
        # Filter out rows with invalid dates
        date_df = df.dropna(subset=['last_received_date'])
        if len(date_df) == 0:
            return {}
        
        # Group by category and find max date
        recency = {}
        for category in date_df['category'].unique():
            category_df = date_df[date_df['category'] == category]
            if not category_df.empty:
                most_recent = category_df['last_received_date'].max()
                days_ago = (datetime.now() - most_recent).days
                recency[category] = {
                    'most_recent_date': most_recent.strftime('%Y-%m-%d'),
                    'days_ago': days_ago
                }
        
        return recency
    
    def _identify_potential_spam(self, df):
        """Identify potential spam sources based on patterns"""
        potential_spam = []
        
        # Check for extremely frequent senders
        sender_counts = df['sender'].value_counts()
        very_frequent = sender_counts[sender_counts > 10].index.tolist()
        
        # Look for suspicious keywords in sender names
        spam_keywords = ['offer', 'discount', 'deal', 'limited', 'exclusive', 'free', 'win']
        keyword_matches = []
        
        for sender in df['sender'].unique():
            sender_lower = str(sender).lower()
            if any(keyword in sender_lower for keyword in spam_keywords):
                keyword_matches.append(sender)
        
        # Combine and deduplicate
        all_suspicious = list(set(very_frequent + keyword_matches))
        
        # Format the output with reasons
        for sender in all_suspicious:
            reasons = []
            if sender in very_frequent:
                reasons.append("Very frequent sender")
            if sender in keyword_matches:
                reasons.append("Contains suspicious keywords")
            
            potential_spam.append({
                'sender': sender,
                'reasons': reasons
            })
        
        return potential_spam
    
    def _estimate_volume_impact(self, df):
        """Estimate the impact of unsubscribing on email volume"""
        # Simple model: assume each sender sends emails at their historical frequency
        
        # If we can't determine dates, make a rough estimate
        if 'last_received_date' not in df.columns or df['last_received_date'].isna().all():
            return {
                'estimated_monthly_reduction': len(df) * 2  # Rough estimate: 2 emails per month per subscription
            }
        
        # Filter out rows with invalid dates
        date_df = df.dropna(subset=['last_received_date'])
        if len(date_df) == 0:
            return {'estimated_monthly_reduction': len(df) * 2}
        
        # Get date range of the data
        min_date = date_df['last_received_date'].min()
        max_date = date_df['last_received_date'].max()
        date_range_days = max(1, (max_date - min_date).days)
        
        # Count emails per sender
        sender_counts = date_df['sender'].value_counts()
        
        # Calculate average daily frequency per sender
        avg_daily_freq = {}
        for sender, count in sender_counts.items():
            avg_daily_freq[sender] = count / date_range_days
        
        # Calculate estimated monthly volume
        monthly_volume = sum(avg_daily_freq.values()) * 30
        
        return {
            'estimated_monthly_reduction': round(monthly_volume),
            'top_contributors': {k: round(v * 30, 1) for k, v in sorted(avg_daily_freq.items(), key=lambda x: x[1], reverse=True)[:5]}
        }
    
    def _generate_recommendations(self, df, categories, potential_spam):
        """Generate personalized recommendations based on analysis"""
        recommendations = []
        
        # Recommendation based on categories
        if categories:
            largest_category = max(categories, key=categories.get)
            if categories[largest_category] > 5:
                recommendations.append({
                    'type': 'category_focus',
                    'message': f"Focus on unsubscribing from '{largest_category}' emails first as they make up the largest category"
                })
        
        # Recommendation based on potential spam
        if potential_spam and len(potential_spam) > 2:
            recommendations.append({
                'type': 'spam_cleanup',
                'message': f"Consider removing {len(potential_spam)} potential promotional/spam emails to reduce inbox clutter"
            })
        
        # Recommendation based on recency
        if 'last_received_date' in df.columns and not df['last_received_date'].isna().all():
            old_subscriptions = df[df['last_received_date'] < (datetime.now() - timedelta(days=180))]
            if len(old_subscriptions) > 3:
                recommendations.append({
                    'type': 'old_subscriptions',
                    'message': f"You have {len(old_subscriptions)} subscriptions that haven't sent emails in over 6 months"
                })
        
        # Add a generic recommendation if no specific ones were generated
        if not recommendations:
            recommendations.append({
                'type': 'general',
                'message': "Regular inbox cleanup can save you time and reduce digital clutter"
            })
        
        return recommendations
    
    def clear_cache(self, email=None):
        """Clear analytics cache for a specific user or all users"""
        if email:
            cache_key = f"{email}_analytics"
            if cache_key in self.analytics_cache:
                del self.analytics_cache[cache_key]
                return True
        else:
            self.analytics_cache.clear()
            return True
        return False