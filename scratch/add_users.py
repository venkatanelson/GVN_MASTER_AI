import sys
import os
from datetime import datetime

# Add path to import app and db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db, User

users_data = [
    ('bharath kumar', '9032751673', 'Demo Trial', '31-03-2026', 'OFF'),
    ('Sangram Behera', '7892437019', 'Demo Trial', '20-05-2026', 'ON'),
    ('Venkat', '+91 93814 90610', 'Basic', '27-05-2026', 'ON'),
    ('Bandi sreekrishna', '9704601443', 'Basic', '01-05-2026', 'ON'),
    ('VENKATAIAH REDDICHERLA', '+96550143086', 'Demo Trial', '17-05-2026', 'ON'),
    ('Ratan babu', '9492629206', 'Demo Trial', '08-04-2026', 'OFF'),
    ('TestUser', '9942135107', 'Demo Trial', '21-04-2026', 'OFF'),
    ('Chinna', '6281044792', 'Demo Trial', '10-04-2026', 'OFF'),
    ('Sai', '8886047545', 'Demo Trial', '30-03-2026', 'OFF'),
    ('Mahesh ponnaganti', '9347509214', 'Demo Trial', '31-03-2026', 'OFF'),
    ('SREENIVASA REDDY', '9493115713', 'Demo Trial', '26-05-2026', 'ON'),
    ('Narendra', '7396774567', 'Demo Trial', '27-05-2026', 'ON'),
    ('Ch.sreenu', '9700766585', 'Demo Trial', '31-03-2026', 'OFF'),
    ('Riyaz', '9381490610', 'Demo Trial', '27-05-2026', 'OFF'),
    ('Sudhakar', '9700237700', 'Demo Trial', '27-05-2026', 'OFF'),
    ('prabhu', '08247726904', 'Demo Trial', '27-05-2026', 'ON'),
    ('Sureshkancheti', '9000474797', 'Demo Trial', '31-03-2026', 'OFF'),
    ('sree8881', '9848408881', 'Demo Trial', '15-05-2026', 'ON'),
    ('Manikantha', '9000913724', 'Demo Trial', '31-03-2026', 'ON'),
    ('Chaitanya', '9398460738', 'Demo Trial', '19-05-2026', 'ON'),
    ('PSN MURYHY', '9966586314', 'Demo Trial', '19-05-2026', 'ON')
]

with app.app_context():
    for name, phone, plan, expiry, algo_status in users_data:
        # Check if user already exists
        existing_user = User.query.filter_by(phone=phone).first()
        exp_date = datetime.strptime(expiry, '%d-%m-%Y')
        
        if not existing_user:
            new_user = User(
                username=name,
                phone=phone,
                email=f'{phone}@gvn.com', # Fake email for test accounts
                password_hash='pbkdf2:sha256:600000$P85N8dI8$59e0a1b6c7a918e9a66d6d45e5b', # random hash
                role='user',
                user_type='DEMO',
                selected_plan=plan,
                algo_status=algo_status,
                expiry_date=exp_date,
                is_approved=True,
                is_locked=False
            )
            db.session.add(new_user)
            print(f'✅ Added New User: {name} ({phone})')
        else:
            existing_user.username = name
            existing_user.user_type = 'DEMO'
            existing_user.selected_plan = plan
            existing_user.algo_status = algo_status
            existing_user.expiry_date = exp_date
            existing_user.is_approved = True
            existing_user.is_locked = False
            print(f'🔄 Updated Existing User: {name} ({phone})')
            
    db.session.commit()
    print('\n🎉 All Users successfully synced into Admin Dashboard Database!')
