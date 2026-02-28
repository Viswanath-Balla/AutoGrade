import sys
import os

# Add the current directory to sys.path to ensure db/models can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import engine, Base, DATABASE_URL, DB_SSL_CA
from models import User, QuestionPaper, AnswerSheet
from sqlalchemy import text

def test_connection():
    print(f"--- Testing Connection ---")
    print(f"Connecting to: {DATABASE_URL.split('@')[-1]}") # Print host/db only for security
    print(f"CA Certificate Path: {DB_SSL_CA}")
    
    if DB_SSL_CA and not os.path.exists(DB_SSL_CA):
        print(f"Warning: CA certificate file not found at {DB_SSL_CA}")

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("[SUCCESS] Database Connected Successfully:", result.scalar())
            
            # Check TiDB version
            version = connection.execute(text("SELECT VERSION()")).scalar()
            print(f"[INFO] TiDB Version: {version}")
            
    except Exception as e:
        print("[FAILURE] Connection Failed:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")

def create_tables():
    print(f"\n--- Syncing Schema ---")
    try:
        # This will create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        print("[SUCCESS] Tables Verified/Created Successfully")
        
        # Verify specific tables exist
        with engine.connect() as connection:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"[INFO] Existing Tables: {', '.join(tables)}")
            
    except Exception as e:
        print("[FAILURE] Table Creation/Verification Failed:", e)

if __name__ == "__main__":
    test_connection()
    create_tables()

