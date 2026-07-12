import glob, sqlite3
for db in glob.glob("*.db"):
    print(f"DB: {db}")
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  Tables: {tables}")
        for t in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                print(f"    Table {t}: {cursor.fetchone()[0]} rows")
            except Exception as e:
                print(f"    Table {t} error: {e}")
        conn.close()
    except Exception as e:
        print(f"  DB Error: {e}")
