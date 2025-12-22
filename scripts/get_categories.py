
import sqlite3
import os

db_path = os.path.expanduser("~/Documents/BakeTracker/bake_tracker.db")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get distinct categories
    cursor.execute("SELECT DISTINCT category FROM ingredients ORDER BY category;")
    categories = cursor.fetchall()

    if categories:
        for category in categories:
            print(category[0])
    else:
        print("No categories found or categories are empty strings.")

    conn.close()

except sqlite3.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
