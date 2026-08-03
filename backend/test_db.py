import os
import sys
from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text

print("DATABASE_URL:", settings.DATABASE_URL)
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT * FROM users')).fetchall()
        print("Users:", result)
        cols = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        if not cols:
            cols = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'")).fetchall()
        print("Columns:", cols)
except Exception as e:
    print("Error:", e)
