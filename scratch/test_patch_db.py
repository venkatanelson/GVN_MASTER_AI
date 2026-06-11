import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import patch
import app

@patch('app.db')
def test_func(mock_db):
    from app import db
    print(f"Inside test: db = {db}")
    print(f"Inside test: mock_db = {mock_db}")

print(f"Before patch: app.db = {app.db}")
test_func()
print(f"After patch: app.db = {app.db}")
