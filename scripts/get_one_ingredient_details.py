
import sqlite3
import os

db_path = os.path.expanduser("~/Documents/BakeTracker/bake_tracker.db")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get details for one ingredient
    cursor.execute("SELECT * FROM ingredients LIMIT 1;")
    row = cursor.fetchone()

    if row:
        # Get column names
        column_names = [description[0] for description in cursor.description]
        print("First Ingredient Details:")
        for name, value in zip(column_names, row):
            print(f"  {name}: {value}")
    else:
        print("No ingredients found.")

    conn.close()

except sqlite3.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
