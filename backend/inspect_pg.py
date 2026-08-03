import psycopg2
from psycopg2.extras import RealDictCursor

try:
    conn = psycopg2.connect("postgresql://inframind:inframind_secret@localhost:5432/inframind")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'")
    cols = cur.fetchall()
    print("Columns in PostgreSQL 'users' table:")
    for col in cols:
        print(f" - {col['column_name']} ({col['data_type']})")
        
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    print("\nUsers in PostgreSQL:")
    for user in users:
        print(user)
        
    conn.close()
except Exception as e:
    print(f"Error connecting to Postgres: {e}")
