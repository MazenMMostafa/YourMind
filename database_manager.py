import logging
import time
import random
from datetime import datetime
import json
import pyrebase
from firebase_config import FIREBASE_CONFIG  # Ensure you import your Firebase config

# Initialize Firebase
firebase = pyrebase.initialize_app(FIREBASE_CONFIG)

class DatabaseManager:
    def __init__(self, db=None):
        self.db = db if db else firebase.database()  # Use the initialized firebase
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds

    def safe_db_operation(self, operation):
        for attempt in range(self.retry_attempts):
            try:
                return operation()
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    logging.error(f"Database operation failed after {self.retry_attempts} attempts: {str(e)}")
                    raise
                time.sleep(self.retry_delay)

    def save_assessment_data(self, user_id, assessment_data):
        try:
            assessment_key = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.db.child("assessments").child(user_id).child(assessment_key).set({
                "score": assessment_data.get('score'),
                "diagnosis": assessment_data.get('diagnosis'),
                "date": datetime.now().isoformat(),
                "answers": assessment_data.get('answers', [])
            })
            return True
        except Exception as e:
            logging.error(f"Error saving assessment data: {str(e)}")
            return False

    # Add other methods from DatabaseManager here...

class DatabaseConnectionManager:
    def __init__(self):
        self.connection_pool = {}
        self.max_connections = 10

    def get_connection(self):
        try:
            if len(self.connection_pool) < self.max_connections:
                connection = pyrebase.initialize_app(FIREBASE_CONFIG)  # Use the correct config
                self.connection_pool[id(connection)] = connection
                return connection
            return random.choice(list(self.connection_pool.values()))
        except Exception as e:
            logging.error(f"Error getting database connection: {str(e)}")
            raise

    def close_connections(self):
        for connection in self.connection_pool.values():
            try:
                connection.close()
            except:
                pass
        self.connection_pool.clear() 