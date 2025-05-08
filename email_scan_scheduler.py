import threading
import schedule
import time
from datetime import datetime
import logging
from flask import session

# Setup logging for the scheduler
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
scheduler_logger = logging.getLogger('EmailScanScheduler')

class EmailScanScheduler:
    """
    Class to manage scheduled email scanning tasks.
    Allows users to set up automatic scans at regular intervals.
    """
    def __init__(self, app):
        self.app = app
        self.scheduled_jobs = {}  # Dictionary to store jobs by user email
        self.lock = threading.Lock()
        self.scheduler_thread = None
        self.running = False
        
    def start(self):
        """Start the scheduler thread"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            scheduler_logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler thread"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1.0)
            scheduler_logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Main loop for the scheduler thread"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def schedule_scan(self, email, password, provider, frequency='weekly', num_emails=100):
        """
        Schedule a recurring scan for the given user
        
        Args:
            email: User's email address
            password: User's email password
            provider: Email provider (gmail, outlook, etc.)
            frequency: Scan frequency (daily, weekly, monthly)
            num_emails: Number of emails to scan each time
        
        Returns:
            bool: True if scheduled successfully, False otherwise
        """
        with self.lock:
            # Cancel any existing job for this user
            self.cancel_scan(email)
            
            # Create the job function
            def job_function():
                with self.app.app_context():
                    from email_unsubscriber import EmailUnsubscriber
                    try:
                        unsubscriber = EmailUnsubscriber(email, password)
                        
                        # Set custom IMAP if needed
                        if provider == "custom":
                            with self.app.test_request_context():
                                custom_server = session.get('custom_server')
                                custom_port = session.get('custom_port')
                                if custom_server and custom_port:
                                    unsubscriber.set_custom_imap(custom_server, int(custom_port))
                        
                        # Perform the scan
                        unsubscribe_data = unsubscriber.find_unsubscribe_links(num_emails=num_emails)
                        
                        # Log the results
                        scheduler_logger.info(f"Scheduled scan for {email} completed: {len(unsubscribe_data)} subscriptions found")
                        
                        # Store the results (You may want to implement a notification system)
                        # This could be a database, file, or email notification
                        
                        return len(unsubscribe_data)
                    except Exception as e:
                        scheduler_logger.error(f"Scheduled scan for {email} failed: {str(e)}")
                        return 0
            
            # Schedule according to frequency
            if frequency == 'daily':
                job = schedule.every().day.at("02:00").do(job_function)  # Run at 2 AM
            elif frequency == 'weekly':
                job = schedule.every().sunday.at("03:00").do(job_function)  # Run at 3 AM on Sundays
            elif frequency == 'monthly':
                job = schedule.every(30).days.at("04:00").do(job_function)  # Run every 30 days at 4 AM
            else:
                return False
                
            # Store the job
            self.scheduled_jobs[email] = {
                'job': job,
                'frequency': frequency,
                'num_emails': num_emails,
                'created_at': datetime.now().isoformat()
            }
            
            scheduler_logger.info(f"Scheduled {frequency} scan for {email}")
            return True
    
    def cancel_scan(self, email):
        """Cancel a scheduled scan for the given user"""
        with self.lock:
            if email in self.scheduled_jobs:
                schedule.cancel_job(self.scheduled_jobs[email]['job'])
                del self.scheduled_jobs[email]
                scheduler_logger.info(f"Canceled scheduled scan for {email}")
                return True
            return False
    
    def get_scheduled_scans(self):
        """Get all scheduled scans"""
        with self.lock:
            return {email: {
                'frequency': job_info['frequency'], 
                'num_emails': job_info['num_emails'],
                'created_at': job_info['created_at']
            } for email, job_info in self.scheduled_jobs.items()}
    
    def get_user_schedule(self, email):
        """Get the schedule for a specific user"""
        with self.lock:
            if email in self.scheduled_jobs:
                return {
                    'frequency': self.scheduled_jobs[email]['frequency'],
                    'num_emails': self.scheduled_jobs[email]['num_emails'],
                    'created_at': self.scheduled_jobs[email]['created_at']
                }
            return None