"""
GVN FII/DII Data Fetcher Module
Scrapes daily institutional activity data from Moneycontrol and saves it to GVN Data Bank.
"""

import requests
import random
import time
import json
import logging
from bs4 import BeautifulSoup
from gvn_data_bank import save_fii_dii_record

logger = logging.getLogger("GVN_FII_DII_Fetcher")

def clean_val(val_str):
    """Cleans numeric string representation (removes commas and converts to float)"""
    if not val_str or str(val_str).strip() == "":
        return 0.0
    try:
        # Remove commas and whitespace, then convert to float
        clean_str = str(val_str).replace(",", "").strip()
        return float(clean_str)
    except Exception as e:
        logger.warning(f"Failed to clean numeric value '{val_str}': {e}")
        return 0.0

def sync_fii_dii_data():
    """
    Fetches the latest 30 days of FII/DII activity from Moneycontrol
    and saves/updates them in the local SQLite database.
    Returns:
        int: Number of records successfully synchronized, or 0 if failed.
    """
    url = "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php"
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    
    try:
        logger.info(f"📡 Fetching FII/DII EOD data from Moneycontrol...")
        response = requests.get(url, headers=headers, timeout=10.0)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to fetch page. HTTP status code: {response.status_code}")
            return 0
            
        soup = BeautifulSoup(response.content, 'html.parser')
        next_data = soup.find("script", id="__NEXT_DATA__")
        
        if not next_data:
            logger.error("❌ __NEXT_DATA__ script tag containing JSON payload not found on page.")
            return 0
            
        js_data = json.loads(next_data.string)
        props = js_data.get("props", {})
        page_props = props.get("pageProps", {})
        fii_dii_obj = page_props.get("FiiDiiData", {})
        fii_dii_list = fii_dii_obj.get("fiiDiiData", [])
        
        if not fii_dii_list:
            logger.warning("⚠️ No FII/DII data records found in pageProps JSON.")
            return 0
            
        saved_count = 0
        logger.info(f"🔄 Syncing {len(fii_dii_list)} FII/DII history records...")
        
        for item in fii_dii_list:
            date_str = item.get("date")
            if not date_str:
                continue
                
            fii_cash = clean_val(item.get("fiiCM"))
            dii_cash = clean_val(item.get("diiCM"))
            fii_idx_fut = clean_val(item.get("fiiIdxFut"))
            fii_idx_opt = clean_val(item.get("fiiIdxOpt"))
            fii_stk_fut = clean_val(item.get("fiiStkFut"))
            
            save_fii_dii_record(
                date_str=date_str,
                fii_cash=fii_cash,
                dii_cash=dii_cash,
                fii_idx_fut=fii_idx_fut,
                fii_idx_opt=fii_idx_opt,
                fii_stk_fut=fii_stk_fut
            )
            saved_count += 1
            
        logger.info(f"✅ FII/DII Synchronization Complete: {saved_count} records saved/updated.")
        try:
            sync_participant_oi_data()
        except Exception as pe:
            logger.error(f"⚠️ Error syncing participant OI: {pe}")
        return saved_count
        
    except Exception as e:
        logger.error(f"❌ Error during FII/DII data synchronization: {e}")
        return 0

def sync_participant_oi_data():
    """
    Downloads the latest available participant-wise open interest CSV from NSE archives,
    parses it, and saves/updates it in the local SQLite database.
    """
    import requests
    from datetime import datetime, timedelta
    import csv
    from gvn_data_bank import save_participant_oi
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    # Try last 10 days to find the latest available daily report
    for i in range(10):
        dt = datetime.now() - timedelta(days=i)
        date_str = dt.strftime("%d%m%Y")
        db_date_str = dt.strftime("%Y-%m-%d")
        url = f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{date_str}.csv"
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                lines = resp.text.splitlines()
                header_idx = -1
                for idx, line in enumerate(lines):
                    if "Client Type" in line:
                        header_idx = idx
                        break
                if header_idx == -1:
                    continue
                    
                reader = csv.reader(lines[header_idx:])
                headers_list = [h.strip() for h in next(reader)]
                
                data = {}
                for row in reader:
                    if not row or len(row) < len(headers_list):
                        continue
                    client_type = row[0].strip()
                    if client_type in ["Client", "DII", "FII", "Pro"]:
                        row_data = {}
                        for col_idx, col_name in enumerate(headers_list[1:], start=1):
                            try:
                                val_str = row[col_idx].strip().replace(",", "")
                                row_data[col_name] = int(val_str) if val_str else 0
                            except:
                                row_data[col_name] = 0
                        data[client_type] = row_data
                
                if data:
                    save_participant_oi(db_date_str, data)
                    logger.info(f"✅ Participant OI successfully synced for {db_date_str}")
                    return True
        except Exception as e:
            logger.error(f"Error fetching participant OI for {db_date_str}: {e}")
            
    logger.warning("⚠️ Could not download participant OI from NSE.")
    return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    sync_fii_dii_data()
