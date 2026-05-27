import os
import sqlite3
import logging
from datetime import datetime

class HistoryDB:
    def __init__(self, db_path=None):
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.project_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        if not db_path:
            self.db_path = os.path.join(self.data_dir, "history.db")
        else:
            self.db_path = db_path
            
        self.init_db()
        
    def init_db(self):
        """Initializes the database and creates the history table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS download_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    format_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
            logging.info("Database initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")

    def add_record(self, title, url, format_name, file_path, file_size="Unknown"):
        """Adds a completed download record to the history."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO download_history (title, url, format_name, file_path, file_size)
                VALUES (?, ?, ?, ?, ?)
            """, (title, url, format_name, file_path, file_size))
            conn.commit()
            conn.close()
            logging.info(f"Added history record for: {title}")
            return True
        except Exception as e:
            logging.error(f"Failed to add history record: {e}")
            return False

    def get_all_records(self):
        """Fetches all records from history, ordered by timestamp descending."""
        try:
            conn = sqlite3.connect(self.db_path)
            # Row factory to get dictionaries
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM download_history ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            records = [dict(row) for row in rows]
            conn.close()
            return records
        except Exception as e:
            logging.error(f"Failed to fetch history records: {e}")
            return []

    def delete_record(self, record_id):
        """Deletes a specific record by id."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM download_history WHERE id = ?", (record_id,))
            conn.commit()
            conn.close()
            logging.info(f"Deleted history record with ID: {record_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to delete history record: {e}")
            return False

    def clear_all(self):
        """Clears all records from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM download_history")
            conn.commit()
            conn.close()
            logging.info("All history records cleared.")
            return True
        except Exception as e:
            logging.error(f"Failed to clear history: {e}")
            return False
