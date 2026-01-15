"""SQLite storage layer for messages."""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Storage:
    """Simple SQLite storage for messages."""
    
    def __init__(self, db_path: Path):
        """Initialize storage with database path."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    from_number TEXT NOT NULL,
                    to_number TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    text TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_from ON messages(from_number)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ts ON messages(ts)
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def insert_message(
        self,
        message_id: str,
        from_number: str,
        to_number: str,
        ts: str,
        text: Optional[str]
    ) -> bool:
        """
        Insert a message. Returns True if inserted, False if duplicate.
        
        Args:
            message_id: Unique message identifier
            from_number: Sender phone number
            to_number: Recipient phone number
            ts: ISO-8601 timestamp
            text: Message text (optional)
        
        Returns:
            True if inserted, False if duplicate
        """
        created_at = datetime.utcnow().isoformat() + "Z"
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO messages (message_id, from_number, to_number, ts, text, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (message_id, from_number, to_number, ts, text, created_at))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Duplicate message_id
            return False
    
    def get_messages(
        self,
        limit: int = 50,
        offset: int = 0,
        from_number: Optional[str] = None,
        since: Optional[str] = None,
        q: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get messages with filtering and pagination.
        
        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            from_number: Filter by sender
            since: Filter by timestamp (ISO-8601)
            q: Search in message text
        
        Returns:
            Tuple of (messages list, total count)
        """
        conditions = []
        params = []
        
        if from_number:
            conditions.append("from_number = ?")
            params.append(from_number)
        
        if since:
            conditions.append("ts >= ?")
            params.append(since)
        
        if q:
            conditions.append("text LIKE ?")
            params.append(f"%{q}%")
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) as count FROM messages{where_clause}"
        
        # Get messages
        query = f"""
            SELECT message_id, from_number, to_number, ts, text
            FROM messages
            {where_clause}
            ORDER BY ts ASC, message_id ASC
            LIMIT ? OFFSET ?
        """
        
        with self._get_connection() as conn:
            # Get total count
            total = conn.execute(count_query, params).fetchone()["count"]
            
            # Get messages
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
            
            messages = [
                {
                    "message_id": row["message_id"],
                    "from": row["from_number"],
                    "to": row["to_number"],
                    "ts": row["ts"],
                    "text": row["text"]
                }
                for row in rows
            ]
            
            return messages, total
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about messages.
        
        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            # Total messages
            total = conn.execute("SELECT COUNT(*) as count FROM messages").fetchone()["count"]
            
            # Unique senders count
            senders_count = conn.execute(
                "SELECT COUNT(DISTINCT from_number) as count FROM messages"
            ).fetchone()["count"]
            
            # Messages per sender (top 10)
            top_senders = conn.execute("""
                SELECT from_number, COUNT(*) as count
                FROM messages
                GROUP BY from_number
                ORDER BY count DESC
                LIMIT 10
            """).fetchall()
            
            messages_per_sender = [
                {"from": row["from_number"], "count": row["count"]}
                for row in top_senders
            ]
            
            # First and last message timestamps
            first_row = conn.execute(
                "SELECT ts FROM messages ORDER BY ts ASC LIMIT 1"
            ).fetchone()
            last_row = conn.execute(
                "SELECT ts FROM messages ORDER BY ts DESC LIMIT 1"
            ).fetchone()
            
            first_message_ts = first_row["ts"] if first_row else None
            last_message_ts = last_row["ts"] if last_row else None
            
            return {
                "total_messages": total,
                "senders_count": senders_count,
                "messages_per_sender": messages_per_sender,
                "first_message_ts": first_message_ts,
                "last_message_ts": last_message_ts
            }
    
    def health_check(self) -> bool:
        """Check if database is reachable."""
        try:
            with self._get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
