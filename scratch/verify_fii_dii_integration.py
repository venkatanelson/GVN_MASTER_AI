"""
GVN FII/DII Integration Verification Script
Tests database storage, retrieval, and sentiment bias calculation logic.
"""

import sys
import os
import json
from datetime import datetime

# Include main workspace path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gvn_data_bank import save_fii_dii_record, get_latest_fii_dii, init_db
from gvn_ai_sentiment_engine import UnifiedSentimentFilter

def run_verification():
    print("[START] Running GVN FII/DII Integration Verification Tests")
    print("-" * 50)
    
    # Initialize DB in case it's not
    init_db()
    
    # 1. Back up existing latest FII/DII record to restore later
    original_latest = get_latest_fii_dii()
    if original_latest:
        print(f"Backed up original latest record from date: {original_latest['date']}")
    else:
        print("No original record found to back up.")
        
    # Mock alpha grid for testing
    mock_grid = {
        "calls": [
            {"strike": 25000, "volume": 5000, "gamma": 0.001},
        ],
        "puts": [
            {"strike": 25000, "volume": 5000, "gamma": 0.001}, # PCR = 1.0 (Neutral)
        ]
    }
    
    # Define test scenarios
    # (Test Name, Date, FII Net, DII Net, Expected Bias, Expected Text Keyword)
    scenarios = [
        (
            "Scenario A: Heavy FII Selling",
            "9999-12-31", -2500.0, 500.0, -1.5,
            "HEAVY FII SELLING"
        ),
        (
            "Scenario B: Heavy FII Buying",
            "9999-12-31", 1800.0, 200.0, 1.5,
            "HEAVY FII BUYING"
        ),
        (
            "Scenario C: Moderate FII Selling with DII Support",
            "9999-12-31", -600.0, 1200.0, -0.25, # -0.75 (mod selling) + 0.5 (DII support) = -0.25
            "MODERATE FII SELLING"
        ),
        (
            "Scenario D: Neutral Flow",
            "9999-12-31", 0.0, 0.0, 0.0,
            "NEUTRAL FLOW"
        )
    ]
    
    all_passed = True
    
    for name, date_str, fii, dii, expected_bias, kw in scenarios:
        print(f"\n[TEST] {name}")
        
        # Fresh sentiment engine instance to prevent history pollution
        sentiment = UnifiedSentimentFilter()
        
        # Save mock record
        save_fii_dii_record(
            date_str=date_str,
            fii_cash=fii,
            dii_cash=dii,
            fii_idx_fut=0.0,
            fii_idx_opt=0.0,
            fii_stk_fut=0.0
        )
        
        # Verify db retrieval
        retrieved = get_latest_fii_dii()
        if not retrieved or retrieved["date"] != date_str:
            print("  [FAIL] Failed to save/retrieve mock FII/DII record from database.")
            all_passed = False
            continue
            
        # Run sentiment analysis
        result = sentiment.get_full_sentiment(
            alpha_grid=mock_grid,
            price=25000,
            volume=100000,
            price_direction="UP"
        )
        
        # Note: volume_trend is neutral (+0), PCR is 1.0 (neutral, +0), volume spike is false (+0), prime is false (+0)
        # So sentiment_score should exactly equal expected_bias.
        actual_score = result["score"]
        fii_dii_sentiment_text = result["components"]["fii_dii_sentiment"]
        
        print(f"  Sent score: {actual_score} (Expected: {expected_bias})")
        print(f"  Sent desc : {fii_dii_sentiment_text}")
        
        # Assertion check
        score_ok = abs(actual_score - expected_bias) < 0.01
        text_ok = kw in fii_dii_sentiment_text
        
        if score_ok and text_ok:
            print("  [PASS] Score and description matched expectations.")
        else:
            print(f"  [FAIL] Score match: {score_ok}, Text match: {text_ok}")
            all_passed = False
            
    # Clean up: delete mock record and restore original
    import sqlite3
    try:
        conn = sqlite3.connect("gvn_data_bank.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fii_dii_history WHERE date = '9999-12-31'")
        conn.commit()
        conn.close()
        print("\n[CLEANUP] Deleted mock test record from database.")
    except Exception as e:
        print(f"\n[WARNING] Cleanup failed: {e}")
        
    if original_latest:
        save_fii_dii_record(
            date_str=original_latest["date"],
            fii_cash=original_latest["fii_cash"],
            dii_cash=original_latest["dii_cash"],
            fii_idx_fut=original_latest["fii_idx_fut"],
            fii_idx_opt=original_latest["fii_idx_opt"],
            fii_stk_fut=original_latest["fii_stk_fut"]
        )
        print("[CLEANUP] Restored original latest FII/DII record.")
        
    print("-" * 50)
    if all_passed:
        print("[RESULT] ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    else:
        print("[RESULT] SOME VERIFICATION TESTS FAILED. CHECK LOGS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
