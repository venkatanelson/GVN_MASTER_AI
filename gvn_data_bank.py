
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

if __name__ == "__main__":
    init_db()
