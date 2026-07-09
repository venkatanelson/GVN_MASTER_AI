
import sqlite3
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger("GVN_DataBank")

DB_PATH = "gvn_data_bank.db"
CSV_PATH = "live_market_history.csv"

# Ensure CSV header exists
if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", encoding="utf-8") as f:
        f.write("timestamp,symbol,strike,type,ltp,oi,volume,delta,iv\n")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS option_chain_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT,
            strike_price FLOAT,
            option_type TEXT,
            ltp FLOAT,
            delta FLOAT,
            gamma FLOAT,
            theta FLOAT,
            vega FLOAT,
            oi INTEGER,
            oi_change INTEGER,
            volume INTEGER,
            iv FLOAT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_wind_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT,
            wind_direction TEXT,
            wind_power FLOAT,
            trend_type TEXT,
            smart_money TEXT,
            battle_status TEXT,
            pcr FLOAT,
            underlying_value FLOAT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            message TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fii_dii_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            fii_cash REAL,
            dii_cash REAL,
            fii_idx_fut REAL,
            fii_idx_opt REAL,
            fii_stk_fut REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("✅ GVN Data Bank initialized.")

def save_option_snapshot(symbol, data_list):
    """
    Saves a list of option data points to the database.
    data_list: list of dicts with keys [strike, type, ltp, delta, gamma, theta, vega, oi, oi_change, volume, iv]
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for item in data_list:
            cursor.execute('''
                INSERT INTO option_chain_history 
                (timestamp, symbol, strike_price, option_type, ltp, delta, gamma, theta, vega, oi, oi_change, volume, iv)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ts, symbol, item.get('strike'), item.get('type'), 
                item.get('ltp'), item.get('delta', 0), item.get('gamma', 0), 
                item.get('theta', 0), item.get('vega', 0), item.get('oi', 0), 
                item.get('oi_change', 0), item.get('volume', 0), item.get('iv', 0)
            ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error saving to Data Bank: {e}")

def save_option_915_benchmark(symbol, strike, opt_type, high, low, delta, levels):
    """
    Saves the 9:15 AM benchmark (high, low, delta, and i-levels) to sqlite.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 🛡️ GVN SCHEMA PROTECTION: Detect and fix outdated table schema
        try:
            cursor.execute("SELECT strike FROM option_915_benchmarks LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("DROP TABLE IF EXISTS option_915_benchmarks")
        
        # Ensure table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_915_benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                strike FLOAT,
                option_type TEXT,
                high FLOAT,
                low FLOAT,
                delta FLOAT,
                i1 FLOAT,
                i5 FLOAT,
                i7 FLOAT
            )
        ''')
        
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO option_915_benchmarks 
            (timestamp, symbol, strike, option_type, high, low, delta, i1, i5, i7)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ts, symbol, float(strike), opt_type, float(high), float(low), float(delta),
            float(levels.get("i1", 0)), float(levels.get("i5", 0)), float(levels.get("i7", 0))
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"💾 9:15 Option Benchmark Saved: {symbol} {strike} {opt_type} (H:{high} L:{low})")
    except Exception as e:
        logger.error(f"❌ Error saving 9:15 benchmark to Data Bank: {e}")

def record_to_csv(symbol, item):
    """Records a single data point to CSV for playback/backtesting"""
    try:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(CSV_PATH, "a", encoding="utf-8") as f:
            f.write(f"{ts},{symbol},{item.get('strike')},{item.get('type')},{item.get('ltp')},{item.get('oi')},{item.get('volume')},{item.get('delta',0)},{item.get('iv',0)}\n")
    except:
        pass

def cleanup_old_data(days=7):
    """
    Deletes data older than 'days' days.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("DELETE FROM option_chain_history WHERE timestamp < ?", (cutoff,))
        conn.commit()
        count = cursor.rowcount
        conn.close()
        logger.info(f"🧹 Data Bank Cleanup: Removed {count} old records.")
        return count
    except Exception as e:
        logger.error(f"❌ Cleanup Error: {e}")
        return 0

def get_historical_trend(symbol, strike, opt_type, hours=24):
    """
    Retrieves LTP history for a specific strike to analyze trend.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            SELECT timestamp, ltp, oi, delta FROM option_chain_history 
            WHERE symbol = ? AND strike_price = ? AND option_type = ? AND timestamp > ?
            ORDER BY timestamp ASC
        ''', (symbol, strike, opt_type, cutoff))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"❌ Error fetching trend: {e}")
        return []

