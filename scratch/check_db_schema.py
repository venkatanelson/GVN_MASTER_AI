
import sqlite3

def check_schema():
    try:
        conn = sqlite3.connect('instance/gvn_algo_pro.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(user_broker_config)")
        columns = cursor.fetchall()
        print("Columns in user_broker_config:")
        for col in columns:
            print(col)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
