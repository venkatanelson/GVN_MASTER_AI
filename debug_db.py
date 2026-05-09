import sqlite3

db_path = 'instance/gvn_algo_pro.db'

def debug():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- User Table ---")
    cursor.execute("SELECT id, username, email, user_type FROM user")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- UserBrokerConfig Table ---")
    cursor.execute("SELECT * FROM user_broker_config")
    rows = cursor.fetchall()
    if not rows:
        print("Empty table.")
    else:
        for row in rows:
            print(row)
            
    conn.close()

if __name__ == "__main__":
    debug()