def save_wind_status(symbol, wind_dir, wind_power, trend_type, smart_money, battle_status, pcr, spot):
    """
    Saves the calculated wind direction and metrics to the sqlite DB.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO market_wind_history 
            (timestamp, symbol, wind_direction, wind_power, trend_type, smart_money, battle_status, pcr, underlying_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ts, symbol, wind_dir, float(wind_power), trend_type, smart_money, battle_status, float(pcr), float(spot)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error saving wind status: {e}")

def get_latest_wind_status(symbol):
    """
    Retrieves the most recent wind status record for a symbol from the database.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wind_direction, wind_power, trend_type, smart_money, battle_status, pcr, underlying_value, timestamp
            FROM market_wind_history
            WHERE symbol = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (symbol,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "wind_direction": row[0],
                "wind_power": row[1],
                "trend_type": row[2],
                "smart_money": row[3],
                "battle_status": row[4],
                "pcr": row[5],
                "underlying_value": row[6],
                "timestamp": row[7]
            }
    except Exception as e:
        logger.error(f"❌ Error fetching latest wind status: {e}")
    return None

def save_ai_message(role, message):
    """Saves a message in the rolling AI memory"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO ai_memory (timestamp, role, message)
            VALUES (?, ?, ?)
        ''', (ts, role, message))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error saving AI message: {e}")

def get_ai_history(limit=30):
    """Retrieves chat history from SQLite"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Retrieve latest messages
        cursor.execute('''
            SELECT role, message FROM ai_memory
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        # Return in chronological order
        return list(reversed(rows))
    except Exception as e:
        logger.error(f"❌ Error retrieving AI history: {e}")
        return []

def purge_old_ai_memory(days=1):
    """Deletes AI memory records before today's date"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cutoff = datetime.now().strftime('%Y-%m-%d 00:00:00')
        cursor.execute("DELETE FROM ai_memory WHERE timestamp < ?", (cutoff,))
        conn.commit()
        count = cursor.rowcount
        conn.close()
        if count > 0:
            logger.info(f"🧹 AI Memory Purged: Removed {count} messages before today.")
        return count
    except Exception as e:
        logger.error(f"❌ Error purging old AI memory: {e}")
        return 0

def save_fii_dii_record(date_str, fii_cash, dii_cash, fii_idx_fut, fii_idx_opt, fii_stk_fut):
    """
    Saves or updates FII/DII flow records in SQLite.
    All cash values are in Crores.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO fii_dii_history 
            (date, fii_cash, dii_cash, fii_idx_fut, fii_idx_opt, fii_stk_fut)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date_str, float(fii_cash), float(dii_cash), float(fii_idx_fut), float(fii_idx_opt), float(fii_stk_fut)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error saving FII/DII record: {e}")

def get_latest_fii_dii():
    """
    Retrieves the latest FII/DII action data from the database.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date, fii_cash, dii_cash, fii_idx_fut, fii_idx_opt, fii_stk_fut, timestamp
            FROM fii_dii_history
            ORDER BY date DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "date": row[0],
                "fii_cash": row[1],
                "dii_cash": row[2],
                "fii_idx_fut": row[3],
                "fii_idx_opt": row[4],
                "fii_stk_fut": row[5],
                "timestamp": row[6]
            }
    except Exception as e:
        logger.error(f"❌ Error fetching latest FII/DII record: {e}")
    return None

if __name__ == "__main__":
    init_db()
    purge_old_ai_memory()
