
import app
with app.app_context():
    from app import User, UserBrokerConfig
    users = User.query.all()
    print("--- USERS ---")
    for u in users:
        print(f"ID: {u.id}, Name: {u.username}, Email: {u.email}, Phone: {u.phone}, Admin: {u.is_admin}")
        conf = UserBrokerConfig.query.filter_by(user_id=u.id).first()
        if conf:
            print(f"  Broker: {conf.broker_name}, ClientID: {conf.client_id}")
    
    admin = User.query.filter_by(is_admin=True).first()
    if admin:
        print(f"\nIdentified Admin: {admin.email}")
    else:
        # Check for the hardcoded one
        admin = User.query.filter_by(email='nelsonp143@gmail.com').first()
        if admin:
            print(f"\nFound Nelson (hardcoded admin): {admin.email}")
        else:
            print("\nNo admin found by flag or email 'nelsonp143@gmail.com'")
