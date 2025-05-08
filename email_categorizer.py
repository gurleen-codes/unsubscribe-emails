import logging
import re
import pickle
import os
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from collections import defaultdict

# Setup logging
categorizer_logger = logging.getLogger('EmailCategorizer')

try:
    import pandas as pd
    import numpy as np
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.naive_bayes import MultinomialNB
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

class EmailCategorizer:
    """
    Enhanced email categorizer using machine learning to identify subscription types.
    """
    def __init__(self, model_path=None):
        """
        Initialize the email categorizer
        
        Args:
            model_path: Path to a pre-trained model file (optional)
        """
        self.ml_available = ML_AVAILABLE
        self.categories = [
            'Shopping', 'Social', 'Finance', 'Travel', 
            'News', 'Updates', 'Forums', 'Entertainment',
            'Promotions', 'Education', 'Health', 'Technology'
        ]
        
        # Define keywords for each category
        self.category_keywords = {
            'Shopping': [
                'shop', 'store', 'discount', 'sale', 'order', 'purchase', 'buy', 
                'deal', 'promo', 'coupon', 'amazon', 'ebay', 'walmart', 'offer', 
                'product', 'shipping', 'delivery'
            ],
            'Social': [
                'friend', 'connect', 'network', 'social', 'follow', 'like', 'share',
                'facebook', 'twitter', 'instagram', 'linkedin', 'invite', 'join',
                'community', 'group', 'profile', 'post'
            ],
            'Finance': [
                'bank', 'finance', 'credit', 'payment', 'account', 'statement', 'invest',
                'loan', 'mortgage', 'bill', 'transaction', 'transfer', 'balance', 'tax',
                'insurance', 'money', 'fund', 'deposit'
            ],
            'Travel': [
                'travel', 'flight', 'trip', 'vacation', 'hotel', 'booking', 'airline',
                'reservation', 'itinerary', 'destination', 'accommodation', 'journey',
                'tour', 'holiday', 'cruise', 'passport', 'ticket'
            ],
            'News': [
                'news', 'update', 'latest', 'breaking', 'daily', 'weekly', 'monthly',
                'alert', 'headline', 'report', 'bulletin', 'newsletter', 'press', 
                'media', 'article', 'blog'
            ],
            'Updates': [
                'update', 'alert', 'notification', 'confirm', 'verify', 'security',
                'status', 'reminder', 'change', 'info', 'important', 'action', 'required',
                'announcement'
            ],
            'Forums': [
                'forum', 'community', 'discussion', 'member', 'group', 'topic', 'thread',
                'reply', 'post', 'message', 'board', 'comment', 'feedback'
            ],
            'Entertainment': [
                'movie', 'music', 'game', 'video', 'stream', 'watch', 'play', 'show',
                'series', 'episode', 'entertainment', 'concert', 'event', 'ticket',
                'performance', 'theater', 'festival'
            ],
            'Promotions': [
                'promotion', 'discount', 'save', 'offer', 'deal', 'coupon', 'special',
                'exclusive', 'limited', 'free', 'gift', 'reward', 'bonus', 'points',
                'earn', 'redeem'
            ],
            'Education': [
                'course', 'class', 'learn', 'study', 'education', 'training', 'workshop',
                'webinar', 'certificate', 'degree', 'school', 'college', 'university',
                'student', 'teacher', 'professor', 'academic'
            ],
            'Health': [
                'health', 'medical', 'doctor', 'patient', 'care', 'fitness', 'wellness',
                'exercise', 'diet', 'nutrition', 'pharmacy', 'medication', 'prescription',
                'appointment', 'clinic', 'hospital'
            ],
            'Technology': [
                'tech', 'software', 'hardware', 'update', 'app', 'application', 'device',
                'computer', 'mobile', 'phone', 'tablet', 'gadget', 'digital', 'online',
                'web', 'cloud', 'data', 'download', 'upgrade'
            ]
        }
        
        # Initialize the ML model
        self.model = None
        self.load_model(model_path)
    
    def load_model(self, model_path=None):
        """
        Load a pre-trained ML model if available, otherwise create a new one
        
        Args:
            model_path: Path to the model file
        """
        if model_path and os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                categorizer_logger.info(f"Loaded model from {model_path}")
                return True
            except Exception as e:
                categorizer_logger.error(f"Error loading model: {str(e)}")
        
        # If no model or loading failed, create a new one
        self.model = Pipeline([
            ('vectorizer', CountVectorizer(ngram_range=(1, 2))),
            ('classifier', MultinomialNB())
        ])
        
        # Train with our keyword sets as a starting point
        self._train_with_keywords()
        
        return False
    
    def _train_with_keywords(self):
        """Initialize the model with category keywords as training data"""
        # Create synthetic training data using keywords
        X = []
        y = []
        
        for category, keywords in self.category_keywords.items():
            # Create samples by combining keywords
            for keyword in keywords:
                # Simple sample with the keyword
                X.append(keyword)
                y.append(category)
                
                # Samples with keyword in context
                X.append(f"Please check out our {keyword} newsletter")
                y.append(category)
                
                X.append(f"Your {keyword} account has been updated")
                y.append(category)
                
                X.append(f"Latest {keyword} news and updates")
                y.append(category)
        
        # Train the model
        self.model.fit(X, y)
        categorizer_logger.info("Trained model with keyword data")
    
    def save_model(self, model_path):
        """
        Save the current model to a file
        
        Args:
            model_path: Path to save the model to
            
        Returns:
            bool: True if successful
        """
        if not self.model:
            categorizer_logger.error("No model to save")
            return False
        
        try:
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            categorizer_logger.info(f"Saved model to {model_path}")
            return True
        except Exception as e:
            categorizer_logger.error(f"Error saving model: {str(e)}")
            return False
    
    def categorize(self, email_data):
        """
        Categorize an email based on its content
        
        Args:
            email_data: Dictionary with email data (subject, sender, content)
            
        Returns:
            str: The most likely category
            dict: Confidence scores for each category
        """
        # Check if we have scikit-learn available
        if not hasattr(self, 'ml_available'):
            try:
                import sklearn
                self.ml_available = True
            except ImportError:
                self.ml_available = False
                categorizer_logger.warning("scikit-learn is not available, using keyword-based categorization only")
        
        # Extract features from email
        text = self._extract_features(email_data)
        
        # If ML is available and we have a trained model, use it
        if self.ml_available and self.model:
            try:
                # Get prediction and probabilities
                category = self.model.predict([text])[0]
                probabilities = self.model.predict_proba([text])[0]
                
                # Map probabilities to categories
                confidence = {}
                for i, prob in enumerate(probabilities):
                    cat = self.model.classes_[i]
                    confidence[cat] = float(prob)
                
                return category, confidence
            except Exception as e:
                categorizer_logger.error(f"Error predicting category: {str(e)}")
        
        # Fallback to keyword matching
        return self._keyword_categorize(text)
    
    def _extract_features(self, email_data):
        """
        Extract features from email data for categorization
        
        Args:
            email_data: Dictionary with email data
            
        Returns:
            str: Combined text for analysis
        """
        features = []
        
        # Extract subject
        if 'subject' in email_data and email_data['subject']:
            features.append(str(email_data['subject']))
        
        # Extract sender
        if 'sender' in email_data and email_data['sender']:
            features.append(str(email_data['sender']))
        
        # Extract content if available
        if 'content' in email_data and email_data['content']:
            # Get a sample of the content
            content = str(email_data['content'])
            if len(content) > 1000:
                content = content[:1000]
            features.append(content)
        
        # Combine features
        return ' '.join(features)
    
    def _keyword_categorize(self, text):
        """
        Categorize using keyword matching as fallback
        
        Args:
            text: Text to categorize
            
        Returns:
            str: Best matching category
            dict: Scores for each category
        """
        text = text.lower()
        scores = defaultdict(int)
        
        # Score each category based on keyword matches
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                # Count occurrences of the keyword
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
                scores[category] += count
        
        # If no matches, default to 'Promotions'
        if not scores or max(scores.values()) == 0:
            scores['Promotions'] = 1
        
        # Normalize scores
        total = sum(scores.values())
        confidence = {k: v / total for k, v in scores.items()}
        
        # Get the highest scoring category
        best_category = max(scores.items(), key=lambda x: x[1])[0]
        
        return best_category, confidence
    
    def bulk_categorize(self, emails):
        """
        Categorize a list of emails
        
        Args:
            emails: List of email data dictionaries
            
        Returns:
            list: List of (email, category, confidence) tuples
        """
        results = []
        
        for email in emails:
            category, confidence = self.categorize(email)
            results.append((email, category, confidence))
        
        return results
    
    def train(self, emails, categories):
        """
        Train the model with new examples
        
        Args:
            emails: List of email data dictionaries
            categories: List of corresponding categories
            
        Returns:
            bool: True if training was successful
        """
        if len(emails) != len(categories):
            categorizer_logger.error("Number of emails and categories must match")
            return False
        
        # Extract features
        X = [self._extract_features(email) for email in emails]
        y = categories
        
        try:
            # Train the model with new data
            self.model.fit(X, y)
            categorizer_logger.info(f"Trained model with {len(emails)} new examples")
            return True
        except Exception as e:
            categorizer_logger.error(f"Error training model: {str(e)}")
            return False
    
    def update_with_feedback(self, email_data, correct_category):
        """
        Update the model with user feedback
        
        Args:
            email_data: Email data that was mis-categorized
            correct_category: The correct category as indicated by user
            
        Returns:
            bool: True if update was successful
        """
        # Extract features
        text = self._extract_features(email_data)
        
        try:
            # Update the model with this single example
            self.model.fit([text], [correct_category])
            categorizer_logger.info(f"Updated model with feedback for category {correct_category}")
            return True
        except Exception as e:
            categorizer_logger.error(f"Error updating model with feedback: {str(e)}")
            return False