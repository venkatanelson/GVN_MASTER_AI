import os
from app import app, db, UserBrokerConfig, cipher

def check_shoonya():
    with app.app_context():
        config = UserBrokerConfig.query.first()
        if not config:
            print("❌ No Broker Config Found!")
            return
            
        print("="*50)
        print("🔍 GVN ALGO: BROKER CHECKER")
        print("="*50)
        print(f"✅ Selected Broker: {config.broker_name.upper()}")
        print(f"✅ Client ID: {config.client_id}")
        print(f"✅ Bypass Dhan Enabled: {'YES' if config.broker_name == 'Shoonya' else 'NO'}")
        print("="*50)
        
        if config.broker_name == 'Shoonya':
            print("🚀 SHOONYA ENGINE IS ACTIVE!")
            print("Our next step is to inject Shoonya's Github API (NorenApi) to fetch the Option Chain.")
            print("Right now, the system is safely bypassing Dhan to avoid errors.")
        else:
            print(f"Currently using {config.broker_name}.")

if __name__ == '__main__':
    check_shoonya()
