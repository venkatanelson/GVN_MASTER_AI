import sqlite3

def force_angel():
    conn = sqlite3.connect('gvn_algo_pro.db')
    cursor = conn.cursor()
    
    # Let's see what is in the table
    cursor.execute("SELECT id, user_id, broker_name, client_id FROM user_broker_config")
    rows = cursor.fetchall()
    print("Before update:")
    for row in rows:
        print(row)
        
    cursor.execute("UPDATE user_broker_config SET broker_name = 'AngelOne', client_id = 'P218754' WHERE user_id = 1")
    conn.commit()
    
    cursor.execute("SELECT id, user_id, broker_name, client_id FROM user_broker_config")
    rows = cursor.fetchall()
    print("\nAfter update:")
    for row in rows:
        print(row)
        
    conn.close()

if __name__ == '__main__':
    force_angel()
