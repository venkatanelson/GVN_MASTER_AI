import sqlite3

db_path = 'instance/gvn_algo_pro.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('🔍 Adding missing columns to user table...')

# Add password_hash if missing
try:
    cursor.execute("ALTER TABLE user ADD COLUMN password_hash VARCHAR(128)")
    print('✅ Added column: password_hash')
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e):
        print('ℹ️  Column password_hash already exists')
    else:
        print(f'❌ Error: {e}')

# Add role if missing
try:
    cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
    print('✅ Added column: role')
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e):
        print('ℹ️  Column role already exists')
    else:
        print(f'❌ Error: {e}')

# Add is_active if missing
try:
    cursor.execute("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1")
    print('✅ Added column: is_active')
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e):
        print('ℹ️  Column is_active already exists')
    else:
        print(f'❌ Error: {e}')

conn.commit()
conn.close()
print('✅ Migration complete! Your database is now ready.')
