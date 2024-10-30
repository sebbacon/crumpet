import sqlite3
import os
import glob
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "documents.db")

def get_db():
    """Get a database connection"""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db_cursor():
    """Context manager for database cursor"""
    conn = get_db()
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()

def migrate():
    """Run all pending migrations"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create migrations table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Get list of applied migrations
    cursor.execute("SELECT name FROM migrations")
    applied = {row[0] for row in cursor.fetchall()}
    
    # Get all migration files
    migration_files = sorted(glob.glob("migrations/*.sql"))
    
    # Apply pending migrations
    for file_path in migration_files:
        name = os.path.basename(file_path)
        if name not in applied:
            print(f"Applying migration: {name}")
            with open(file_path) as f:
                cursor.executescript(f.read())
            cursor.execute("INSERT INTO migrations (name) VALUES (?)", (name,))
    
    conn.commit()
    conn.close()

def create_document(title: str, description: str, content: str, tags: str | None = None):
    """Create a new document"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documents (title, description, content, tags)
            VALUES (?, ?, ?, ?)
            RETURNING *
            """,
            (title, description, content, tags)
        )
        return dict(cursor.fetchone())

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        migrate()
