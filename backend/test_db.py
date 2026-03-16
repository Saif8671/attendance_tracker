import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

print(f"Testing connection to: {db_url.split('@')[-1]}") # Print host only for security

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    db_version = cur.fetchone()
    print("✅ Connection Successful!")
    print(f"Database version: {db_version[0]}")
    
    # Test if tables exist
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = cur.fetchall()
    print(f"Found {len(tables)} tables in 'public' schema:")
    for table in tables:
        print(f" - {table[0]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print("❌ Connection Failed!")
    print(f"Error: {e}")
