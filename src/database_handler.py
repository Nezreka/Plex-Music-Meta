# src/database_handler.py
import sqlite3
import logging
from datetime import datetime

class DatabaseHandler:
    def __init__(self, db_path):
        self.db_path = db_path
        self.logger = logging.getLogger('PlexMusicEnricher')
        self._init_db()

    def _init_db(self):
        """Initialize the database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_artists (
                        artist_id TEXT PRIMARY KEY,
                        artist_name TEXT NOT NULL,
                        spotify_id TEXT,
                        processed_date TIMESTAMP,
                        success BOOLEAN,
                        error_message TEXT
                    )
                ''')
                conn.commit()
                self.logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {str(e)}")
            raise

    def is_artist_processed(self, artist_id):
        """Check if an artist has already been processed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT success FROM processed_artists WHERE artist_id = ?",
                    (artist_id,)
                )
                result = cursor.fetchone()
                return bool(result)
        except sqlite3.Error as e:
            self.logger.error(f"Database query error: {str(e)}")
            return False

    def mark_artist_processed(self, artist_id, artist_name, spotify_id=None, success=True, error_message=None):
        """Mark an artist as processed in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_artists 
                    (artist_id, artist_name, spotify_id, processed_date, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    artist_id,
                    artist_name,
                    spotify_id,
                    datetime.now().isoformat(),
                    success,
                    error_message
                ))
                conn.commit()
                self.logger.debug(f"Artist {artist_name} marked as processed")
        except sqlite3.Error as e:
            self.logger.error(f"Database update error: {str(e)}")
            raise

    def get_processing_stats(self):
        """Get statistics about processed artists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                    FROM processed_artists
                ''')
                return cursor.fetchone()
        except sqlite3.Error as e:
            self.logger.error(f"Database stats query error: {str(e)}")
            return (0, 0, 0)