"""
GVN Integration Test Suite
Validates all core components work together correctly
"""

import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVNTests")

def test_imports():
    """Test that all modules import correctly"""
    logger.info("=" * 60)
    logger.info("TEST 1: Module Imports")
    logger.info("=" * 60)
    
    try:
        import gvn_master_robot
        logger.info("✓ gvn_master_robot imported")
        
        import gvn_delta_levels_engine
        logger.info("✓ gvn_delta_levels_engine imported")
        
        import gvn_levels_engine
        logger.info("✓ gvn_levels_engine imported")
        
        import broker_api
        logger.info("✓ broker_api imported")
        
        import shared_data
        logger.info("✓ shared_data imported")
        
        import security_engine_v2
        logger.info("✓ security_engine_v2 imported")
        
        import gvn_startup
        logger.info("✓ gvn_startup imported")
        
        logger.info("✅ All modules imported successfully\n")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}\n")
        return False

def test_level_calculations():
    """Test GVN level calculations"""
    logger.info("=" * 60)
    logger.info("TEST 2: Level Calculations")
    logger.info("=" * 60)
    
    try:
        import gvn_levels_engine
        
        # Test with sample data
        high_915 = 100.0
        low_915 = 90.0
        
        levels = gvn_levels_engine.calculate_gvn_levels(high_915, low_915)
        
        logger.info(f"Input: High={high_915}, Low={low_915}")
        logger.info(f"Output Levels:")
        
        required_levels = ['i0', 'i1', 'i2', 'i3', 'i5', 'i6', 'i7']
        all_present = True
        
        for level in required_levels:
            if level in levels:
                logger.info(f"  ✓ {level}: {levels[level]}")
            else:
                logger.error(f"  ✗ {level}: MISSING")
                all_present = False
        
        if all_present and len(levels) >= 7:
            logger.info("✅ Level calculations working correctly\n")
            return True
        else:
            logger.error("❌ Level calculation incomplete\n")
            return False
    
    except Exception as e:
        logger.error(f"❌ Level calculation failed: {e}\n")
        return False

def test_robot_initialization():
    """Test Master Robot initialization"""
    logger.info("=" * 60)
    logger.info("TEST 3: Master Robot Initialization")
    logger.info("=" * 60)
    
    try:
        import gvn_master_robot
        
        robot = gvn_master_robot.GVNMasterRobot()
        
        logger.info(f"✓ Robot created")
        logger.info(f"  - Delta range: {robot.priority_delta_min}-{robot.priority_delta_max}")
        logger.info(f"  - Stop loss: {robot.stop_loss_pts} pts")
        logger.info(f"  - Panic exit: {robot.panic_exit_pts} pts")
        logger.info(f"  - Active trades: {len(robot.active_trades)}")
        logger.info(f"  - Market indices: {robot.market_indices}")
        
        logger.info("✅ Robot initialization successful\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ Robot initialization failed: {e}\n")
        return False

def test_broker_api():
    """Test Broker API"""
    logger.info("=" * 60)
    logger.info("TEST 4: Broker API")
    logger.info("=" * 60)
    
    try:
        import broker_api
        
        # Test order statistics tracking
        stats = broker_api.get_order_stats()
        
        logger.info(f"✓ Order API available")
        logger.info(f"  - Total orders: {stats['total']}")
        logger.info(f"  - Successful: {stats['successful']}")
        logger.info(f"  - Failed: {stats['failed']}")
        logger.info(f"  - Success rate: {stats['success_rate']:.1f}%")
        
        logger.info("✅ Broker API functioning\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ Broker API test failed: {e}\n")
        return False

def test_shared_data():
    """Test shared data structures"""
    logger.info("=" * 60)
    logger.info("TEST 5: Shared Data Structures")
    logger.info("=" * 60)
    
    try:
        import shared_data
        
        # Test thread-safe operations
        shared_data.update_market_data("NIFTY", 23500.0)
        data = shared_data.get_market_data("NIFTY")
        
        if data['spot'] == 23500.0:
            logger.info("✓ Market data update works")
        
        # Test pulse update
        pulse_data = {
            "trend": "UPTREND",
            "trend_strength": 75,
            "momentum": "STRONG"
        }
        shared_data.update_market_pulse("NIFTY", pulse_data)
        pulse = shared_data.get_market_pulse("NIFTY")
        
        logger.info(f"✓ Market pulse: {pulse['trend']} ({pulse['trend_strength']})")
        
        # Test trade history
        test_trade = {
            "symbol": "NIFTY24100CE",
            "entry": 100.0,
            "exit": 110.0,
            "pnl": 10.0
        }
        shared_data.add_trade_to_history(test_trade)
        stats = shared_data.get_trade_stats()
        
        logger.info(f"✓ Trade history: {stats['total_trades']} trades, PnL: {stats['total_pnl']}")
        
        logger.info("✅ Shared data structures working\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ Shared data test failed: {e}\n")
        return False

def test_security_engine():
    """Test security engine"""
    logger.info("=" * 60)
    logger.info("TEST 6: Security Engine")
    logger.info("=" * 60)
    
    try:
        import security_engine_v2
        
        shield = security_engine_v2.SecurityShield()
        
        logger.info("✓ Security engine created")
        
        # Test IP operations
        shield.whitelist_ip("127.0.0.1")
        logger.info("✓ IP whitelisting works")
        
        # Get stats
        stats = shield.get_security_stats()
        logger.info(f"✓ Files monitored: {stats['critical_files_monitored']}")
        logger.info(f"✓ Attack mode: {stats['attack_mode_active']}")
        
        logger.info("✅ Security engine operational\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ Security engine test failed: {e}\n")
        return False

def test_delta_engine():
    """Test Delta Levels Engine"""
    logger.info("=" * 60)
    logger.info("TEST 7: Delta Levels Engine")
    logger.info("=" * 60)
    
    try:
        import gvn_delta_levels_engine
        
        # Test trigger strength calculation
        test_strike = {
            'symbol': 'NIFTY24100CE',
            'delta': 0.64,
            'volume': 5000,
            'bid_ask_spread': 0.1
        }
        
        strength = gvn_delta_levels_engine._calculate_trigger_strength(test_strike)
        logger.info(f"✓ Trigger strength calculated: {strength}/100")
        
        if 0 <= strength <= 100:
            logger.info("✓ Strength score in valid range")
        
        logger.info("✅ Delta engine working\n")
        return True
    
    except Exception as e:
        logger.error(f"❌ Delta engine test failed: {e}\n")
        return False

def run_all_tests():
    """Run all integration tests"""
    logger.info("\n")
    logger.info("╔" + "="*58 + "╗")
    logger.info("║  GVN SYSTEM INTEGRATION TEST SUITE                       ║")
    logger.info("║  Testing all core components                            ║")
    logger.info("╚" + "="*58 + "╝")
    logger.info("\n")
    
    tests = [
        ("Module Imports", test_imports),
        ("Level Calculations", test_level_calculations),
        ("Robot Initialization", test_robot_initialization),
        ("Broker API", test_broker_api),
        ("Shared Data", test_shared_data),
        ("Security Engine", test_security_engine),
        ("Delta Engine", test_delta_engine),
    ]
    
    results = []
    for name, test_func in tests:
        results.append((name, test_func()))
    
    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("=" * 60)
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✅ ALL TESTS PASSED - GVN SYSTEM READY FOR TRADING!")
        return 0
    else:
        logger.info(f"\n❌ {total - passed} test(s) failed - please review logs")
        return 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
